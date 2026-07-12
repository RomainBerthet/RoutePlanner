"""Taxonomy of point-of-interest categories.

Each category maps to a set of OpenStreetMap tag filters used to build Overpass
queries and to classify results. The taxonomy is intentionally small and
travel-oriented: the goal is to surface *things worth stopping for* around a
waypoint, not an exhaustive map dump.

The ``weight`` drives ranking (higher = more interesting by default), ``icon``
is a plain emoji reused by the HTML exporter, and ``label`` is a French, human
readable section title.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


# An OSM filter is a (key, {values}) pair. An element matches a category when
# any of its filters match: the element carries ``key`` with a value in the set
# (an empty set means "any value for this key").
OSMFilter = Tuple[str, frozenset]


@dataclass(frozen=True)
class Category:
    key: str
    label: str
    icon: str
    weight: float
    filters: Tuple[OSMFilter, ...]

    def matches(self, tags: Dict[str, str]) -> bool:
        for osm_key, values in self.filters:
            if osm_key not in tags:
                continue
            if not values or tags[osm_key] in values:
                return True
        return False


def _f(key: str, *values: str) -> OSMFilter:
    return key, frozenset(values)


# Ordered by descending priority: an element is classified into the first
# category whose filters it matches, so put the more specific/interesting
# categories first.
CATEGORIES: Tuple[Category, ...] = (
    Category(
        key="sight",
        label="À voir",
        icon="🏛️",
        weight=1.0,
        filters=(
            _f("tourism", "attraction", "artwork"),
            _f(
                "historic",
                "castle",
                "monument",
                "memorial",
                "ruins",
                "fort",
                "archaeological_site",
                "city_gate",
                "monastery",
                "tower",
            ),
        ),
    ),
    Category(
        key="viewpoint",
        label="Points de vue",
        icon="🌄",
        weight=0.9,
        filters=(_f("tourism", "viewpoint"),),
    ),
    Category(
        key="nature",
        label="Nature",
        icon="🌲",
        weight=0.85,
        filters=(
            _f("natural", "peak", "waterfall", "cave_entrance", "spring", "cliff", "glacier"),
            _f("leisure", "nature_reserve", "park"),
            _f("boundary", "national_park", "protected_area"),
        ),
    ),
    Category(
        key="beach",
        label="Plages & baignade",
        icon="🏖️",
        weight=0.9,
        filters=(
            _f("natural", "beach"),
            _f("leisure", "beach_resort", "swimming_area"),
        ),
    ),
    Category(
        key="museum",
        label="Culture",
        icon="🖼️",
        weight=0.75,
        filters=(_f("tourism", "museum", "gallery"),),
    ),
    Category(
        key="religious",
        label="Patrimoine religieux",
        icon="⛪",
        weight=0.6,
        filters=(
            _f("building", "church", "cathedral", "chapel"),
            _f("amenity", "place_of_worship"),
        ),
    ),
    Category(
        key="food",
        label="Manger",
        icon="🍽️",
        weight=0.5,
        filters=(_f("amenity", "restaurant"),),
    ),
    Category(
        key="drink",
        label="Boire un coup",
        icon="🍺",
        weight=0.45,
        filters=(_f("amenity", "bar", "pub", "biergarten", "cafe"),),
    ),
)

CATEGORY_BY_KEY: Dict[str, Category] = {c.key: c for c in CATEGORIES}

# Categories that describe places to visit (as opposed to eat/drink). Handy as a
# default when the caller only wants sightseeing.
SIGHTSEEING_KEYS: Tuple[str, ...] = (
    "sight",
    "viewpoint",
    "nature",
    "beach",
    "museum",
    "religious",
)

DEFAULT_KEYS: Tuple[str, ...] = tuple(c.key for c in CATEGORIES)


def resolve_categories(keys=None) -> List[Category]:
    """Return the Category objects for ``keys`` (defaults to the whole taxonomy).

    Unknown keys are ignored so callers can pass user input safely.
    """

    if keys is None:
        return list(CATEGORIES)
    resolved = [CATEGORY_BY_KEY[key] for key in keys if key in CATEGORY_BY_KEY]
    return resolved or list(CATEGORIES)


def classify(tags: Dict[str, str], categories=None) -> str | None:
    """Return the key of the first matching category, or ``None``."""

    for category in categories or CATEGORIES:
        if category.matches(tags):
            return category.key
    return None
