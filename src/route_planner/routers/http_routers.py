import os
from math import asin, cos, radians, sin, sqrt

import requests
from geopy.geocoders import Nominatim

from route_planner.cache import SQLiteCache

from .interface import IRouter


class HTTPRouterBase(IRouter):
    speeds_kmh = {"drive": 50.0, "bike": 15.0, "walk": 5.0}

    def __init__(self, mode, avoid_tolls=False, cache=None):
        self.mode = mode
        self.avoid_tolls = avoid_tolls
        self.geocoder = Nominatim(user_agent="route_planner")
        self._geocode_cache = {}
        self.cache = cache or SQLiteCache()

    def geocode(self, adresse):
        if adresse in self._geocode_cache:
            return self._geocode_cache[adresse]
        cache_key = self._cache_key("geocode", adresse)
        cached = self.cache.get("geocode", cache_key)
        if cached is not None:
            coordinate = tuple(cached)
            self._geocode_cache[adresse] = coordinate
            return coordinate
        location = self.geocoder.geocode(adresse)
        if not location:
            raise ValueError(f"Adresse introuvable : {adresse}")
        coordinate = (location.latitude, location.longitude)
        self._geocode_cache[adresse] = coordinate
        self.cache.set("geocode", cache_key, list(coordinate))
        return coordinate

    def distance_matrix(self, adresses, coordinates=None):
        points = coordinates or [self.geocode(adr) for adr in adresses]
        cache_key = self._cache_key("matrix", self.mode, points)
        cached = self.cache.get("matrix", cache_key)
        if cached is not None:
            return cached
        try:
            payload = self._api_distance_matrix(points)
        except Exception:
            payload = self._fallback_matrix(points)
        self.cache.set("matrix", cache_key, payload)
        return payload

    def _api_distance_matrix(self, points):
        raise NotImplementedError

    def _should_exclude_tolls(self):
        return False

    def _fallback_matrix(self, points):
        distance = []
        speed = self.speeds_kmh.get(self.mode, 50.0)
        for origin in points:
            row = []
            for destination in points:
                row.append(self._haversine_km(origin, destination))
            distance.append(row)
        return {
            "distance": distance,
            "duration": [[value / speed for value in row] for row in distance],
        }

    def _line_geometry(self, points):
        return {
            "type": "LineString",
            "coordinates": [[lon, lat] for lat, lon in points],
        }

    def _fallback_legs(self, adresses, points):
        legs = []
        speed = self.speeds_kmh.get(self.mode, 50.0)
        for index in range(len(points) - 1):
            distance_km = self._haversine_km(points[index], points[index + 1])
            legs.append({
                "depart": adresses[index],
                "arrivee": adresses[index + 1],
                "distance_km": round(distance_km, 3),
                "duree_h": round(distance_km / speed, 3) if speed else 0.0,
                "resume": "",
            })
        return legs

    def _haversine_km(self, origin, destination):
        lat1, lon1 = origin
        lat2, lon2 = destination
        radius = 6371.0
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        return radius * 2 * asin(min(1.0, sqrt(a)))

    def _cache_key(self, *parts):
        return "|".join([self.__class__.__name__, *[self._serialize_part(part) for part in parts]])

    def _serialize_part(self, part):
        if isinstance(part, (list, tuple)):
            return repr(tuple(part))
        return str(part)


class ValhallaRouter(HTTPRouterBase):
    def __init__(self, mode, avoid_tolls=False, cache=None, base_url=None):
        super().__init__(mode, avoid_tolls=avoid_tolls, cache=cache)
        self.base_url = (base_url or os.getenv("VALHALLA_URL") or "http://localhost:8002").rstrip("/")

    def calculer_route(self, adresses, coordinates=None):
        points = coordinates or [self.geocode(adr) for adr in adresses]
        response = requests.post(f"{self.base_url}/route", json=self._route_payload(points), timeout=30)
        response.raise_for_status()
        trip = response.json().get("trip", {})
        summary = trip.get("summary", {})
        distance_km = float(summary.get("length", 0.0))
        duration_h = float(summary.get("time", 0.0)) / 3600
        legs_payload = trip.get("legs", [])
        legs = []
        for index, leg in enumerate(legs_payload):
            leg_summary = leg.get("summary", {})
            legs.append({
                "depart": adresses[index],
                "arrivee": adresses[index + 1],
                "distance_km": round(float(leg_summary.get("length", 0.0)), 3),
                "duree_h": round(float(leg_summary.get("time", 0.0)) / 3600, 3),
                "resume": leg_summary.get("text", ""),
            })
        if not legs:
            legs = self._fallback_legs(adresses, points)
        geometry = self._valhalla_geometry(trip, points)
        return points, geometry, distance_km, duration_h, legs

    def _api_distance_matrix(self, points):
        payload = {
            "sources": [{"lat": lat, "lon": lon} for lat, lon in points],
            "targets": [{"lat": lat, "lon": lon} for lat, lon in points],
            "costing": self._costing(),
            "costing_options": self._costing_options(),
            "units": "kilometers",
        }
        response = requests.post(f"{self.base_url}/sources_to_targets", json=payload, timeout=30)
        response.raise_for_status()
        matrix = response.json().get("sources_to_targets", [])
        distance = []
        duration = []
        for row in matrix:
            distance.append([None if item is None else item.get("distance") for item in row])
            duration.append([None if item is None else item.get("time", 0.0) / 3600 for item in row])
        if not distance or not duration:
            raise ValueError("Valhalla matrix response is empty")
        return {"distance": distance, "duration": duration}

    def _route_payload(self, points):
        return {
            "locations": [{"lat": lat, "lon": lon} for lat, lon in points],
            "costing": self._costing(),
            "costing_options": self._costing_options(),
            "directions_options": {"units": "kilometers"},
            "shape_format": "geojson",
        }

    def _costing(self):
        return {"drive": "auto", "bike": "bicycle", "walk": "pedestrian"}.get(self.mode, "auto")

    def _costing_options(self):
        if self.mode == "drive" and self.avoid_tolls:
            return {"auto": {"use_tolls": 0}}
        return {}

    def _should_exclude_tolls(self):
        return self.mode == "drive" and self.avoid_tolls

    def _valhalla_geometry(self, trip, points):
        shape = trip.get("shape")
        if isinstance(shape, dict):
            return shape
        if isinstance(shape, list):
            return {"type": "LineString", "coordinates": shape}
        return self._line_geometry(points)


