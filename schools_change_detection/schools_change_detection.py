"""
Schools Change detection for updating NZ Facilities.

This script takes NZ Facilities data from either a file or database source.
Checks the schools within that source against the data downloaded from the MOE
Schools API. It then outputs a geopackage containing the unfiltered MOE data,
filtered MOE data, and the NZ Facilities data annotated with update suggestions.

Attributes being compared:
- Source Name
- Source Type
- Geom (based on distance MOE point and Facilities polygon)

Occupancy not checked for now as every school
had a different estimated occupancy.

Future alterations suggested:
- Exception list
- Input JSON file containing DB conn details

History:
5/10/2023 - Created - RClarke
"""

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar, Literal, NamedTuple, Union

import fiona
import psycopg2
import pyproj
import requests
from fiona.crs import CRS
from psycopg2 import OperationalError, extras
from shapely.geometry import MultiPoint, Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, transform
from tqdm import tqdm

##################
# Set up logging #
##################

logger: logging.Logger = logging.getLogger("schools_change_detection")


def setup_logging() -> None:
    """Set up logging"""
    logger.setLevel(logging.DEBUG)
    log_formatter = logging.Formatter(fmt="{asctime} {levelname:8} {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{")
    if not QUIET:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(log_formatter)
        logger.addHandler(stream_handler)


####################
# Global variables #
####################

DBCONN_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "host": {"type": "string"},
        "port": {"type": "number"},
        "user": {"type": "string"},
        "password": {"type": "string"},
        "schema": {"type": "string"},
        "table": {"type": "string"},
    },
    "additionalProperties": False,
}

OUTPUT_SCHEMAS: dict[str, dict[str, Union[str, dict[str, str]]]] = {
    "nz_facilities": {
        "geometry": "MultiPolygon",
        "properties": {
            "facility_id": "int",
            "source_facility_id": "str",
            "name": "str",
            "source_name": "str",
            "use": "str",
            "use_type": "str",
            "use_subtype": "str",
            "estimated_occupancy": "int",
            "last_modified": "date",
            "change_action": "str",
            "change_description": "str",
            "comments": "str",
            "sql": "str",
        },
    },
    "moe_schools": {
        "geometry": "Point",
        "properties": {
            "School_Id": "int",
            "Org_Name": "str",
            "Add1_Line1": "str",
            "Add1_Suburb": "str",
            "Add1_City": "str",
            "Org_Type": "str",
            "Roll_Date": "date",
            "Total": "int",
            "Latitude": "float",
            "Longitude": "float",
            "change_action": "str",
            "change_description": "str",
        },
    },
}

MOE_ENDPOINT = "https://catalogue.data.govt.nz/api/3/action/datastore_search_sql"

MOE_SQL = 'SELECT "School_Id", "Org_Name", "Add1_Line1", "Add1_Suburb", "Add1_City", "Org_Type", \
         "Latitude", "Longitude", "Roll_Date", "Total" FROM "20b7c271-fd5a-4c9e-869b-481a0e2453cd" \
             ORDER BY "School_Id"'

FACILITIES_FIELDS = [
    "facility_id",
    "source_facility_id",
    "name",
    "source_name",
    "use",
    "use_type",
    "use_subtype",
    "estimated_occupancy",
    "last_modified",
    "ST_AsGeoJSON(shape) as shape",
]
FACILITIES_FILTER = "WHERE use = 'School'"

EPSG_2193 = pyproj.CRS("EPSG:2193")
EPSG_4326 = pyproj.CRS("EPSG:4326")

TRANSFORMER_4326_TO_2193 = pyproj.Transformer.from_crs(EPSG_4326, EPSG_2193, always_xy=True)

DISTANCE_THRESHOLD = 30
TEEN_UNIT_DISTANCE_THRESHOLD = 100

QUIET = False


############################################
# Exceptions, Customised classes and alias #
############################################


class FatalError(Exception):
    pass


GeoInterface = dict[str, dict[str, Any]]
SourceKind = Literal["file", "db"]


class ChangeAction(StrEnum):
    ignore = "ignore"
    add = "add"
    remove = "remove"
    update_geom = "update_geom"
    update_attr = "update_attr"
    update_geom_attr = "update_geom_attr"


class Comparison(NamedTuple):
    distance: float | None
    attrs: dict[str, tuple[str, str]]

    def is_geom_within_threshold(self) -> bool:
        if self.distance is None:
            return False
        return self.distance < DISTANCE_THRESHOLD

    def is_attrs_same(self) -> bool:
        return all(a == b for (a, b) in self.attrs.values())

    def changed_attrs(self) -> list[str]:
        return [k for k, (a, b) in self.attrs.items() if a != b]


