import pytest
from route_planner.routers.factory import RouterFactory
from route_planner.routers.osrm_router import OSRMRouter

def test_get_osrm_router():
    router = RouterFactory.get_router('osrm', 'drive')
    assert isinstance(router, OSRMRouter)

def test_router_inconnu():
    with pytest.raises(ValueError):
        RouterFactory.get_router('unknown', 'drive')
