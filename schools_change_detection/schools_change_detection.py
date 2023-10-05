"""
    Schools Change dection for updating NZ Facilities.
    
    This script takes NZ Facilities data from either a file or database source.
    
    Checks the schools within that source against the data downloaded from the MOE Schools API.
    
    It then outputs a geopackage containing the unfiltered MOE data, filtered MOE data, and the
    NZ Facilities data annotated with update suggestions. 
    
    Attributes being compared:
    - Source Name
    - Source Type
    - Geom (based on distance MOE point and Facilities polygon)
    * Occupancy not checked for now as every school had a different estimated occupancy *
    
    
    Intially created October 2023 by RClarke
    
    Future alterations suggested:
    - Exception list
    - Input JSON file containing DB conn details
    
"""
import argparse
import copy
import json
import logging
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import fiona
import psycopg2
import pyproj
import requests
from fiona.crs import CRS
from psycopg2 import OperationalError, extras
from shapely.geometry import MultiPoint, Point, mapping, shape
from shapely.ops import nearest_points, transform
from tqdm import tqdm

##################
# Set up logging #
##################

logger: logging.Logger = logging.getLogger("schools_change_dectection")


def setup_logging() -> None:
    """Set up logging"""
    logger.setLevel(logging.DEBUG)
    log_formatter = logging.Formatter(
        fmt="{asctime} {levelname:8} {message}", datefmt="%Y-%m-%d %H:%M:%S", style="{"
    )
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
FILESCHEMA = None
OUTPUT_SCHEMAS: Dict[str, Dict[str, Union[str, Dict[str, str]]]] = {
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

DISTANCE_FROM_FACLITY = 30
TEEN_UNIT_DISTANCE = 100

############################################
# Exceptions, Customised classes and alias #
############################################


class FatalError(Exception):
    pass


GeoRecord = Dict[str, Dict[str, Any]]


@dataclass
class Source:
    """
    Base class for facilities and moe schools.

    """

    source_id: int
    source_name: str
    source_type: str  # good use for an enum once we work out what they should be
    geom: str
    occupancy: Optional[int] = None
    change_action: Optional[str] = None
    change_description: Optional[str] = None
    comments: Optional[str] = None

    def __eq__(self, other: "Source") -> bool:
        results = {
            "source_id": self.source_id == other.source_id,
            "source_name": self.source_name == other.source_name,
            "source_type": self.source_type == other.source_type,
        }

        if all(match for match in results.values()):
            return True
        return False

    def check_distance_polygon(self, other: "Source") -> bool:
        """
        Mearsure the distance between this school and another school
        """
        if self.geom is None or other.geom is None:
            return None
        else:
            distance_from_source = shape(self.geom).distance(shape(other.geom))
            return distance_from_source <= DISTANCE_FROM_FACLITY

    def check_occupancy(self, other: "Source") -> bool:
        """
        check occupancy between this school and another school.
        """
        return self.occupancy == other.occupancy


@dataclass(eq=False)
class MOESchool(Source):
    """
    Subclass of School.
    Contains specific attributes and functions for schools that come from the MOE data.
    """

    address: Optional[str] = None
    suburb: Optional[str] = None
    city: Optional[str] = None
    roll_date: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None

    def get_geo_record(self) -> GeoRecord:
        """
        return the attributes of the school as a geo_record appropriate to be written to geopackage.
        """
        geo_record = {
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
        return geo_record

    def parse_check_results(self, check_results: Dict) -> None:
        """
        Parse the analysis results
        """
        # PARSE NEW/ADD
        if check_results["add"]:
            self.change_action = "add"


@dataclass(eq=False)
class FacilitiesSchool(Source):
    """
    Subclass of School.
    Contains specific attributes and functions for schools that come from the Facilities data.
    """

    facilities_id: Optional[int] = None
    facilities_name: Optional[str] = None
    facilities_use: Optional[str] = None
    facilities_subtype: Optional[str] = None
    last_modified: Optional[date] = None
    sql: Optional[str] = None

    def get_geo_record(self) -> GeoRecord:
        """
        return the attributes of the school as a geo_record appropriate to be written to geopackage.
        """
        geo_record = {
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
        return geo_record

    def parse_check_results(self, check_results: Dict, moe_match: MOESchool) -> None:
        """
        Parse the analysis results
        """
        # PARSE REMOVE
        ## change status to remove
        if check_results["remove"]:
            self.change_action = "remove"
        else:
            # PARSE UPDATE
            ## change status to update where if any of the update related checks are false
            if not all(
                result for check, result in check_results.items() if check != "remove"
            ):
                self.change_action = "update"
                if not check_results["attributes"]:
                    self.sql = self.generate_update_sql(moe_match)

                ## append description with each update that is needed
                self.change_description = ", ".join(
                    [
                        check
                        for check, result in check_results.items()
                        if not result and check != "remove"
                    ]
                )

    def generate_update_sql(self, moe_match: MOESchool) -> str:
        """
        Function called when there is a need for an attribution update.
        The function creates an update sql statement containing the updated
        attributes from the matched MOE school.
        Intended to be run against the NZ Facilities DB.
        """
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


def verify_input_facilities_file(file: Path) -> Path | None:
    """
    Validates supplied input file path. Must both exist and be a file.
    If either of these is not True, will raise a FatalError exception.
    Returns the same Path that was supplied.
    """
    if SOURCE_TYPE == "file":
        if not file.exists():
            raise FatalError(f"{file} does not exist")
        if not file.is_file():
            raise FatalError(f"{file} is not a file")
        return file
    return None


def verify_facilities_db_json(facilities_db_json: str) -> str | None:
    """
    Validates the JSON string passed in by the user. It must be formatted
    correclty It must also contain all, and only, the fields required for
    the db connection.
    """
    if SOURCE_TYPE == "db":
        # Validate JSON Format
        try:
            dbconn_json = json.loads(facilities_db_json)
        except ValueError as error:
            raise ValueError("Invalid JSON") from error

        # Validate JSON keys are the ones we want for the db connection
        valid_fields = DBCONN_SCHEMA["properties"]
        valid_keys = ", ".join(f'"{field}"' for field in valid_fields)

        ## check all keys are valid according to schema
        if extra_fields := dbconn_json.keys() - valid_fields.keys():
            raise ValueError(
                f"'{extra_fields}' not a valid JSON key for facilties db. "
                "Valid keys are: {valid_keys}"
            )
        ## check for missing keys
        if missing_fields := valid_fields.keys() - dbconn_json.keys():
            raise ValueError(
                f"'{missing_fields}' is missing from JSON string. Required keys are: {valid_keys}"
            )

        return dbconn_json
    else:
        return None


def verify_output_dir(output_dir: Path, overwrite: bool) -> Path:
    """
    Validates supplied output directory path. Must both exists and be a directory.
    If any of these is not true, will raise a FatalError exception. If the directory
    already exists and the overwrite argument is False, will prompt the user if they wish to delete
    the file. If they do not answer yes, a FatalError exception will be raised. If they answer yes,
    or the overwrite argument was True, the directory will be deleted. If an exception was not
    raised, the supplied directory will be returned.
    """
    if not output_dir.parent.exists():
        raise FatalError(
            f"Parent of specified output directory does not exist: {output_dir.parent}"
        )
    if not output_dir.parent.is_dir():
        raise FatalError(
            f"Parent of specified output directory is not a directory: {output_dir.parent}"
        )
    if output_dir.exists() and overwrite is False:
        answer = input(
            f"Output directory {output_dir} already exists. "
            f"Do you want to delete the directory before continuing? "
            f"Type Y to delete file, or any other value to abort: "
        )
        answer = answer.strip().lower()
        if answer == "y":
            overwrite = True
        else:
            raise FatalError("Output directory already exists")
    if overwrite is True:
        try:
            shutil.rmtree(output_dir)
        except PermissionError as error:
            raise FatalError(
                f"Unable to remove output directory {output_dir}: {error} \nAre there files inside open in QGIS?"
            ) from error

    return output_dir


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
    layer_data: Dict,
    schema_name: str,
    layer_name: str,
) -> None:
    """
    Add layer to geopackage

    Args:
        output_file (Path): the geopackage to add layer to.
        layer_data (Dict): the data the layer will contain
        schema_name (str): the schema of the layer
        layer_name (str): the name of the layer
    """
    with fiona.open(
        output_file,
        "w",
        driver="GPKG",
        layer=layer_name,
        schema=OUTPUT_SCHEMAS[schema_name],
        crs=CRS.from_epsg(2193),
    ) as output:
        for value in tqdm(
            layer_data.values(),
            disable=QUIET,
            total=len(layer_data.values()),
            unit="records",
        ):
            output.write(value.get_geo_record())


#################################
# Load and structure input data #
#################################


def load_file_source(file: Path) -> Dict:
    """
    Loads the facilities from file. Returns a list of Polygon geometries.
    """
    list_of_school_facilities = {}
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
                        geom=feature["geometry"],
                    )
                    list_of_school_facilities[
                        facilities_school.source_id
                    ] = facilities_school

        return list_of_school_facilities
    except Exception as error:
        error_name = get_error_name(error)
        raise FatalError(f"Unable to load file {file}: {error_name} {error}") from error


def load_db_source(dbconn_json: str) -> List[FacilitiesSchool]:
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

    list_of_school_facilities = {}
    if db_conn:
        query = f'SELECT {",".join(FACILITIES_FIELDS)} FROM {dbconn_json["schema"]}.{dbconn_json["table"]} {FACILITIES_FILTER}'
        cursor = db_conn.cursor(cursor_factory=extras.DictCursor)
        try:
            cursor.execute(query)
            features = cursor.fetchall()

            for feature in tqdm(
                features, disable=QUIET, total=len(features), unit="facilities"
            ):
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
                list_of_school_facilities[
                    facilities_school.source_id
                ] = facilities_school

        except OperationalError as error:
            print(f"The error '{error}' occurred")

        db_conn.close()
        return list_of_school_facilities


def request_moe_api() -> List[MOESchool]:
    """
    Access MOE API and retreive school records.

    If response status code is not 200, a FatalError exception will be raised.

    Return results as a dictionary, so you can access values in the object by key.
    """
    params = {"sql": f"{MOE_SQL}"}
    response = requests.get(MOE_ENDPOINT, params=params, timeout=10)
    if response.status_code != 200:
        raise FatalError(
            f"Request to API returned: Status Code {response.status_code}, {response.reason}"
        )

    list_of_moe_schools = {}

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
            geom=mapping(make_point(record["Latitude"], record["Longitude"]))
            if record["Latitude"] is not None and record["Longitude"] is not None
            else None,
        )

        list_of_moe_schools[moe_school.source_id] = moe_school
    return list_of_moe_schools


