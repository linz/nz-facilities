import typing
from dataclasses import dataclass
from enum import StrEnum

from shapely.geometry.base import BaseGeometry

COMPARABLE = "COMPARABLE"
DEFAULT_COMPARABLE = "DEFAULT_COMPARABLE"
DISTANCE_THRESHOLD = 30


class ChangeAction(StrEnum):
    IGNORE = "ignore"
    ADD = "add"
    REMOVE = "remove"
    UPDATE_GEOM = "update_geom"
    UPDATE_ATTR = "update_attr"
    UPDATE_GEOM_ATTR = "update_geom_attr"


class DBConnectionDetails(typing.TypedDict):
    name: str
    host: str
    port: int
    user: str
    password: str
    schema: str
    table: str


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

    schema: typing.ClassVar = None

    source_id: typing.Annotated[int, COMPARABLE, DEFAULT_COMPARABLE]
    source_name: typing.Annotated[str, COMPARABLE, DEFAULT_COMPARABLE]
    source_type: typing.Annotated[str, COMPARABLE, DEFAULT_COMPARABLE]
    geom: BaseGeometry | None
    occupancy: typing.Annotated[int | None, COMPARABLE] = None
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

    def compare(self, other: "Source", check_geom: bool = True, check_attrs: typing.Iterable[str] | None = None) -> Comparison:
        """
        Compares this instance with another instance, returning a Comparison object.
        """
        if check_attrs is None:
            check_attrs = self.get_comparable_attrs(default=True)
        if check_geom is True and self.geom is not None and other.geom is not None:
            distance = self.geom.distance(other.geom)
        else:
            distance = None
        attrs = {attr: (getattr(self, attr), getattr(other, attr)) for attr in check_attrs}
        return Comparison(distance=distance, attrs=attrs)

    @classmethod
    def get_comparable_attrs(cls, default: bool = False) -> set[str]:
        """
        Return a set of all comparable attributes for this class,
        being all those with a type hint of typing.Annotated[<type>, COMPARABLE].
        If default is True, only default comparable attributes will be returned.
        """
        comparable_attrs = set()
        if default is True:
            check_vals = {COMPARABLE, DEFAULT_COMPARABLE}
        else:
            check_vals = {COMPARABLE}
        for attr, type_ in typing.get_type_hints(cls, include_extras=True).items():
            if typing.get_origin(type_) is typing.Annotated and check_vals.issubset(type_.__metadata__):
                comparable_attrs.add(attr)
        return comparable_attrs


def get_comparable_attrs(cls_1: type[Source], cls_2: type[Source]) -> set[str]:
    """
    Returns a set of comparable attributes shared by the two classes.
    """
    return cls_1.get_comparable_attrs() & cls_2.get_comparable_attrs()
