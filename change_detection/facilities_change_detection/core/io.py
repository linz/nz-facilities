import json
import sqlite3
import typing
from pathlib import Path

import fiona
import psycopg2
import requests
from fiona.crs import CRS
from psycopg2 import OperationalError, extras
from shapely.geometry import shape
from tqdm import tqdm

from facilities_change_detection.core.facilities import Facility, GeoSchema, Source
from facilities_change_detection.core.log import get_logger
from facilities_change_detection.core.schools import FatalError

logger = get_logger()

FACILITIES_SQL = """
SELECT
    facility_id,
    source_facility_id,
    name,
    source_name,
    use,
    use_type,
    use_subtype,
    estimated_occupancy,
    last_modified,
    ST_AsGeoJSON(shape) as shape
FROM
    {schema}.{table}
WHERE use = 'School'
"""

LAYER_STYLES_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS layer_styles (
    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    f_table_catalog TEXT(256),
    f_table_schema TEXT(256),
    f_table_name TEXT(256),
    f_geometry_column TEXT(256),
    styleName TEXT(30),
    styleQML TEXT,
    styleSLD TEXT,
    useAsDefault BOOLEAN,
    description TEXT,
    owner TEXT(30),
    ui TEXT(30),
    update_time DATETIME DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
"""

LAYER_STYLES_INSERT_SQL = """
INSERT OR REPLACE INTO layer_styles (
    f_table_catalog,
    f_table_schema,
    f_table_name,
    f_geometry_column,
    styleName,
    styleQML,
    styleSLD,
    useAsDefault,
    description,
    owner
)
VALUES ('', '', (?), 'geom', 'Style', (?), '', true, '', '');
"""

GPKG_CONTENTS_INSERT_SQL = """
INSERT OR REPLACE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id)
VALUES ((?), (?), (?), (?), (?));
"""


def save_layers_to_gpkg(
    output_file: Path,
    layer_schema: GeoSchema,
    layer_data: typing.Iterable[Source],
    layer_name: str,
) -> None:
    """
    Add layer to geopackage

    Args:
        output_file: the geopackage to add layer to
        layer_schema: the schema of the layer
        layer_data: the data the layer will contain
        layer_name: the name of the layer
    """
    # noinspection PyTypeChecker,PyArgumentList
    with fiona.open(
        output_file,
        "w",
        driver="GPKG",
        layer=layer_name,
        schema=layer_schema,
        crs=CRS.from_epsg(2193),
    ) as output:
        logger.info(f"Writing layer {layer_name} to {output_file.name}")
        output.writerecords(layer_data)


def load_file_source(file: Path) -> dict[int, Facility]:
    """
    Loads the facilities from file.
    """
    facilities_schools = {}
    try:
        with fiona.open(file) as src:
            for feature in tqdm(src, total=len(src), unit="facilities"):
                if feature["properties"]["use"] == "School":
                    facilities_school = Facility.from_props_and_geom(
                        properties=feature["properties"], geom=shape(feature["geometry"])
                    )
                    facilities_schools[facilities_school.source_id] = facilities_school
        return facilities_schools
    except Exception as error:
        error_name = get_error_name(error)
        raise FatalError(f"Unable to load file {file}: {error_name} {error}") from error


def load_db_source(dbconn_json: dict[str, str]) -> dict[int, Facility]:
    """
    Connects to the database the user desires and queries specific
    facilities table with predetermined filters.
    """
    facilities_schools = {}
    try:
        db_conn = psycopg2.connect(
            host=dbconn_json["host"],
            port=dbconn_json["port"],
            database=dbconn_json["name"],
            user=dbconn_json["user"],
            password=dbconn_json["password"],
        )
        query = FACILITIES_SQL.format(schema=dbconn_json["schema"], table=dbconn_json["table"])
        cursor = db_conn.cursor(cursor_factory=extras.DictCursor)
        cursor.execute(query)
        features = cursor.fetchall()
        for feature in tqdm(features, total=len(features), unit="facilities"):
            geom = json.loads(feature.pop("shape"))
            del geom["crs"]
            facilities_school = Facility.from_props_and_geom(properties=feature, geom=geom)
            facilities_schools[facilities_school.source_id] = facilities_school
        db_conn.close()
    except OperationalError as error:
        print(f"The error '{error}' occurred")
    return facilities_schools


def get_error_name(error: BaseException) -> str:
    """
    Returns the name of the supplied exception, optionally prefixed
    by its module name if it not a builtin exception.
    """
    if (module_name := error.__class__.__module__) != "builtins":
        return f"{module_name}.{error.__class__.__name__}"
    else:
        return error.__class__.__name__


def download_file(url: str, output_file: Path, chunk_size=1024) -> Path:
    """
    Downloads a file from a supplied URL to a supplied output path.

    Args:
        url: The URL of the file to download.
        output_file: The path to save the file to.
        chunk_size: size in bytes of chunks to download at a time. Defaults to 1024.

    Raises:
        requests.RequestException [or child Exceptions]: if any network issues
            occur.

    Returns:
        The Path where the file has been downloaded to.
    """
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(output_file, "wb") as f:
            for chunk in r.iter_content(chunk_size):
                f.write(chunk)
    return output_file


def add_styles_to_gpkg(gpkg_file: Path, layer_styles: dict[str, str]) -> None:
    """
    Adds QGIS layer styles to a GeoPackage.

    Args:
        gpkg_file: The GeoPackage to add the layer styles to.
        layer_styles: A dictionary mapping layer name keys to a string of a
            QGIS QML layer style definition.
    """
    connection = sqlite3.connect(gpkg_file)
    cursor = connection.cursor()
    cursor.execute("BEGIN TRANSACTION")
    try:
        cursor.execute(LAYER_STYLES_CREATE_SQL)
        cursor.executemany(
            LAYER_STYLES_INSERT_SQL,
            [(layer_name, layer_style) for layer_name, layer_style in layer_styles.items()],
        )
        cursor.execute(GPKG_CONTENTS_INSERT_SQL, ("layer_styles", "attributes", "layer_styles", "", 0))
        cursor.execute("COMMIT;")
    except Exception:
        logger.error("Error adding layer styles to GeoPackage, rolling back.")
        cursor.execute("ROLLBACK;")
