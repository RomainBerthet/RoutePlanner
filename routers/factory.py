
from .osrm_router import OSRMRouter

class RouterFactory:
    @staticmethod
    def get_router(methode: str, mode: str):
        if methode == 'osrm':
            return OSRMRouter(mode)
        else:
            raise ValueError(f"Méthode inconnue : {methode}")
