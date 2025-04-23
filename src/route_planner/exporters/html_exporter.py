import folium

class HTMLExporter:
    def exporter(self, coords, geometry, filename):
        m = folium.Map(location=coords[0][::-1], zoom_start=6)
        folium.GeoJson(geometry).add_to(m)

        for idx, (lon, lat) in enumerate(coords):
            folium.Marker(location=(lat, lon), popup=f"Étape {idx+1}").add_to(m)

        m.save(f"{filename}.html")
