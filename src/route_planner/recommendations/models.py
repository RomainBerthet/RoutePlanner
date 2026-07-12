"""Data models for travel recommendations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus

Coordinate = Tuple[float, float]


@dataclass(frozen=True)
class PointOfInterest:
    """A single place worth stopping for near a waypoint."""

    name: str
    category: str
    lat: float
    lon: float
    tags: Dict[str, str] = field(default_factory=dict)
    osm_type: str = ""
    osm_id: int = 0
    score: float = 0.0
    distance_km: float = 0.0

    @property
    def coordinate(self) -> Coordinate:
        return (self.lat, self.lon)

    @property
    def gps(self) -> str:
        return f"{self.lat:.4f}, {self.lon:.4f}"

    @property
    def maps_url(self) -> str:
        """A Google Maps search link (photos, reviews, directions)."""

        query = quote_plus(f"{self.name} {self.lat},{self.lon}")
        return f"https://www.google.com/maps/search/?api=1&query={query}"

    @property
    def wikipedia(self) -> Optional[str]:
        return self.tags.get("wikipedia")

    @property
    def description(self) -> str:
        """A short human hint built from useful OSM tags."""

        parts: List[str] = []
        if self.tags.get("description"):
            parts.append(self.tags["description"])
        cuisine = self.tags.get("cuisine")
        if cuisine:
            parts.append("Cuisine : " + cuisine.replace(";", ", ").replace("_", " "))
        if self.tags.get("ele"):
            parts.append(f"Altitude {self.tags['ele']} m")
        if self.tags.get("website"):
            parts.append(self.tags["website"])
        return " · ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["gps"] = self.gps
        payload["maps_url"] = self.maps_url
        return payload


@dataclass
class StopRecommendations:
    """Recommendations attached to one waypoint of a route."""

    label: str
    coordinate: Coordinate
    pois: List[PointOfInterest] = field(default_factory=list)
    index: int = 0

    def by_category(self) -> Dict[str, List[PointOfInterest]]:
        grouped: Dict[str, List[PointOfInterest]] = {}
        for poi in self.pois:
            grouped.setdefault(poi.category, []).append(poi)
        return grouped

    @property
    def count(self) -> int:
        return len(self.pois)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "label": self.label,
            "index": self.index,
            "coordinate": list(self.coordinate),
            "pois": [poi.to_dict() for poi in self.pois],
        }
