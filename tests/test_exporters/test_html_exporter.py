from route_planner.exporters.html_exporter import HTMLExporter
from unittest.mock import patch

@patch('folium.Map.save')
def test_exporter_html(mock_save):
    exporter = HTMLExporter()
    coords = [(2.2945, 48.8584), (2.3364, 48.8606)]
    geometry = {"type": "LineString", "coordinates": coords}

    exporter.exporter(coords, geometry, "test_parcours")

    mock_save.assert_called_once()
