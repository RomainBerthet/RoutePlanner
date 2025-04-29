from route_planner.routers.factory import RouterFactory
from route_planner.exporters.html_exporter import HTMLExporter


class RoutePlanner:
    def __init__(self, vehicule, methode_routage):
        self.vehicule = vehicule
        self.router = RouterFactory.get_router(methode_routage, vehicule.type_transport)
        self.exporter = HTMLExporter()

    def generer_parcours(self, adresses, filename):
        coords, geometry, distance_km, temps_h, etapes = self.router.calculer_route(adresses)
        cout_total = distance_km * self.vehicule.consommation_l_km * self.vehicule.cout_energie

        self.exporter.exporter(coords, geometry, filename)

        print(f"Parcours généré : {filename}.html")
        print(f"Distance totale : {distance_km:.2f} km")
        print(f"Temps estimé total : {temps_h * 60:.1f} min")
        print(f"Coût total estimé : {cout_total:.2f} €")

        print("\nDétails par étape :")
        for i in etapes:
            print(f"Étape {i['depart']} -> {i['arrivee']}:")
            print(f"  Distance : {i['distance_km']} km")
            print(f"  Durée : {i['duree_h'] * 60:.1f} min")
            print(f"  Résumé : {i['resume']}")