@dataclass
class Source:
    """
    Base class for data sources
    """

    default_check_attrs: ClassVar[list[str]] = [
        "source_id",
        "source_name",
        "source_type",
    ]

    source_id: int
    source_name: str
    source_type: str  # good use for an enum once we work out what they should be
    geom: BaseGeometry | None
    occupancy: int | None = None
    change_action: ChangeAction | None = None
    change_description: str | None = None
    comments: str | None = None

    @property
    def __geo_interface__(self):
        raise NotImplementedError

    def get(self, key, default=None):
        """
        Reproduces dict.get behaviour to allow Fiona to consume this class
        in the same way as its own classes, using __geo_interface__.
        """
        return getattr(self, key, default)

    def compare(self, other: "Source", check_geom: bool = True, check_attrs: list[str] = None) -> Comparison:
        if check_attrs is None:
            check_attrs = self.default_check_attrs
        self._check_have_attrs(check_attrs)
        other._check_have_attrs(check_attrs)
        if check_geom is True and self.geom is not None and other.geom is not None:
            distance = self.geom.distance(other.geom)
        else:
            distance = None
        attrs = {attr: (getattr(self, attr), getattr(other, attr)) for attr in check_attrs}
        return Comparison(distance=distance, attrs=attrs)

    def _check_have_attrs(self, attributes: list[str]):
        if missing := [attr for attr in attributes if not hasattr(self, attr)]:
            raise AttributeError(f"Class {self.__class__.__name__} missing attributes {', '.join(missing)}")


@dataclass(eq=False)
class MOESchool(Source):
    """
    A school facility from MOE data.
    """

    address: str | None = None
    suburb: str | None = None
    city: str | None = None
    roll_date: str | None = None
    latitude: str | None = None
    longitude: str | None = None

    @property
    def __geo_interface__(self) -> GeoInterface:
        return {
            "geometry": self.geom,
            "properties": {
                "School_Id": self.source_id,
                "Org_Name": self.source_name,
                "Add1_Line1": self.address,
                "Add1_Suburb": self.suburb,
                "Add1_City": self.city,
                "Org_Type": self.source_type,
                "Roll_Date": self.roll_date,
                "Total": self.occupancy,
                "Latitude": self.latitude,
                "Longitude": self.longitude,
                "change_action": self.change_action,
                "change_description": self.change_description,
            },
        }


@dataclass(eq=False)
class FacilitiesSchool(Source):
    """
    A school facility from LINZ Facilities data.
    """

    facilities_id: int | None = None
    facilities_name: str | None = None
    facilities_use: str | None = None
    facilities_subtype: str | None = None
    last_modified: date | None = None
    sql: str | None = None

    def update_from_comparison(self, comparison: Comparison):
        if not comparison.is_geom_within_threshold():
            self.change_action = ChangeAction.update_geom
            self.change_description = "geom"
        if not comparison.is_attrs_same():
            description = ", ".join(comparison.changed_attrs())
            if self.change_action == ChangeAction.update_geom:
                self.change_action = ChangeAction.update_geom_attr
                self.change_description = f"{self.change_description}, {description}"
            else:
                self.change_action = ChangeAction.update_attr
                self.change_description = description

    @property
    def __geo_interface__(self) -> GeoInterface:
        return {
            "geometry": self.geom,
            "properties": {
                "facility_id": self.facilities_id,
                "source_facility_id": self.source_id,
                "name": self.facilities_name,
                "source_name": self.source_name,
                "use": self.facilities_use,
                "use_type": self.source_type,
                "use_subtype": self.facilities_subtype,
                "estimated_occupancy": self.occupancy,
                "last_modified": self.last_modified,
                "change_action": self.change_action,
                "change_description": self.change_description,
                "comments": "",
                "sql": self.sql,
            },
        }

    def generate_update_sql(self, moe_match: MOESchool) -> str:
        """
        Function called when there is a need for an attribution update.
        The function creates an update sql statement containing the updated
        attributes from the matched MOE school.
        Intended to be run against the NZ Facilities DB.
        """
        # TODO: both name and source_name should be `moe_match.source_name`
        # TODO: only emit updates for columns whose values have actually changed.
        #  if source_name has changed, update both the name and source_name columns
        # TODO: no longer called, refactor to work with new method of comparison
        sql = (
            "UPDATE facilities_lds.nz_facilities "
            f"SET name='{self.source_name}', source_name='{moe_match.source_name}', "
            f"use_type='{moe_match.source_type}', estimated_occupancy={moe_match.occupancy}, "
            f"last_modified='{date.today()}' WHERE facility_id={self.facilities_id} "
            f"AND source_facility_id={self.source_id};"
        )
        return sql


