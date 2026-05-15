from route_planner.exporters.html_exporter import HTMLExporter
from unittest.mock import patch

@patch('folium.Map.save')
def test_exporter_html(mock_save):
    exporter = HTMLExporter()
    coords = [(2.2945, 48.8584), (2.3364, 48.8606)]
    geometry = {"type": "LineString", "coordinates": coords}

    exporter.exporter(coords, geometry, "test_parcours")

    mock_save.assert_called_once()


@patch('folium.Map.save')
def test_exporter_html_auto_fits_bounds(mock_save):
    exporter = HTMLExporter()
    coords = [(48.8584, 2.2945), (48.8606, 2.3364), (48.8530, 2.3499)]
    geometry = {"type": "LineString", "coordinates": [[2.2945, 48.8584], [2.3364, 48.8606], [2.3499, 48.8530]]}

    with patch('folium.Map.fit_bounds') as mock_fit_bounds:
        exporter.exporter(coords, geometry, "test_parcours")

    mock_fit_bounds.assert_called_once()