def make_point(lat: float, long: float) -> str:
    """
    Creates a Point using the lat and long from provided and reproject it
    to NZTM(EPSG:2193)
    """
    transformer = pyproj.Transformer.from_crs(
        EPSG_4326, EPSG_2193, always_xy=True
    ).transform
    new_point = transform(transformer, Point(long, lat))
    return new_point


def filter_moe_schools(
    unfiltered_moe_schools: List[MOESchool],
) -> List[MOESchool]:
    """
        Takes the MOE Schools list and filters out Teen Parents Units which are
        potentially contained. This is determined by distance from nearest
        other MOE school point within the same list. The distance is defined
        by the global variable TEEN_UNIT_DISTANCE.

    Args:
        unfiltered_moe_schools (List[MOE_School]): list of schools directly from API

    Returns:
        List[MOE_School]: list of schools minus the contained Teen Parent Units
    """

    filtered_moe_schools = {}
    for unfiltered_school_id, unfiltered_school in unfiltered_moe_schools.items():
        if not "proposed" in unfiltered_school.source_name.lower():
            # If school is not a Teen Parent Unit then ignore
            if unfiltered_school.source_type == "Teen Parent Unit":
                if unfiltered_school.geom is not None:
                    # Create a multipoint containing all points of all the MOE schools
                    other_moe_schools = MultiPoint(
                        [
                            school.geom["coordinates"]
                            for school in unfiltered_moe_schools.values()
                            if school.source_id != unfiltered_school_id
                            and school.geom is not None
                        ]
                    )

                    # Makes a shapely point out of the current unfiltered school
                    unfiltered_school_point = Point(
                        unfiltered_school.geom["coordinates"]
                    )

                    # Get nearest point to unfiltered school from multipoint.
                    nearest_pt = nearest_points(
                        unfiltered_school_point, other_moe_schools
                    )

                    # Measure distance and determine if school is to be excluded or not.
                    if (
                        unfiltered_school_point.distance(nearest_pt[1])
                        >= TEEN_UNIT_DISTANCE
                    ):
                        filtered_moe_schools[unfiltered_school_id] = unfiltered_school
                    else:
                        continue
            else:
                filtered_moe_schools[unfiltered_school_id] = unfiltered_school
    return filtered_moe_schools


