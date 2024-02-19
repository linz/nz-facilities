import datetime
import json
import typing
from dataclasses import dataclass
from pathlib import Path

import pyproj
import requests
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import nearest_points, transform
from tqdm import tqdm

from facilities_change_detection.core.facilities import Source, ChangeAction, Comparison
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


class GeoInterface(typing.TypedDict):
    properties: dict[str, str | int | float | datetime.date | None]
    geometry: BaseGeometry | None


class GeoSchema(typing.TypedDict):
    properties: dict[str, str]
    geometry: str


@dataclass(eq=False)
class MOESchool(Source):
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
    def from_api_response(cls, record) -> "MOESchool":
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


@dataclass(eq=False)
class FacilitiesSchool(Source):
    """
    A school facility from LINZ Facilities data.
    """

    schema: typing.ClassVar[GeoSchema] = {
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
    }

    geom: Polygon | None
    facilities_id: int | None = None
    facilities_name: str | None = None
    facilities_use: str | None = None
    facilities_subtype: str | None = None
    last_modified: datetime.date | None = None
    sql: str | None = None

    @classmethod
    def from_props_and_geom(cls, properties, geom) -> "FacilitiesSchool":
        return cls(
            source_id=properties["source_facility_id"],
            source_name=properties["source_name"],
            source_type=properties["use_type"],
            facilities_id=properties["facility_id"],
            facilities_name=properties["name"],
            occupancy=properties["estimated_occupancy"],
            facilities_use=properties["use"],
            facilities_subtype=properties["use_subtype"],
            last_modified=properties["last_modified"],
            geom=geom,
        )

    def update_from_comparison(self, comparison: Comparison):
        """
        Updates this instance in place from a Comparison instance.
        """
        if not comparison.is_geom_within_threshold():
            self.change_action = ChangeAction.UPDATE_GEOM
            if comparison.distance is None:
                self.change_description = "Geom: missing"
            else:
                self.change_description = f"Geom: {comparison.distance:.1f}m"
        if changed_attrs := comparison.changed_attrs():
            description = ", ".join(changed_attrs.keys())
            sql = self.generate_update_sql(comparison)
            if self.change_action == ChangeAction.UPDATE_GEOM:
                self.change_action = ChangeAction.UPDATE_GEOM_ATTR
                self.change_description = f"{self.change_description}, Attrs: {description}"
                self.sql = sql
            else:
                self.change_action = ChangeAction.UPDATE_ATTR
                self.change_description = f"Attrs: {description}"
                self.sql = sql

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

    def generate_update_sql(self, comparison: Comparison) -> str | None:
        """
        Generates an SQL UPDATE query to update the NZ Facilities database
        with the changes described in the passed comparison object.
        """
        if not comparison.attrs:
            return None
        sql = "UPDATE facilities_lds.nz_facilities\nSET\n"
        for attr, (old, new) in comparison.changed_attrs().items():
            match attr:
                case "source_name":
                    sql += f"  name='{new}',\n  source_name='{new}',\n"
                case "source_type":
                    sql += f"  use_type='{new}',\n"
                case "occupancy":
                    sql += f"  estimated_occupancy='{new}',\n"
        sql += "  last_modified=CURRENT_DATE\n"
        sql += f"WHERE facility_id={self.facilities_id} AND source_facility_id={self.source_id};"
        return sql


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


def compare_schools(
    facilities_schools: dict[int, FacilitiesSchool], moe_schools: dict[int, MOESchool], comparison_attrs: typing.Iterable[str]
) -> tuple[dict[int, FacilitiesSchool], dict[int, MOESchool]]:
    """
    Compares a collection of schools from the MOE dataset with a collection of
    schools from the current facilities dataset. Each facilities school is
    marked with whether it should be updated (if it is still in the MOE dataset,
    but its location or attributes have changed) or removed (if it is no longer
    in the MOE dataset). MOE schools which are not in the facilities are marked
    to be added.
    """
    for facility_school_id, facility_school in facilities_schools.items():
        moe_match = moe_schools.get(facility_school_id)
        if moe_match and moe_match.change_action != ChangeAction.IGNORE:
            comparison = facility_school.compare(moe_match, check_geom=True, check_attrs=comparison_attrs)
            facility_school.update_from_comparison(comparison)
        else:
            facility_school.change_action = ChangeAction.REMOVE
    for moe_school_id, moe_school in moe_schools.items():
        if moe_school.change_action != ChangeAction.IGNORE and moe_school_id not in facilities_schools:
            moe_school.change_action = ChangeAction.ADD
    return facilities_schools, moe_schools