########################
# CLI input validation #
########################


def validate_input_arg_file(input_arg: str) -> Path:
    """
    Validates supplied input file path. Must both exist and be a file.
    If either of these is not True, will raise a FatalError exception.
    Returns the same Path that was supplied.
    """
    file = Path(input_arg)
    if not file.exists():
        raise FatalError(f"{file} does not exist")
    if not file.is_file():
        raise FatalError(f"{file} is not a file")
    return file


def validate_input_arg_db(input_arg: str) -> dict[str, str]:
    """
    Validates the JSON string passed in by the user. It must be
    formatted correctly and contain all, and only, the fields required
    for the db connection.
    """
    # Parse JSON
    try:
        dbconn_json = json.loads(input_arg)
    except ValueError as error:
        raise FatalError("Invalid JSON") from error
    # Validate JSON keys are the ones we want for the db connection
    valid_fields = DBCONN_SCHEMA["properties"]
    valid_keys = ", ".join(f'"{field}"' for field in valid_fields)
    # Check all keys are valid according to schema
    if extra_fields := dbconn_json.keys() - valid_fields.keys():
        raise FatalError(f"'{extra_fields}' not a valid JSON key for facilities db. " "Valid keys are: {valid_keys}")
    # Check for missing keys
    if missing_fields := valid_fields.keys() - dbconn_json.keys():
        raise FatalError(f"'{missing_fields}' is missing from JSON string. Required keys are: {valid_keys}")
    return dbconn_json


def validate_output_arg(output_arg: Path, overwrite: bool) -> Path:
    """
    Validates the supplied output file path. Must be a file ending in .gpkg,
    in a directory which exists, but which doesn't itself exist unless
    overwrite is True. If any of these tests fail, a FatalError exception
    will be raised.
    """
    if not output_arg.parent.exists():
        raise FatalError(f"Parent directory of specified output file does not exist: {output_arg.parent}")
    if not output_arg.parent.is_dir():
        raise FatalError(f"Parent of specified output file is not a directory: {output_arg.parent}")
    if not output_arg.suffix == ".gpkg":
        raise FatalError(f"Specified output file does not end in .gpkg: {output_arg}")
    if output_arg.exists() and overwrite is False:
        raise FatalError("Specified output file already exists. To overwrite, rerun with --overwrite.")
    return output_arg


####################
# Shared functions #
####################


def get_error_name(error: BaseException) -> str:
    """
    Returns the name of the supplied exception, optionally prefixed
    by its module name if it not a builtin exception
    """
    if (module_name := error.__class__.__module__) != "builtins":
        return f"{module_name}.{error.__class__.__name__}"
    else:
        return error.__class__.__name__


def save_layers_to_gpkg(
    output_file: Path,
    layer_data: dict[str, Source],
    schema_name: str,
    layer_name: str,
) -> None:
    """
    Add layer to geopackage

    Args:
        output_file: the geopackage to add layer to.
        layer_data: the data the layer will contain
        schema_name: the schema of the layer
        layer_name: the name of the layer
    """
    with fiona.open(
        output_file,
        "w",
        driver="GPKG",
        layer=layer_name,
        schema=OUTPUT_SCHEMAS[schema_name],
        crs=CRS.from_epsg(2193),
    ) as output:
        logger.info(f"Writing layer {layer_name} to {output_file.name}")
        output.writerecords(layer_data.values())


#################################
# Load and structure input data #
#################################


def load_file_source(file: Path) -> dict[int, FacilitiesSchool]:
    """
    Loads the facilities from file.
    """
    facilities_schools = {}
    try:
        with fiona.open(file) as src:
            for feature in tqdm(src, disable=QUIET, total=len(src), unit="facilities"):
                if feature["properties"]["use"] == "School":
                    facilities_school = FacilitiesSchool(
                        source_id=feature["properties"]["source_facility_id"],
                        source_name=feature["properties"]["source_name"],
                        source_type=feature["properties"]["use_type"],
                        facilities_id=feature["properties"]["facility_id"],
                        facilities_name=feature["properties"]["name"],
                        occupancy=feature["properties"]["estimated_occupancy"],
                        facilities_use=feature["properties"]["use"],
                        facilities_subtype=feature["properties"]["use_subtype"],
                        last_modified=feature["properties"]["last_modified"],
                        geom=shape(feature["geometry"]),
                    )
                    facilities_schools[facilities_school.source_id] = facilities_school
        return facilities_schools
    except Exception as error:
        error_name = get_error_name(error)
        raise FatalError(f"Unable to load file {file}: {error_name} {error}") from error


