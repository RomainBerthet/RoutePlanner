"""Reusable recommendation service.

Given a coordinate (or a whole :class:`RoutePlan`), the service asks a provider
for nearby points of interest, then scores, deduplicates and ranks them so the
most travel-worthy stops surface first. It is deliberately independent from the
routing layer so it can be reused from the CLI, the web app, tests or any other
caller.
"""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Dict, List, Optional, Sequence

from route_planner.recommendations.categories import (
    CATEGORY_BY_KEY,
    resolve_categories,
)
from route_planner.recommendations.models import (
    Coordinate,
    PointOfInterest,
    StopRecommendations,
)
from route_planner.recommendations.providers.overpass import OverpassProvider

# Tags that signal an especially notable place; each adds to a POI's score.
_IMPORTANCE_TAGS = {
    "wikidata": 0.45,
    "wikipedia": 0.35,
    "heritage": 0.30,
    "website": 0.10,
    "image": 0.10,
    "wikimedia_commons": 0.10,
}


class RecommendationService:
    def __init__(
        self,
        provider=None,
        radius_m: int = 8000,
        per_stop_limit: int = 8,
        per_category_limit: int = 4,
        categories: Optional[Sequence[str]] = None,
        min_score: float = 0.0,
    ):
        self.provider = provider or OverpassProvider()
        self.radius_m = radius_m
        self.per_stop_limit = per_stop_limit
        self.per_category_limit = per_category_limit
        self.categories = resolve_categories(categories)
        self.min_score = min_score

    # -- public API ---------------------------------------------------------

    def recommend_for_coordinate(
        self,
        coordinate: Coordinate,
        label: str = "",
        index: int = 0,
        exclude_ids: Optional[set] = None,
    ) -> StopRecommendations:
        raw = self.provider.fetch(coordinate, self.radius_m, self.categories)
        scored = self._score_and_filter(raw, coordinate, exclude_ids or set())
        ranked = self._rank_and_limit(scored)
        return StopRecommendations(
            label=label or self._coordinate_label(coordinate),
            coordinate=coordinate,
            pois=ranked,
            index=index,
        )

    def recommend_for_plan(self, plan) -> List[StopRecommendations]:
        """Enrich each ordered waypoint of a plan, avoiding cross-stop repeats."""

        labels = plan.ordered_addresses or []
        coordinates = plan.coordinates or []
        results: List[StopRecommendations] = []
        seen_ids: set = set()
        seen_coords: set = set()
        for index, coordinate in enumerate(coordinates):
            key = self._coordinate_key(coordinate)
            if key in seen_coords:
                continue
            seen_coords.add(key)
            label = labels[index] if index < len(labels) else ""
            stop = self.recommend_for_coordinate(
                tuple(coordinate), label=label, index=index, exclude_ids=seen_ids
            )
            for poi in stop.pois:
                seen_ids.add((poi.osm_type, poi.osm_id))
            results.append(stop)
        return results

    # -- scoring ------------------------------------------------------------

    def _score_and_filter(
        self,
        pois: Sequence[PointOfInterest],
        origin: Coordinate,
        exclude_ids: set,
    ) -> List[PointOfInterest]:
        radius_km = max(self.radius_m / 1000.0, 0.001)
        scored: List[PointOfInterest] = []
        for poi in pois:
            identity = (poi.osm_type, poi.osm_id)
            if identity in exclude_ids:
                continue
            distance_km = _haversine_km(origin, poi.coordinate)
            proximity = max(0.0, 1.0 - (distance_km / radius_km) * 0.6)
            category = CATEGORY_BY_KEY.get(poi.category)
            base = category.weight if category else 0.4
            importance = sum(
                bonus for tag, bonus in _IMPORTANCE_TAGS.items() if tag in poi.tags
            )
            score = round(base * (1.0 + importance) * (0.4 + 0.6 * proximity), 4)
            if score < self.min_score:
                continue
            scored.append(
                PointOfInterest(
                    name=poi.name,
                    category=poi.category,
                    lat=poi.lat,
                    lon=poi.lon,
                    tags=poi.tags,
                    osm_type=poi.osm_type,
                    osm_id=poi.osm_id,
                    score=score,
                    distance_km=round(distance_km, 2),
                )
            )
        return scored

    def _rank_and_limit(self, pois: List[PointOfInterest]) -> List[PointOfInterest]:
        # Drop duplicate names (keep the highest scored), then cap per category
        # and overall while preserving global score order.
        best_by_name: Dict[str, PointOfInterest] = {}
        for poi in pois:
            key = poi.name.strip().lower()
            existing = best_by_name.get(key)
            if existing is None or poi.score > existing.score:
                best_by_name[key] = poi

        ordered = sorted(best_by_name.values(), key=lambda p: p.score, reverse=True)
        per_category: Dict[str, int] = {}
        selected: List[PointOfInterest] = []
        for poi in ordered:
            if per_category.get(poi.category, 0) >= self.per_category_limit:
                continue
            per_category[poi.category] = per_category.get(poi.category, 0) + 1
            selected.append(poi)
            if len(selected) >= self.per_stop_limit:
                break
        return selected

    # -- helpers ------------------------------------------------------------

    @staticmethod
    def _coordinate_label(coordinate: Coordinate) -> str:
        lat, lon = coordinate
        return f"{lat:.3f}, {lon:.3f}"

    @staticmethod
    def _coordinate_key(coordinate) -> tuple:
        lat, lon = coordinate
        return (round(lat, 4), round(lon, 4))


def _haversine_km(origin: Coordinate, destination: Coordinate) -> float:
    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return radius * 2 * asin(min(1.0, sqrt(a)))
