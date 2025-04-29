import osmnx as ox
from osmnx import routing
from geopy.geocoders import Nominatim
from .interface import IRouter

class OSMnxRouter(IRouter):
    def __init__(self, mode):
        self.mode = mode
        self.geocoder = Nominatim(user_agent="route_planner")

    def geocode(self, adresse):
        location = self.geocoder.geocode(adresse)
        if not location:
            raise ValueError(f"Adresse introuvable : {adresse}")
        return (location.latitude, location.longitude)

    def calculer_route(self, adresses):
        points = [self.geocode(adr) for adr in adresses]

        lats = [lat for lat, lon in points]
        lons = [lon for lat, lon in points]

        graph = ox.graph_from_bbox(
            north=max(lats) + 0.05,
            south=min(lats) - 0.05,
            east=max(lons) + 0.05,
            west=min(lons) - 0.05,
            network_type=self.mode
        )

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
        coords = [(graph.nodes[n]['x'], graph.nodes[n]['y']) for n in full_route]
        duree_totale_h = sum(e["duree_h"] for e in etapes)

        return coords, geometry, distance_totale_km, duree_totale_h, etapes