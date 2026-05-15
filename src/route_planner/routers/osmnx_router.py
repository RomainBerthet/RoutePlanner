import osmnx as ox
from osmnx import routing
from geopy.geocoders import Nominatim
from math import radians, sin, cos, asin, sqrt

from route_planner.cache import SQLiteCache

from .interface import IRouter

class OSMnxRouter(IRouter):
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
        distance_matrix = self._matrix_from_points(points)
        payload = {
            "distance": distance_matrix,
            "duration": self._duration_matrix_from_distance(distance_matrix),
        }
        self.cache.set("matrix", cache_key, payload)
        return payload

    def calculer_route(self, adresses, coordinates=None):
        points = coordinates or [self.geocode(adr) for adr in adresses]

        lats = [lat for lat, lon in points]
        lons = [lon for lat, lon in points]

        graph = self._graph_from_points_bbox(lats, lons)

        nodes = [ox.nearest_nodes(graph, lon, lat) for lat, lon in points]

        full_route = []
        etapes = []

        vitesses = {'drive': 50, 'bike': 15, 'walk': 5}
        vitesse = vitesses.get(self.mode, 50)  # km/h

        for i in range(len(nodes) - 1):
            route = ox.shortest_path(graph, nodes[i], nodes[i + 1], weight='length')
            full_route += route[:-1]  # éviter doublons

            edges = ox.utils_graph.get_route_edge_attributes(graph, route, 'length')
            distance_km = sum(edges) / 1000
            duree_h = distance_km / vitesse

            etapes.append({
                "depart": adresses[i],
                "arrivee": adresses[i + 1],
                "distance_km": round(distance_km, 3),
                "duree_h": round(duree_h, 3)
            })

        full_route.append(nodes[-1])  # dernier noeud

        edges_gdf = routing.route_to_gdf(graph, full_route)
        distance_totale_km = edges_gdf['length'].sum() / 1000
        geometry = edges_gdf.geometry.__geo_interface__
        coords = [(graph.nodes[n]['y'], graph.nodes[n]['x']) for n in full_route]
        duree_totale_h = sum(e["duree_h"] for e in etapes)

        return coords, geometry, distance_totale_km, duree_totale_h, etapes

    def _matrix_from_points(self, points):
        speeds = {'drive': 50, 'bike': 15, 'walk': 5}
        speed = speeds.get(self.mode, 50)
        matrix = []
        for origin in points:
            row = []
            for destination in points:
                row.append(self._haversine_km(origin, destination))
            matrix.append(row)
        return matrix

    def _graph_from_points_bbox(self, lats, lons):
        north = max(lats) + 0.05
        south = min(lats) - 0.05
        east = max(lons) + 0.05
        west = min(lons) - 0.05
        try:
            return ox.graph_from_bbox(
                (north, south, east, west),
                network_type=self.mode,
            )
        except TypeError:
            return ox.graph_from_bbox(
                north=north,
                south=south,
                east=east,
                west=west,
                network_type=self.mode,
            )

    def _duration_matrix_from_distance(self, matrix):
        speeds = {'drive': 50, 'bike': 15, 'walk': 5}
        speed = speeds.get(self.mode, 50)
        return [[distance / speed for distance in row] for row in matrix]

    def _haversine_km(self, origin, destination):
        lat1, lon1 = origin
        lat2, lon2 = destination
        r = 6371.0
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * asin(min(1.0, sqrt(a)))
        return r * c

    def _cache_key(self, *parts):
        return "|".join([self.__class__.__name__, *[self._serialize_part(part) for part in parts]])

    def _serialize_part(self, part):
        if isinstance(part, (list, tuple)):
            return repr(tuple(part))
        return str(part)
