from unittest.mock import patch

import pytest

from route_planner.routers.http_routers import BRouter, GraphHopperRouter, ValhallaRouter


def test_valhalla_route_payload_uses_mode_and_tolls():
    router = ValhallaRouter("drive", avoid_tolls=True, base_url="http://valhalla.test")
    payload = router._route_payload([(48.0, 2.0), (48.1, 2.1)])

    assert payload["costing"] == "auto"
    assert payload["costing_options"] == {"auto": {"use_tolls": 0}}
    assert payload["locations"] == [{"lat": 48.0, "lon": 2.0}, {"lat": 48.1, "lon": 2.1}]


@patch("route_planner.routers.http_routers.requests.post")
def test_valhalla_calculer_route(mock_post):
    mock_post.return_value.json.return_value = {
        "trip": {
            "summary": {"length": 2.5, "time": 600},
            "shape": {"type": "LineString", "coordinates": [[2.0, 48.0], [2.1, 48.1]]},
            "legs": [{"summary": {"length": 2.5, "time": 600, "text": "Route"}}],
        }
    }
    router = ValhallaRouter("bike", base_url="http://valhalla.test")

    _, geometry, distance_km, duration_h, legs = router.calculer_route(
        ["A", "B"],
        coordinates=[(48.0, 2.0), (48.1, 2.1)],
    )

    assert geometry["type"] == "LineString"
    assert distance_km == 2.5
    assert round(duration_h, 3) == 0.167
    assert legs[0]["resume"] == "Route"


@patch("route_planner.routers.http_routers.requests.get")
def test_graphhopper_calculer_route(mock_get):
    mock_get.return_value.json.return_value = {
        "paths": [{
            "distance": 3000,
            "time": 600000,
            "points": {"type": "LineString", "coordinates": [[2.0, 48.0], [2.1, 48.1]]},
        }]
    }
    router = GraphHopperRouter("walk", base_url="http://graphhopper.test", api_key="")

    _, geometry, distance_km, duration_h, _ = router.calculer_route(
        ["A", "B"],
        coordinates=[(48.0, 2.0), (48.1, 2.1)],
    )

    assert geometry["type"] == "LineString"
    assert distance_km == 3
    assert round(duration_h, 3) == 0.167
    params = mock_get.call_args.kwargs["params"]
    assert ("vehicle", "foot") in params


def test_graphhopper_public_api_requires_key_for_route():
    router = GraphHopperRouter("drive", api_key="")

    with pytest.raises(ValueError):
        router.calculer_route(["A", "B"], coordinates=[(48.0, 2.0), (48.1, 2.1)])


@patch("route_planner.routers.http_routers.requests.get")
def test_brouter_calculer_route(mock_get):
    mock_get.return_value.json.return_value = {
        "features": [{
            "geometry": {"type": "LineString", "coordinates": [[2.0, 48.0], [2.1, 48.1]]},
            "properties": {"track-length": 4000, "total-time": 1200},
        }]
    }
    router = BRouter("bike", base_url="http://brouter.test")

    _, geometry, distance_km, duration_h, _ = router.calculer_route(
        ["A", "B"],
        coordinates=[(48.0, 2.0), (48.1, 2.1)],
    )

    assert geometry["type"] == "LineString"
    assert distance_km == 4
    assert round(duration_h, 3) == 0.333
    assert mock_get.call_args.kwargs["params"]["profile"] == "trekking"
