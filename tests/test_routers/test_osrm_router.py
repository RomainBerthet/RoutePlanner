from requests import HTTPError
from requests.models import Response
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
    coords, geometry, distance_km, temps_h, etapes = router.calculer_route(["Adresse 1", "Adresse 2"])

    assert distance_km == 3
    assert round(temps_h, 2) == 0.17


@patch('route_planner.routers.osrm_router.requests.get')
@patch('route_planner.routers.osrm_router.Nominatim.geocode')
def test_avoid_tolls_adds_exclude(mock_geocode, mock_requests):
    mock_geocode.return_value = type('Location', (object,), {'longitude': 2.2945, 'latitude': 48.8584})
    mock_requests.return_value.json.return_value = {
        'routes': [{
            'distance': 3000,
            'duration': 600,
            'geometry': {'type': 'LineString', 'coordinates': []},
            'legs': [],
        }]
    }

    router = OSRMRouter(mode='drive', avoid_tolls=True)
    router.calculer_route(["Adresse 1", "Adresse 2"])

    called_url = mock_requests.call_args[0][0]
    assert "exclude=toll" in called_url


@patch('route_planner.routers.osrm_router.requests.get')
@patch('route_planner.routers.osrm_router.Nominatim.geocode')
def test_avoid_tolls_falls_back_when_public_osrm_rejects_toll_exclusion(mock_geocode, mock_requests):
    mock_geocode.side_effect = [
        type('Location', (object,), {'longitude': 2.2945, 'latitude': 48.8584}),
        type('Location', (object,), {'longitude': 2.3364, 'latitude': 48.8606}),
    ]

    response_error = Response()
    response_error.status_code = 400
    response_error._content = b'{"code":"InvalidValue","message":"exclude=toll not supported"}'

    failing_response = type('Resp', (), {})()
    failing_response.raise_for_status = lambda: (_ for _ in ()).throw(HTTPError(response=response_error))
    failing_response.json = lambda: {}

    success_response = type('Resp', (), {})()
    success_response.raise_for_status = lambda: None
    success_response.json = lambda: {
        'routes': [{
            'distance': 3000,
            'duration': 600,
            'geometry': {'type': 'LineString', 'coordinates': []},
            'legs': [],
        }]
    }

    mock_requests.side_effect = [failing_response, success_response]

    router = OSRMRouter(mode='drive', avoid_tolls=True)
    router.calculer_route(["Adresse 1", "Adresse 2"])

    first_url = mock_requests.call_args_list[0][0][0]
    second_url = mock_requests.call_args_list[1][0][0]

    assert "exclude=toll" in first_url
    assert "exclude=toll" not in second_url
    assert router.toll_fallback_used is True
