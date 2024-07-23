import datetime
import typing
from dataclasses import dataclass
from enum import StrEnum

from shapely import Polygon
from shapely.geometry.base import BaseGeometry

COMPARABLE = "COMPARABLE"
DEFAULT_COMPARABLE = "DEFAULT_COMPARABLE"
DISTANCE_THRESHOLD = 350


class ChangeAction(StrEnum):
    IGNORE = "ignore"
    ADD = "add"
    REMOVE = "remove"
    UPDATE_GEOM = "update_geom"
    UPDATE_ATTR = "update_attr"
    UPDATE_GEOM_ATTR = "update_geom_attr"
    CANNOT_COMPARE = "cannot_compare"


class DBConnectionDetails(typing.TypedDict):
    name: str
    host: str
    port: int
    user: str
    password: str
    schema: str
    table: str


class GeoInterface(typing.TypedDict):
    properties: dict[str, str | int | float | datetime.date | None]
    geometry: typing.Union[BaseGeometry, None]


class GeoSchema(typing.TypedDict):
    properties: dict[str, str]
    geometry: str


class Comparison(typing.NamedTuple):
    distance: float | None
    attrs: dict[str, tuple[str, str]]

    def is_geom_within_threshold(self) -> bool:
        """Whether the distance is less than the threshold distance."""
        if self.distance is None:
            return False
        return self.distance < DISTANCE_THRESHOLD

    def changed_attrs(self) -> dict[str, tuple[str, str]]:
        """Attributes which have changed."""
        return {k: (a, b) for k, (a, b) in self.attrs.items() if a != b}


@dataclass
class Source:
    """
    Base class for data sources
    """

    schema: typing.ClassVar[GeoSchema] = None
    default_comparable_attrs: typing.ClassVar = frozenset({"source_id", "source_name", "source_type"})
    optional_comparable_attrs: typing.ClassVar = frozenset({"occupancy"})

    source_id: typing.Annotated[int, COMPARABLE, DEFAULT_COMPARABLE]
    source_name: typing.Annotated[str, COMPARABLE, DEFAULT_COMPARABLE]
    source_type: typing.Annotated[str, COMPARABLE, DEFAULT_COMPARABLE]
    geom: BaseGeometry | None
    occupancy: typing.Annotated[int | None, COMPARABLE] = None
    change_action: ChangeAction | None = None
    change_description: str | None = None
    comments: str | None = None
    geometry_change: str | None = None

    @property
    def __geo_interface__(self) -> GeoInterface:
        raise NotImplementedError

    @classmethod
    def comparable_attrs(cls):
        return frozenset(cls.default_comparable_attrs | cls.optional_comparable_attrs)

    def get(self, key, default=None):
        """
        Reproduces dict.get behaviour to allow Fiona to consume this class
        in the same way as its own classes, using __geo_interface__.
        """
        return getattr(self, key, default)


class ExternalSource(Source):
    @classmethod
    def from_external(cls, record) -> typing.Self:
        raise NotImplementedError


@dataclass(eq=False)
class Facility(Source):
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
            "sql": "str",
            "geometry_change": "str",
            "comments": "str",
        },
    }

    geom: Polygon
    facilities_id: int | None = None
    facilities_name: str | None = None
    facilities_use: str | None = None
    facilities_subtype: str | None = None
    last_modified: datetime.date | None = None
    sql: str | None = None

    @classmethod
    def from_props_and_geom(cls, properties, geom) -> typing.Self:
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

                "sql": self.sql,
                "geometry_change": self.geometry_change,
                "comments": "",
            },
        }

    def update_from_other(self, other: ExternalSource, check_attrs: set[str] = Source.default_comparable_attrs):
        # Compare geometry
        distance = self.geom.distance(other.geom) if other.geom is not None else None
        if distance is None:
            self.change_action = ChangeAction.UPDATE_GEOM
            self.change_description = "Geom: missing"
            self.geometry_change = "Missing"
        elif distance > DISTANCE_THRESHOLD:
            self.change_action = ChangeAction.UPDATE_GEOM
            self.change_description = f"Geom: {distance:.1f}m"
            self.geometry_change = "Modify"

        # Compare attributes
        attrs = {attr: (getattr(self, attr), getattr(other, attr)) for attr in check_attrs}
        changed_attrs = {k: (a, b) for k, (a, b) in attrs.items() if a != b}
        if changed_attrs:
            description = "; ".join([f'{attrib_type}: "{old_attrib}" -> "{new_attrib}"' for attrib_type, (old_attrib, new_attrib) in changed_attrs.items()])
            sql = self._generate_update_sql(changed_attrs)
            if self.change_action == ChangeAction.UPDATE_GEOM:
                self.change_action = ChangeAction.UPDATE_GEOM_ATTR
                self.change_description = f"{self.change_description}, Attrs: {description}"
                self.sql = sql
                self.geometry_change = "Modify"
            else:
                self.change_action = ChangeAction.UPDATE_ATTR
                self.change_description = f"Attrs: {description}"
                self.sql = sql

    def _generate_update_sql(self, changed_attrs: dict[str, tuple[str, str]]) -> str | None:
        """
        Generates an SQL UPDATE query to update the NZ Facilities database
        with the changes described in the passed comparison object.
        """
        sql = "UPDATE facilities.facilities SET "
        for attr, (old, new) in changed_attrs.items():
            match attr:
                case "source_name":
                    sql += f"name='{new}',  source_name='{new}', "
                case "source_type":
                    sql += f"use_type='{new}', "
                case "occupancy":
                    sql += f"estimated_occupancy='{new}', "
        sql += "last_modified=CURRENT_DATE "
        sql += f"WHERE facility_id={self.facilities_id} AND source_facility_id={self.source_id};"
        return sql


def compare_facilities(
    facilities: dict[int, Facility], external_sources: dict[int, ExternalSource], comparison_attrs: set[str]
) -> tuple[dict[int, Facility], dict[int, ExternalSource]]:
    """
    Compares a collection of schools from the MOE dataset with a collection of
    schools from the current facilities dataset. Each facilities school is
    marked with whether it should be updated (if it is still in the MOE dataset,
    but its location or attributes have changed) or removed (if it is no longer
    in the MOE dataset). MOE schools which are not in the facilities are marked
    to be added.
    """
    for facility_id, facility in facilities.items():
        external_match = external_sources.get(facility_id)
        if external_match and external_match.change_action != ChangeAction.IGNORE:
            facility.update_from_other(external_match, check_attrs=comparison_attrs)
        else:
            facility.change_action = ChangeAction.REMOVE
    for external_source_id, external_source in external_sources.items():
        if external_source.change_action != ChangeAction.IGNORE and external_source_id not in facilities:
            external_source.change_action = ChangeAction.ADD
    return facilities, external_sources
