from route_planner.vehicule import Vehicule
from route_planner.route_planner import RoutePlanner
from unittest.mock import MagicMock

def test_generer_parcours():
    vehicule = Vehicule('drive', 0.05, 2)
    planner = RoutePlanner(vehicule, methode_routage='osrm')

    # Mock des attributs d'instance après création
    planner.router = MagicMock()
    planner.exporter = MagicMock()

    planner.router.calculer_route.return_value = ([(0,0)], {}, 10, 0.2, [])

    planner.generer_parcours(["A", "B"], "test_output")

    planner.exporter.exporter.assert_called_once()


def test_planifier_parcours_optimise_ordre():
    vehicule = Vehicule("drive", 0.05, 2)
    planner = RoutePlanner(vehicule, methode_routage="osrm")

    class FakeRouter:
        def geocode(self, adresse):
            mapping = {
                "A": (0.0, 0.0),
                "B": (0.0, 3.0),
                "C": (0.0, 1.0),
                "D": (0.0, 4.0),
            }
            return mapping[adresse]

        def distance_matrix(self, adresses, coordinates=None):
            return {
                "distance": [
                    [0, 10, 1, 100],
                    [10, 0, 1, 1],
                    [1, 1, 0, 10],
                    [100, 1, 10, 0],
                ],
                "duration": [
                    [0, 10, 1, 100],
                    [10, 0, 1, 1],
                    [1, 1, 0, 10],
                    [100, 1, 10, 0],
                ],
            }

        def calculer_route(self, adresses, coordinates=None):
            return coordinates, {"type": "LineString", "coordinates": []}, 12, 0.25, [
                {"depart": adresses[0], "arrivee": adresses[1], "distance_km": 1, "duree_h": 0.1, "resume": ""},
                {"depart": adresses[1], "arrivee": adresses[2], "distance_km": 1, "duree_h": 0.1, "resume": ""},
                {"depart": adresses[2], "arrivee": adresses[3], "distance_km": 1, "duree_h": 0.05, "resume": ""},
            ]

    planner.router = FakeRouter()
    plan = planner.planifier_parcours(["A", "B", "C", "D"])

    assert plan.ordered_addresses == ["A", "C", "B", "D"]
    assert plan.optimization_strategy == "exact_dp"
    assert plan.distance_km == 12


def test_planifier_parcours_shortest_km():
    vehicule = Vehicule("drive", 0.05, 2)
    planner = RoutePlanner(vehicule, methode_routage="osrm", objective="shortest_km")

    class FakeRouter:
        def geocode(self, adresse):
            return {"A": (0.0, 0.0), "B": (0.0, 3.0), "C": (0.0, 1.0), "D": (0.0, 4.0)}[adresse]

        def distance_matrix(self, adresses, coordinates=None):
            return {
                "distance": [
                    [0, 10, 1, 100],
                    [10, 0, 1, 1],
                    [1, 1, 0, 10],
                    [100, 1, 10, 0],
                ],
                "duration": [
                    [0, 1, 10, 1],
                    [1, 0, 1, 10],
                    [10, 1, 0, 1],
                    [1, 10, 1, 0],
                ],
            }

        def calculer_route(self, adresses, coordinates=None):
            return coordinates, {"type": "LineString", "coordinates": []}, 5, 0.1, [
                {"depart": adresses[0], "arrivee": adresses[1], "distance_km": 1, "duree_h": 0.1, "resume": ""},
                {"depart": adresses[1], "arrivee": adresses[2], "distance_km": 1, "duree_h": 0.1, "resume": ""},
                {"depart": adresses[2], "arrivee": adresses[3], "distance_km": 1, "duree_h": 0.1, "resume": ""},
            ]

    planner.router = FakeRouter()
    plan = planner.planifier_parcours(["A", "B", "C", "D"])

    assert plan.preferences["objective"] == "shortest_km"
    assert plan.ordered_addresses == ["A", "C", "B", "D"]


def test_planifier_parcours_budget_warning():
    vehicule = Vehicule("drive", 0.05, 2)
    planner = RoutePlanner(vehicule, methode_routage="osrm", budget_eur=0.1)

    class FakeRouter:
        def geocode(self, adresse):
            return {"A": (0.0, 0.0), "B": (0.0, 1.0)}[adresse]

        def calculer_route(self, adresses, coordinates=None):
            return coordinates, {"type": "LineString", "coordinates": []}, 10, 0.2, [
                {"depart": "A", "arrivee": "B", "distance_km": 10, "duree_h": 0.2, "resume": ""}
            ]

    planner.router = FakeRouter()
    plan = planner.planifier_parcours(["A", "B"])

    assert not plan.budget_within
    assert plan.budget_limit_eur == 0.1
    assert plan.warnings


def test_budget_is_ignored_for_bike_and_walk():
    for mode in ("bike", "walk"):
        vehicule = Vehicule(mode, 0.05, 2)
        planner = RoutePlanner(vehicule, methode_routage="osrm", budget_eur=123.45)

        class FakeRouter:
            def geocode(self, adresse):
                return {"A": (0.0, 0.0), "B": (0.0, 1.0)}[adresse]

            def calculer_route(self, adresses, coordinates=None):
                return coordinates, {"type": "LineString", "coordinates": []}, 10, 0.2, [
                    {"depart": "A", "arrivee": "B", "distance_km": 10, "duree_h": 0.2, "resume": ""}
                ]

        planner.router = FakeRouter()
        plan = planner.planifier_parcours(["A", "B"])

        assert plan.budget_limit_eur is None
        assert plan.budget_within
        assert plan.preferences["objective"] == "fastest"
        assert plan.preferences["transport_mode"] == mode
        assert plan.preferences["avoid_tolls"] is False


def test_non_drive_modes_neutralize_cost_and_cheapest_objective():
    for mode in ("bike", "walk"):
        vehicule = Vehicule(mode, 0.05, 2)
        planner = RoutePlanner(vehicule, methode_routage="osrm", objective="cheapest")

        class FakeRouter:
            def geocode(self, adresse):
                return {"A": (0.0, 0.0), "B": (0.0, 1.0)}[adresse]

            def calculer_route(self, adresses, coordinates=None):
                return coordinates, {"type": "LineString", "coordinates": []}, 10, 0.5, [
                    {"depart": "A", "arrivee": "B", "distance_km": 10, "duree_h": 0.5, "resume": ""}
                ]

        planner.router = FakeRouter()
        plan = planner.planifier_parcours(["A", "B"])

        assert plan.cost_eur == 0.0
        assert plan.stats["cost_eur"] == 0.0
        assert plan.preferences["objective"] == "fastest"
        assert plan.stats["co2_car_kg"] > 0
