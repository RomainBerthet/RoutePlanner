
from routers.factory import RouterFactory
from exporters.html_exporter import HTMLExporter

class RoutePlanner:
    def __init__(self, vehicule, methode_routage):
        self.vehicule = vehicule
        self.router = RouterFactory.get_router(methode_routage, vehicule.type_transport)
        self.exporter = HTMLExporter()

    def generer_parcours(self, adresses, filename):
        coords, geometry, distance_km, temps_h = self.router.calculer_route(adresses)
        cout = distance_km * self.vehicule.consommation_l_km * self.vehicule.cout_energie

        self.exporter.exporter(coords, geometry, filename)

        print(f"Parcours généré : {filename}.html")
        print(f"Distance : {distance_km:.2f} km")
        print(f"Temps estimé : {temps_h*60:.1f} min")
        print(f"Coût estimé : {cout:.2f} €")
