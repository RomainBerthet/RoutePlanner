from abc import ABC, abstractmethod

class IRouter(ABC):
    @abstractmethod
    def geocode(self, adresse):
        pass

    @abstractmethod
    def distance_matrix(self, adresses, coordinates=None):
        pass

    @abstractmethod
    def calculer_route(self, adresses, coordinates=None):
        pass