################
# Analyse Data #
################


# look at using dictionaries so don't need to loop through lists
def compare_schools(
    facilities: Dict,
    moe_schools: Dict,
) -> List[MOESchool]:
    """
    Script checks for:
     - updates to facilities - attributes and geoms
     - facilities that need deleting
     - schools which need to be added to facilities

    Args:
        facilities (Dict): all facilities which are schools
        moe_schools (Dict): filtered moe_schools

    Returns:
        List[MOESchool]: a list of schools which need to be added to facilities.
    """
    new_schools = {}
    # check each facility exists in MOE data, and if it does, then does it need updating?
    for facility_source_id, facility in facilities.items():
        facility_results = {
            "attributes": None,
            "geom": None,
            # "occupancy": None,
            "remove": False,
        }
        moe_match = moe_schools.get(facility_source_id)

        if moe_match:
            facility_results = {
                "attributes": facility == moe_match,
                "geom": facility.check_distance_polygon(moe_match),
                # "occupancy": facility.check_occupancy(moe_match),
                "remove": False,
            }
        else:
            facility_results["remove"] = True

        facility.parse_check_results(facility_results, moe_match)

    # check each MOE school to see if it exists in facilities.
    # if it doesn't then it needs to be added.
    for school_id, school in moe_schools.items():
        new_school_bool = False

        # Does it exist in facilities
        facility_match = facilities.get(school_id)
        if not facility_match:
            new_school_bool = True
            new_schools[school_id] = school

        moe_results = {"add": new_school_bool}

        school.parse_check_results(moe_results)
    return new_schools


