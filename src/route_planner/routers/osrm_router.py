import requests
from geopy.geocoders import Nominatim
from .interface import IRouter

class OSRMRouter(IRouter):
    def __init__(self, mode):
        self.mode = mode
        self.geocoder = Nominatim(user_agent="route_planner")

    def geocode(self, adresse):
        location = self.geocoder.geocode(adresse)
        if not location:
            raise ValueError(f"Adresse introuvable : {adresse}")
        return (location.longitude, location.latitude)

    def calculer_route(self, adresses):
        coords = [self.geocode(adr) for adr in adresses]
        coord_str = ";".join([f"{lon},{lat}" for lon, lat in coords])

        profile = self._map_mode_to_profile()

        url = (
            f"http://router.project-osrm.org/route/v1/{profile}/{coord_str}"
            f"?overview=full&geometries=geojson&steps=true"
        )
        response = requests.get(url).json()

        if 'routes' not in response or not response['routes']:
            raise ValueError("Aucune route trouvée")

        route = response['routes'][0]
        geometry = route['geometry']
        distance_km = route['distance'] / 1000
        temps_h = route['duration'] / 3600

        # Étapes entre les adresses
        etapes = []
        for i, leg in enumerate(route['legs']):
            etapes.append({
                "depart": adresses[i],
                "arrivee": adresses[i + 1],
                "distance_km": round(leg['distance'] / 1000, 3),
                "duree_h": round(leg['duration'] / 3600, 3),
                "resume": leg.get("summary", "")
            })

        return coords, geometry, distance_km, temps_h, etapes

    def _map_mode_to_profile(self):
        mapping = {'drive': 'driving', 'bike': 'cycling', 'walk': 'walking'}
        return mapping.get(self.mode, 'driving')