def load_db_source(dbconn_json: dict[str, str]) -> dict[int, FacilitiesSchool]:
    """
    Connects to the database the user desires and queries specific
    facilities table with predetermined filters.
    """
    db_conn = None
    try:
        db_conn = psycopg2.connect(
            host=dbconn_json["host"],
            port=dbconn_json["port"],
            database=dbconn_json["name"],
            user=dbconn_json["user"],
            password=dbconn_json["password"],
        )
    except OperationalError as error:
        print(f"The error '{error}' occurred")

    facilities_schools = {}
    if db_conn:
        query = f'SELECT {",".join(FACILITIES_FIELDS)} FROM {dbconn_json["schema"]}.{dbconn_json["table"]} {FACILITIES_FILTER}'
        cursor = db_conn.cursor(cursor_factory=extras.DictCursor)
        try:
            cursor.execute(query)
            features = cursor.fetchall()

            for feature in tqdm(features, disable=QUIET, total=len(features), unit="facilities"):
                geom = json.loads(feature["shape"])
                del geom["crs"]
                facilities_school = FacilitiesSchool(
                    source_id=feature["source_facility_id"],
                    source_name=feature["source_name"],
                    source_type=feature["use_type"],
                    facilities_id=feature["facility_id"],
                    facilities_name=feature["name"],
                    occupancy=feature["estimated_occupancy"],
                    facilities_use=feature["use"],
                    facilities_subtype=feature["use_subtype"],
                    last_modified=feature["last_modified"],
                    geom=geom,
                )
                facilities_schools[facilities_school.source_id] = facilities_school

        except OperationalError as error:
            print(f"The error '{error}' occurred")

        db_conn.close()
        return facilities_schools


def request_moe_api() -> dict[int, MOESchool]:
    """
    Access MOE API and retrieve school records.

    If response status code is not 200, a FatalError exception will be raised.

    Return results as a dictionary, so you can access values in the object by key.
    """
    # TODO: optionally log this response for debugging / later analysis
    response = requests.get(MOE_ENDPOINT, params={"sql": MOE_SQL}, timeout=10)
    if not response.ok:
        raise FatalError(f"Request to API returned: Status Code {response.status_code}, {response.reason}")

    moe_schools = {}

    for record in tqdm(
        response.json()["result"]["records"],
        disable=QUIET,
        total=len(response.json()["result"]["records"]),
        unit="schools",
    ):
        moe_school = MOESchool(
            source_id=record["School_Id"],
            source_name=record["Org_Name"],
            source_type=record["Org_Type"],
            address=record["Add1_Line1"],
            suburb=record["Add1_Suburb"],
            city=record["Add1_City"],
            roll_date=record["Roll_Date"],
            occupancy=record["Total"],
            latitude=record["Latitude"],
            longitude=record["Longitude"],
            geom=make_moe_point(record["Latitude"], record["Longitude"]),
        )

        moe_schools[moe_school.source_id] = moe_school
    return moe_schools


def make_moe_point(lat: float | None, lon: float | None) -> Point | None:
    """
    Creates a Point geometry from the latitude and longitude properties from the
    MOE API response. The geoegraphic coordinates are converted to NZTM.
    If either of the values is None - which can be the case, as not all schools
    in the MOE API have coordinates - then None is returned instead.
    """
    if lat is None or lon is None:
        return None
    return transform(TRANSFORMER_4326_TO_2193.transform, Point(lon, lat))


