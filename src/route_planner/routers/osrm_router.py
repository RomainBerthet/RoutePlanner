import requests
from geopy.geocoders import Nominatim
from math import asin, cos, radians, sin, sqrt

from route_planner.cache import SQLiteCache

from .interface import IRouter

class OSRMRouter(IRouter):
    def __init__(self, mode, avoid_tolls=False, cache=None):
        self.mode = mode
        self.avoid_tolls = avoid_tolls
        self.geocoder = Nominatim(user_agent="route_planner")
        self._geocode_cache = {}
        self.cache = cache or SQLiteCache()
        self.toll_fallback_used = False

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
        profile = self._map_mode_to_profile()
        coord_str = ";".join([f"{lon},{lat}" for lat, lon in points])

        url = (
            f"http://router.project-osrm.org/table/v1/{profile}/{coord_str}"
            f"?annotations=distance,duration"
        )
        toll_url = url + "&exclude=toll" if self._should_exclude_tolls() else None
        try:
            response = self._request_json_with_optional_toll_fallback(
                toll_url or url,
                url if toll_url else None,
            )
            durations = response.get("durations")
            if not durations:
                raise ValueError("Table API returned no durations")
            payload = {
                "distance": self._normalise_distance_matrix(response.get("distances")),
                "duration": self._normalise_duration_matrix(durations),
            }
            self.cache.set("matrix", cache_key, payload)
            return payload
        except Exception:
            payload = self._fallback_matrix(points)
            self.cache.set("matrix", cache_key, payload)
            return payload

    def calculer_route(self, adresses, coordinates=None):
        coords = coordinates or [self.geocode(adr) for adr in adresses]
        coord_str = ";".join([f"{lon},{lat}" for lat, lon in coords])

        profile = self._map_mode_to_profile()

        url = (
            f"http://router.project-osrm.org/route/v1/{profile}/{coord_str}"
            f"?overview=full&geometries=geojson&steps=true"
        )
        toll_url = url + "&exclude=toll" if self._should_exclude_tolls() else None
        response = self._request_json_with_optional_toll_fallback(
            toll_url or url,
            url if toll_url else None,
        )

        if 'routes' not in response or not response['routes']:
            raise ValueError("Aucune route trouvée")

        route = response['routes'][0]
        geometry = route['geometry']
        distance_km = route['distance'] / 1000
        temps_h = route['duration'] / 3600

        # Étapes entre les adresses
        etapes = []
        for i, leg in enumerate(route.get('legs', [])):
            etapes.append({
                "depart": adresses[i],
                "arrivee": adresses[i + 1],
                "distance_km": round(leg['distance'] / 1000, 3),
                "duree_h": round(leg['duration'] / 3600, 3),
                "resume": leg.get("summary", "")
            })

        return coords, geometry, distance_km, temps_h, etapes

    def _request_json(self, url):
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return response.json()

    def _request_json_with_optional_toll_fallback(self, primary_url, fallback_url=None):
        try:
            return self._request_json(primary_url)
        except requests.HTTPError as exc:
            if fallback_url and self._is_toll_exclusion_rejected(exc):
                self.toll_fallback_used = True
                return self._request_json(fallback_url)
            raise

    def _is_toll_exclusion_rejected(self, exc):
        response = getattr(exc, "response", None)
        if response is None or response.status_code != 400:
            return False
        body = ""
        try:
            body = response.text or ""
        except Exception:
            body = ""
        return "exclude=toll" in body or "InvalidValue" in body or "InvalidQuery" in body

    def _normalise_distance_matrix(self, matrix):
        if matrix is None:
            return None
        return [
            [None if value is None else value / 1000 for value in row]
            for row in matrix
        ]

    def _normalise_duration_matrix(self, matrix):
        return [
            [None if value is None else value / 3600 for value in row]
            for row in matrix
        ]

    def _fallback_matrix(self, points):
        matrix = []
        speeds = {"drive": 50.0, "bike": 15.0, "walk": 5.0}
        speed = speeds.get(self.mode, 50.0)

        for origin in points:
            row = []
            for destination in points:
                distance_km = self._haversine_km(origin, destination)
                row.append(distance_km)
            matrix.append(row)

        return {
            "distance": matrix,
            "duration": [[value / speed for value in row] for row in matrix],
        }

    def _haversine_km(self, origin, destination):
        lat1, lon1 = origin
        lat2, lon2 = destination
        r = 6371.0
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * asin(min(1.0, sqrt(a)))
        return r * c

    def _map_mode_to_profile(self):
        mapping = {'drive': 'driving', 'bike': 'cycling', 'walk': 'walking'}
        return mapping.get(self.mode, 'driving')

    def _should_exclude_tolls(self):
        return self.avoid_tolls and self.mode == "drive"

    def _cache_key(self, *parts):
        return "|".join([self.__class__.__name__, *[self._serialize_part(part) for part in parts]])

    def _serialize_part(self, part):
        if isinstance(part, (list, tuple)):
            return repr(tuple(part))
        return str(part)
