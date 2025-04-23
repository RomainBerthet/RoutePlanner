def main():
    from route_planner.vehicule import Vehicule
    from route_planner.route_planner import RoutePlanner

    adresses = [
        "Tour Eiffel, Paris",
        "Louvre, Paris",
        "Notre-Dame de Paris"
    ]

    vehicule = Vehicule(type_transport='drive', consommation_l_km=0.06, cout_energie=1.8)
    planner = RoutePlanner(vehicule, methode_routage='osrm')
    planner.generer_parcours(adresses, "parcours_paris")

if __name__ == "__main__":
    main()