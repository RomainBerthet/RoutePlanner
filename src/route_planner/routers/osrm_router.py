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

        url = f"http://router.project-osrm.org/route/v1/{profile}/{coord_str}?overview=full&geometries=geojson"
        response = requests.get(url).json()

        route = response['routes'][0]
        distance_km = route['distance'] / 1000
        temps_h = route['duration'] / 3600

        geometry = route['geometry']
        return coords, geometry, distance_km, temps_h

    def _map_mode_to_profile(self):
        mapping = {'drive': 'driving', 'bike': 'cycling', 'walk': 'walking'}
        return mapping.get(self.mode, 'driving')
