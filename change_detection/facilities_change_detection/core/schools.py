import json
import typing
from dataclasses import dataclass
from pathlib import Path

import pyproj
import requests
from shapely.geometry import MultiPoint, Point
from shapely.ops import nearest_points, transform
from tqdm import tqdm

from facilities_change_detection.core.facilities import ChangeAction, ExternalSource, GeoInterface, GeoSchema
from facilities_change_detection.core.log import get_logger


logger = get_logger()

TEEN_UNIT_DISTANCE_THRESHOLD = 100
TRANSFORMER_4326_TO_2193 = pyproj.Transformer.from_crs(pyproj.CRS("EPSG:4326"), pyproj.CRS("EPSG:2193"), always_xy=True)
MOE_ENDPOINT = "https://catalogue.data.govt.nz/api/3/action/datastore_search_sql"
MOE_SQL = """
SELECT
    "School_Id",
    "Org_Name",
    "Add1_Line1",
    "Add1_Suburb",
    "Add1_City",
    "Org_Type",
    "Latitude",
    "Longitude",
    "Roll_Date",
    "Total"
FROM "20b7c271-fd5a-4c9e-869b-481a0e2453cd"
ORDER BY "School_Id"
"""


class FatalError(Exception):
    pass


@dataclass(eq=False)
class MOESchool(ExternalSource):
    """
    A school facility from MOE data.
    """

    schema: typing.ClassVar[GeoSchema] = {
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
    }

    geom: Point | None
    address: str | None = None
    suburb: str | None = None
    city: str | None = None
    roll_date: str | None = None
    latitude: str | None = None
    longitude: str | None = None

    @classmethod
    def from_api_response(cls, record) -> typing.Self:
        return cls(
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
            geom=cls._make_geom(record["Latitude"], record["Longitude"]),
        )

    @staticmethod
    def _make_geom(lat: float | None, lon: float | None) -> Point | None:
        """
        Creates a Point geometry from the latitude and longitude properties from the
        MOE API response. The geographic coordinates are converted to NZTM.
        If either of the values is None - which can be the case, as not all schools
        in the MOE API have coordinates - then None is returned instead.
        """
        if lat is None or lon is None:
            return None
        return transform(TRANSFORMER_4326_TO_2193.transform, Point(lon, lat))

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


def request_moe_api(
    api_response_input_path: Path | None = None, api_response_output_path: Path | None = None
) -> dict[int, MOESchool]:
    """
    Access MOE API and retrieve school records.

    If response status code is not 200, a FatalError exception will be raised.

    Return results as a dictionary, so you can access values in the object by key.
    """
    if api_response_input_path is not None:
        logger.info(f"Loading previous MOE API response from {api_response_input_path.name}")
        with api_response_input_path.open() as f:
            response_content = json.load(f)
    else:
        logger.info("Accessing MOE API")
        response = requests.get(MOE_ENDPOINT, params={"sql": MOE_SQL}, timeout=10)
        if not response.ok:
            raise FatalError(f"Request to API returned: Status Code {response.status_code}, {response.reason}")
        response_content = response.json()
        if api_response_output_path is not None:
            api_response_output_path.write_bytes(response.content)

    moe_schools = {}

    for record in tqdm(
        response_content["result"]["records"],
        total=len(response_content["result"]["records"]),
        unit="schools",
    ):
        moe_school = MOESchool.from_api_response(record)
        moe_schools[moe_school.source_id] = moe_school
    return moe_schools


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
            school.change_action = ChangeAction.IGNORE
        if school.source_type == "Teen Parent Unit" and school.geom is not None:
            # Create a multipoint containing all other schools
            other_schools = MultiPoint(
                [school.geom for school in moe_schools.values() if school.source_id != id_ and school.geom is not None]
            )
            # Get point of nearest other school
            nearest_other_school = nearest_points(school.geom, other_schools)[1]
            # Ignore if the nearest other school point is less than the threshold distance
            if school.geom.distance(nearest_other_school) < TEEN_UNIT_DISTANCE_THRESHOLD:
                school.change_action = ChangeAction.IGNORE
    return moe_schools
