import folium
from route_planner.models import RoutePlan

class HTMLExporter:
    def exporter(self, coords_or_plan, geometry=None, filename="route"):
        if isinstance(coords_or_plan, RoutePlan):
            plan = coords_or_plan
            coords = plan.coordinates
            geometry = plan.geometry
            filename = filename or "route"
            legs = plan.legs
        else:
            plan = None
            coords = coords_or_plan
            legs = []

        if not coords:
            raise ValueError("Aucune coordonnee a exporter")

        m = folium.Map(location=coords[0], zoom_start=6)
        if geometry:
            folium.GeoJson(geometry).add_to(m)

        for idx, (lat, lon) in enumerate(coords):
            popup = f"Étape {idx + 1}"
            if idx < len(legs):
                popup = f"{legs[idx].depart} -> {legs[idx].arrivee}"
            folium.Marker(location=(lat, lon), popup=popup).add_to(m)

        self._fit_bounds(m, coords)
        m.save(f"{filename}.html")

    def _fit_bounds(self, map_obj, coords):
        if len(coords) < 2:
            return
        latitudes = [lat for lat, _ in coords]
        longitudes = [lon for _, lon in coords]
        south_west = (min(latitudes), min(longitudes))
        north_east = (max(latitudes), max(longitudes))
        map_obj.fit_bounds([south_west, north_east], padding=(30, 30))
