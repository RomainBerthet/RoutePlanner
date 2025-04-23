from abc import ABC, abstractmethod

class IRouter(ABC):
    @abstractmethod
    def calculer_route(self, adresses):
        pass
