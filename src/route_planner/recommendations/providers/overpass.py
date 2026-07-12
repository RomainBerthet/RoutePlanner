"""OpenStreetMap Overpass provider for point-of-interest discovery.

Overpass is free, keyless and consistent with the Nominatim geocoding already
used across the project. A single ``around`` query fetches every candidate for
all requested categories, then each element is classified locally.
"""

from __future__ import annotations

import os
from typing import Dict, List, Sequence

import requests

from route_planner.cache import SQLiteCache
from route_planner.recommendations.categories import Category, classify
from route_planner.recommendations.models import Coordinate, PointOfInterest

DEFAULT_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# Public Overpass instances are frequently overloaded (HTTP 429/504). Trying a
# couple of well-known mirrors makes real-world lookups far more reliable.
FALLBACK_MIRRORS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
CACHE_NAMESPACE = "overpass"
# Overpass rejects requests without a User-Agent (HTTP 406), matching the
# courtesy header already used for Nominatim geocoding.
USER_AGENT = "route_planner (https://github.com/RomainBerthet/RoutePlanner)"


class OverpassProvider:
    def __init__(self, base_url: str | None = None, cache=None, timeout: int = 40):
        self.base_url = (base_url or os.getenv("OVERPASS_URL") or DEFAULT_OVERPASS_URL).rstrip("/")
        self.cache = cache or SQLiteCache()
        self.timeout = timeout
        self.headers = {"User-Agent": USER_AGENT}

    @property
    def endpoints(self):
        """Primary endpoint first, then mirrors (skipping duplicates)."""

        ordered = [self.base_url]
        for mirror in FALLBACK_MIRRORS:
            if mirror.rstrip("/") not in ordered:
                ordered.append(mirror)
        return ordered

    def fetch(
        self,
        coordinate: Coordinate,
        radius_m: int,
        categories: Sequence[Category],
    ) -> List[PointOfInterest]:
        categories = list(categories)
        if not categories:
            return []

        cache_key = self._cache_key(coordinate, radius_m, categories)
        cached = self.cache.get(CACHE_NAMESPACE, cache_key)
        if cached is not None:
            return [self._poi_from_cache(item) for item in cached]

        query = self._build_query(coordinate, radius_m, categories)
        elements = self._request(query)
        if elements is None:
            # Resilient by contract: a failed lookup yields no recommendations
            # and is not cached, so a later retry can still succeed.
            return []

        pois = self._parse_elements(elements, categories)
        self.cache.set(CACHE_NAMESPACE, cache_key, [poi.to_dict() for poi in pois])
        return pois

    def _request(self, query: str):
        """POST the query to each endpoint until one answers; ``None`` if all fail."""

        for endpoint in self.endpoints:
            try:
                response = requests.post(
                    endpoint.rstrip("/"),
                    data={"data": query},
                    headers=self.headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json().get("elements", [])
            except Exception:
                continue
        return None

    # -- query building -----------------------------------------------------

    def _build_query(
        self,
        coordinate: Coordinate,
        radius_m: int,
        categories: Sequence[Category],
    ) -> str:
        lat, lon = coordinate

        # Group every requested value under its OSM key so we emit a single,
        # index-friendly regex clause per key (e.g. tourism~"^(museum|...)$").
        # This is far cheaper on Overpass than one clause per (key, value) and
        # avoids the server-side timeouts a wide taxonomy would otherwise hit.
        values_by_key: Dict[str, set] = {}
        bare_keys: set = set()
        for category in categories:
            for osm_key, values in category.filters:
                if values:
                    values_by_key.setdefault(osm_key, set()).update(values)
                else:
                    bare_keys.add(osm_key)

        clauses: List[str] = []
        for osm_key in sorted(bare_keys):
            values_by_key.pop(osm_key, None)  # a bare key subsumes any values
            clauses.append(f'  nwr(around:{radius_m},{lat},{lon})["{osm_key}"];')
        for osm_key in sorted(values_by_key):
            pattern = "|".join(sorted(values_by_key[osm_key]))
            clauses.append(
                f'  nwr(around:{radius_m},{lat},{lon})["{osm_key}"~"^({pattern})$"];'
            )

        body = "\n".join(clauses)
        return f"[out:json][timeout:{self.timeout}];\n(\n{body}\n);\nout center tags 120;"

    # -- parsing ------------------------------------------------------------

    def _parse_elements(
        self,
        elements: Sequence[Dict],
        categories: Sequence[Category],
    ) -> List[PointOfInterest]:
        pois: List[PointOfInterest] = []
        for element in elements:
            tags = element.get("tags") or {}
            name = tags.get("name")
            if not name:
                continue
            lat, lon = self._element_coordinate(element)
            if lat is None or lon is None:
                continue
            category = classify(tags, categories)
            if category is None:
                continue
            pois.append(
                PointOfInterest(
                    name=name,
                    category=category,
                    lat=float(lat),
                    lon=float(lon),
                    tags=tags,
                    osm_type=element.get("type", ""),
                    osm_id=int(element.get("id", 0)),
                )
            )
        return pois

    @staticmethod
    def _element_coordinate(element: Dict):
        if "lat" in element and "lon" in element:
            return element["lat"], element["lon"]
        center = element.get("center") or {}
        return center.get("lat"), center.get("lon")

    @staticmethod
    def _poi_from_cache(item: Dict) -> PointOfInterest:
        return PointOfInterest(
            name=item["name"],
            category=item["category"],
            lat=item["lat"],
            lon=item["lon"],
            tags=item.get("tags", {}),
            osm_type=item.get("osm_type", ""),
            osm_id=item.get("osm_id", 0),
            score=item.get("score", 0.0),
            distance_km=item.get("distance_km", 0.0),
        )

    def _cache_key(self, coordinate: Coordinate, radius_m: int, categories: Sequence[Category]) -> str:
        lat, lon = coordinate
        cat_keys = ",".join(sorted(category.key for category in categories))
        return f"{lat:.4f}|{lon:.4f}|{radius_m}|{cat_keys}"
