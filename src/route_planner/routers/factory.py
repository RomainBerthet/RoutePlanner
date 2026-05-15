from .osrm_router import OSRMRouter
from .osmnx_router import OSMnxRouter
from .http_routers import BRouter, GraphHopperRouter, ValhallaRouter

class RouterFactory:
    @staticmethod
    def get_router(methode: str, mode: str, avoid_tolls: bool = False, cache=None, router_options=None):
        router_options = router_options or {}
        if methode == 'osrm':
            return OSRMRouter(mode, avoid_tolls=avoid_tolls, cache=cache)
        elif methode == 'osmnx':
            return OSMnxRouter(mode, avoid_tolls=avoid_tolls, cache=cache)
        elif methode == 'valhalla':
            return ValhallaRouter(
                mode,
                avoid_tolls=avoid_tolls,
                cache=cache,
                base_url=router_options.get("valhalla_url"),
            )
        elif methode == 'graphhopper':
            return GraphHopperRouter(
                mode,
                avoid_tolls=avoid_tolls,
                cache=cache,
                base_url=router_options.get("graphhopper_url"),
                api_key=router_options.get("graphhopper_api_key"),
            )
        elif methode == 'brouter':
            return BRouter(
                mode,
                avoid_tolls=avoid_tolls,
                cache=cache,
                base_url=router_options.get("brouter_url"),
            )
        else:
            raise ValueError(f"Méthode inconnue : {methode}")