class GraphHopperRouter(HTTPRouterBase):
    def __init__(self, mode, avoid_tolls=False, cache=None, base_url=None, api_key=None):
        super().__init__(mode, avoid_tolls=avoid_tolls, cache=cache)
        self.base_url = (base_url or os.getenv("GRAPHHOPPER_URL") or "https://graphhopper.com/api/1").rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("GRAPHHOPPER_API_KEY", "")

    def calculer_route(self, adresses, coordinates=None):
        if not self.api_key and self.base_url.startswith("https://graphhopper.com"):
            raise ValueError("GraphHopper requiert GRAPHHOPPER_API_KEY ou une URL locale GRAPHHOPPER_URL")
        points = coordinates or [self.geocode(adr) for adr in adresses]
        params = [
            ("vehicle", self._vehicle()),
            ("locale", "fr"),
            ("calc_points", "true"),
            ("points_encoded", "false"),
        ]
        if self.api_key:
            params.append(("key", self.api_key))
        for lat, lon in points:
            params.append(("point", f"{lat},{lon}"))
        if self.mode == "drive" and self.avoid_tolls:
            params.append(("ch.disable", "true"))
            params.append(("avoid", "toll"))
        response = requests.get(f"{self.base_url}/route", params=params, timeout=30)
        response.raise_for_status()
        path = response.json().get("paths", [{}])[0]
        distance_km = float(path.get("distance", 0.0)) / 1000
        duration_h = float(path.get("time", 0.0)) / 3600000
        geometry = path.get("points") or self._line_geometry(points)
        if geometry.get("type") == "Point":
            geometry = self._line_geometry(points)
        legs = self._graphhopper_legs(path, adresses, points)
        return points, geometry, distance_km, duration_h, legs

    def _api_distance_matrix(self, points):
        if not self.api_key and self.base_url.startswith("https://graphhopper.com"):
            raise ValueError("GraphHopper matrix requires an API key")
        payload = {
            "points": [[lon, lat] for lat, lon in points],
            "profile": self._vehicle(),
            "out_arrays": ["distances", "times"],
        }
        params = {"key": self.api_key} if self.api_key else {}
        response = requests.post(f"{self.base_url}/matrix", params=params, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        distances = data.get("distances")
        times = data.get("times")
        if not distances or not times:
            raise ValueError("GraphHopper matrix response is empty")
        return {
            "distance": [[None if value is None else value / 1000 for value in row] for row in distances],
            "duration": [[None if value is None else value / 3600000 for value in row] for row in times],
        }

    def _graphhopper_legs(self, path, adresses, points):
        instructions = path.get("instructions", [])
        if not instructions or len(adresses) == 2:
            return self._fallback_legs(adresses, points)
        return self._fallback_legs(adresses, points)

    def _vehicle(self):
        return {"drive": "car", "bike": "bike", "walk": "foot"}.get(self.mode, "car")

    def _should_exclude_tolls(self):
        return self.mode == "drive" and self.avoid_tolls


class BRouter(HTTPRouterBase):
    def __init__(self, mode, avoid_tolls=False, cache=None, base_url=None):
        super().__init__(mode, avoid_tolls=avoid_tolls, cache=cache)
        self.base_url = (base_url or os.getenv("BROUTER_URL") or "https://brouter.de/brouter").rstrip("/")

    def calculer_route(self, adresses, coordinates=None):
        points = coordinates or [self.geocode(adr) for adr in adresses]
        params = {
            "lonlats": "|".join(f"{lon},{lat}" for lat, lon in points),
            "profile": self._profile(),
            "alternativeidx": "0",
            "format": "geojson",
        }
        response = requests.get(f"{self.base_url}", params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        feature = data.get("features", [{}])[0]
        properties = feature.get("properties", {})
        geometry = feature.get("geometry") or self._line_geometry(points)
        distance_km = float(properties.get("track-length", properties.get("distance", 0.0))) / 1000
        duration_h = float(properties.get("total-time", properties.get("time", 0.0))) / 3600
        if distance_km <= 0:
            fallback = self._fallback_matrix(points)
            route_indexes = range(len(points) - 1)
            distance_km = sum(fallback["distance"][index][index + 1] for index in route_indexes)
            duration_h = sum(fallback["duration"][index][index + 1] for index in route_indexes)
        return points, geometry, distance_km, duration_h, self._fallback_legs(adresses, points)

    def _api_distance_matrix(self, points):
        raise NotImplementedError("BRouter ne fournit pas de matrice publique standard")

    def _profile(self):
        if self.mode == "bike":
            return "trekking"
        if self.mode == "walk":
            return "walking"
        return "car-fast"
