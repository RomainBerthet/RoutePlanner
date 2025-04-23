from vehicule import Vehicule
from route_planner import RoutePlanner

if __name__ == "__main__":
    adresses = [
        "17, rue nationale 39500 Tavaux",
        "route de vienne 69008 Lyon",
        "Venice, Italy",
    ]

    vehicule = Vehicule(type_transport='drive', consommation_l_km=0.06, cout_energie=1.8)

    planner = RoutePlanner(vehicule, methode_routage='osrm')
    planner.generer_parcours(adresses, "parcours_paris")