###################
# Main entrypoint #
###################


def main(
    faclities_input_file: Path,
    faclities_db_conn: str,
    output_dir: Path,
) -> None:
    """
    Takes facilities location as an input and path to output.
    """
    # Create output directory
    logger.info("Creating output directory at %s", output_dir)
    os.mkdir(output_dir)

    # Load facilities
    if SOURCE_TYPE == "file":
        logger.info("Loading facilities from %s", faclities_input_file)
        facilities = load_file_source(faclities_input_file)
    elif SOURCE_TYPE == "db":
        logger.info("Loading facilities from DB")
        facilities = load_db_source(faclities_db_conn)

    # Load MOE Schooles
    logger.info("Accessing MOE API")
    unfiltered_moe_schools = request_moe_api()

    # Create Output file
    output_filename = "schools_change_dectection.gpkg"
    output_file = os.path.join(output_dir, output_filename)

    logger.info("Filtering MOE Schools")
    filtered_moe_schools = filter_moe_schools(copy.deepcopy(unfiltered_moe_schools))

    # Compare facilities and MOE Schools
    logger.info("Analysing datasets")
    new_moe_schools = compare_schools(facilities, filtered_moe_schools)

    logger.info("Creating output geopackage at %s", output_file)
    logger.info("Adding NZ Facilities layer")
    save_layers_to_gpkg(output_file, facilities, "nz_facilities", "nz-facilities")

    logger.info("Adding MOE Schools layer")
    save_layers_to_gpkg(
        output_file, unfiltered_moe_schools, "moe_schools", "moe-schools"
    )

    logger.info("Adding filtered MOE Schools layer")
    save_layers_to_gpkg(
        output_file, filtered_moe_schools, "moe_schools", "moe-schools-filtered"
    )

    logger.info("Adding New MOE Schools layer")
    save_layers_to_gpkg(output_file, new_moe_schools, "moe_schools", "moe-schools-new")


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
        dest="source_type",
        choices=["file", "db"],
        required=True,
        help=(
            "Flag indicating whether the facilities source type is "
            "an OGR readable file or a PostgreSQL DB"
        ),
    )
    PARSER.add_argument(
        "-i",
        "--input",
        metavar="<STRING>",
        dest="source_details",
        required=True,
        help=(
            "If the facilties source type is 'file', then this should contain "
            "the PATH to the source file (it must be an OGR readable format). "
            "If source type is 'db', then this should contain a JSON formatted string "
            "containing the values for these keys: name, host, port, user, password, schema, table."
        ),
    )
    PARSER.add_argument(
        "-o",
        "--output",
        metavar="<PATH>",
        dest="output_dir",
        type=Path,
        default=os.path.join(os.getcwd(), "output"),
        help=(
            "Output directory which source files will be copied to and final reports outputted to."
        ),
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
        SOURCE_TYPE = ARGS.source_type
        FACILITIES_INPUT_FILE = verify_input_facilities_file(Path(ARGS.source_details))
        FACILITIES_DB_CONN = verify_facilities_db_json(ARGS.source_details)
        OUTPUT_DIR = verify_output_dir(ARGS.output_dir, ARGS.overwrite)
        QUIET = ARGS.quiet

        setup_logging()
        main(FACILITIES_INPUT_FILE, FACILITIES_DB_CONN, OUTPUT_DIR)
    except FatalError as err:
        sys.exit(str(err))
    except KeyboardInterrupt:
        sys.exit()