def filter_moe_schools(
    moe_schools: dict[int, MOESchool],
) -> dict[int, MOESchool]:
    """
    Takes the collection of MOE Schools filters out proposed schools, and
    non-standalone Teen Parent  Units, i.e. those which are potentially
    contained within another school. This is determined by their distance from
    the nearest other MOE school point. The threshold distance is defined
    by the global variable TEEN_UNIT_DISTANCE.

    Args:
        moe_schools: collection of MOE Schools

    Returns: collection of MOE Schools minus those which have been excluded.
    """

    for id_, school in moe_schools.items():
        # Ignore proposed schools
        if "proposed" in school.source_name.lower():
            school.change_action = ChangeAction.ignore
        if school.source_type == "Teen Parent Unit" and school.geom is not None:
            # Create a multipoint containing all other schools
            other_schools = MultiPoint(
                [school.geom for school in moe_schools.values() if school.source_id != id_ and school.geom is not None]
            )
            # Get point of nearest other school
            nearest_other_school = nearest_points(school.geom, other_schools)[1]
            # Ignore if the nearest other school point is less than the threshold distance
            if school.geom.distance(nearest_other_school) < TEEN_UNIT_DISTANCE_THRESHOLD:
                school.change_action = ChangeAction.ignore
    return moe_schools


################
# Analyse Data #
################


def compare_schools(
    facilities_schools: dict[int, FacilitiesSchool], moe_schools: dict[int, MOESchool]
) -> tuple[dict[int, FacilitiesSchool], dict[int, MOESchool]]:
    for facility_school_id, facility_school in facilities_schools.items():
        moe_match = moe_schools.get(facility_school_id)
        if moe_match and moe_match.change_action != ChangeAction.ignore:
            comparison = facility_school.compare(moe_match)
            facility_school.update_from_comparison(comparison)
        else:
            facility_school.change_action = ChangeAction.remove
    for moe_school_id, moe_school in moe_schools.items():
        if moe_school.change_action != ChangeAction.ignore and moe_school_id not in facilities_schools:
            moe_school.change_action = ChangeAction.add
    return facilities_schools, moe_schools


###################
# Main entrypoint #
###################


def main(
    source_kind: SourceKind,
    source: Path | dict[str, str],
    output: Path,
) -> None:
    """
    Takes facilities location as an input and path to output.
    """

    # Load facilities
    match source_kind:
        case "file":
            logger.info("Loading facilities from %s", source)
            facilities_schools = load_file_source(source)
        case "db":
            logger.info("Loading facilities from DB")
            facilities_schools = load_db_source(source)
        case _:
            raise FatalError()

    # Load MOE Schools
    logger.info("Accessing MOE API")
    # TODO: optionally load this from a file rather than direct from their API to allow for testing
    moe_schools = request_moe_api()

    logger.info("Filtering MOE Schools")
    moe_schools = filter_moe_schools(moe_schools)

    # Compare facilities and MOE Schools
    logger.info("Analysing datasets")
    facilities_schools, moe_schools = compare_schools(facilities_schools, moe_schools)

    save_layers_to_gpkg(output, facilities_schools, "nz_facilities", "nz-facilities")
    save_layers_to_gpkg(output, moe_schools, "moe_schools", "moe-schools")


###################
# Parse Arguments #
###################

if __name__ == "__main__":
    PARSER = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Check for changes within the MoE schools data which need \
            to be applied to the NZ Facilities data.",
    )
    PARSER.add_argument(
        "-t",
        "--type",
        dest="source_kind",
        choices=["file", "db"],
        required=True,
        help="Flag indicating whether the facilities source type is " "an OGR readable file or a PostgreSQL DB",
    )
    PARSER.add_argument(
        "-i",
        "--input",
        metavar="<STRING>",
        required=True,
        help=(
            "If the facilities source type is 'file', then this should contain "
            "the PATH to the source file (it must be an OGR readable format). "
            "If source type is 'db', then this should contain a JSON formatted string "
            "containing the values for these keys: name, host, port, user, password, schema, table."
        ),
    )
    PARSER.add_argument(
        "-o",
        "--output",
        metavar="<PATH>",
        type=Path,
        default=Path.cwd() / "schools_change_detection.gpkg",
        help="Output file location. Must be a valid path a file ending in .gpkg.",
    )
    PARSER.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the specified output file if it already exists.",
    )
    PARSER.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Do not print any logging messages to screen.",
    )
    ARGS = PARSER.parse_args()
    try:
        if ARGS.source_kind == "file":
            SOURCE = validate_input_arg_file(ARGS.input)
        elif ARGS.source_kind == "db":
            SOURCE = validate_input_arg_db(ARGS.input)
        else:
            raise FatalError("--type must be 'file' or 'db'")
        OUTPUT = validate_output_arg(ARGS.output, ARGS.overwrite)
        QUIET = ARGS.quiet
        setup_logging()
        main(source_kind=ARGS.source_kind, source=SOURCE, output=OUTPUT)
    except FatalError as err:
        sys.exit(str(err))
    except KeyboardInterrupt:
        sys.exit()
