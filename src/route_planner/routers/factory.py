from .osrm_router import OSRMRouter
from .osmnx_router import OSMnxRouter

class RouterFactory:
    @staticmethod
    def get_router(methode: str, mode: str):
        if methode == 'osrm':
            return OSRMRouter(mode)
        elif methode == 'osmnx':
            return OSMnxRouter(mode)
        else:
            raise ValueError(f"Méthode inconnue : {methode}")
