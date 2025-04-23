from unittest.mock import patch
from route_planner.routers.osrm_router import OSRMRouter

@patch('route_planner.routers.osrm_router.requests.get')
@patch('route_planner.routers.osrm_router.Nominatim.geocode')
def test_calculer_route(mock_geocode, mock_requests):
    mock_geocode.side_effect = [
        type('Location', (object,), {'longitude': 2.2945, 'latitude': 48.8584}),
        type('Location', (object,), {'longitude': 2.3364, 'latitude': 48.8606}),
    ]

    mock_requests.return_value.json.return_value = {
        'routes': [{
            'distance': 3000,
            'duration': 600,
            'geometry': {'type': 'LineString', 'coordinates': []}
        }]
    }

    router = OSRMRouter(mode='drive')
    coords, geometry, distance_km, temps_h = router.calculer_route(["Adresse 1", "Adresse 2"])

    assert distance_km == 3
    assert round(temps_h, 2) == 0.17
