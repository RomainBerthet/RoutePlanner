from route_planner.vehicule import Vehicule
from route_planner.route_planner import RoutePlanner
from unittest.mock import MagicMock

def test_generer_parcours():
    vehicule = Vehicule('drive', 0.05, 2)
    planner = RoutePlanner(vehicule, methode_routage='osrm')

    # Mock des attributs d'instance après création
    planner.router = MagicMock()
    planner.exporter = MagicMock()

    planner.router.calculer_route.return_value = ([(0,0)], {}, 10, 0.2)

    planner.generer_parcours(["A", "B"], "test_output")

    planner.exporter.exporter.assert_called_once()
