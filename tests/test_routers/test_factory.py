import pytest
from route_planner.routers.factory import RouterFactory
from route_planner.routers.osrm_router import OSRMRouter
from route_planner.routers.http_routers import BRouter, GraphHopperRouter, ValhallaRouter

def test_get_osrm_router():
    router = RouterFactory.get_router('osrm', 'drive')
    assert isinstance(router, OSRMRouter)


@pytest.mark.parametrize(
    ("method", "router_type"),
    [
        ("valhalla", ValhallaRouter),
        ("graphhopper", GraphHopperRouter),
        ("brouter", BRouter),
    ],
)
def test_get_additional_http_routers(method, router_type):
    router = RouterFactory.get_router(method, "bike")

    assert isinstance(router, router_type)
    assert router.mode == "bike"


def test_factory_passes_router_options():
    valhalla = RouterFactory.get_router(
        "valhalla",
        "drive",
        router_options={"valhalla_url": "http://valhalla.local"},
    )
    graphhopper = RouterFactory.get_router(
        "graphhopper",
        "drive",
        router_options={
            "graphhopper_url": "http://graphhopper.local",
            "graphhopper_api_key": "secret",
        },
    )
    brouter = RouterFactory.get_router(
        "brouter",
        "bike",
        router_options={"brouter_url": "http://brouter.local"},
    )

    assert valhalla.base_url == "http://valhalla.local"
    assert graphhopper.base_url == "http://graphhopper.local"
    assert graphhopper.api_key == "secret"
    assert brouter.base_url == "http://brouter.local"


def test_router_inconnu():
    with pytest.raises(ValueError):
        RouterFactory.get_router('unknown', 'drive')
