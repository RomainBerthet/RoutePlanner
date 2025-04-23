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

        # Calcul de la bounding box avec marge
        lats = [lat for lat, lon in points]
        lons = [lon for lat, lon in points]

        graph = ox.graph_from_bbox(
            north=max(lats) + 0.05,
            south=min(lats) - 0.05,
            east=max(lons) + 0.05,
            west=min(lons) - 0.05,
            network_type=self.mode
        )

        # Récupération des noeuds les plus proches
        nodes = [ox.nearest_nodes(graph, lon, lat) for lat, lon in points]

        # Calcul du chemin complet
        full_route = []
        for i in range(len(nodes) - 1):
            route = ox.shortest_path(graph, nodes[i], nodes[i+1], weight='length')
            full_route += route[:-1]
        full_route.append(nodes[-1])

        # Extraction des données du parcours
        edges_gdf = routing.route_to_gdf(graph, full_route)
        distance_km = edges_gdf['length'].sum() / 1000

        # Estimation simple du temps avec vitesses moyennes par mode
        vitesses = {'drive': 50, 'bike': 15, 'walk': 5}
        vitesse = vitesses.get(self.mode, 50)
        temps_h = distance_km / vitesse

        geometry = edges_gdf.geometry.__geo_interface__

        # Conversion des noeuds en coordonnées lon, lat
        coords = [(graph.nodes[n]['x'], graph.nodes[n]['y']) for n in full_route]

        return coords, geometry, distance_km, temps_h
