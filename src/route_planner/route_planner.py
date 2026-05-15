from route_planner.routers.factory import RouterFactory
from route_planner.exporters.html_exporter import HTMLExporter
from route_planner.models import RouteLeg, RoutePlan, RoutePreferences
from route_planner.optimization import solve_open_route


MODE_OBJECTIVES = {
    "drive": {"fastest", "shortest_km", "cheapest", "balanced"},
    "bike": {"fastest", "shortest_km", "balanced"},
    "walk": {"fastest", "shortest_km", "balanced"},
}


class RoutePlanner:
    def __init__(
        self,
        vehicule,
        methode_routage,
        objective="fastest",
        avoid_tolls=False,
        budget_eur=None,
        balanced_weight=0.5,
        router_options=None,
    ):
        self.vehicule = vehicule
        self.objective = self._normalize_objective(objective)
        self.avoid_tolls = avoid_tolls and vehicule.type_transport == "drive"
        self.budget_eur = budget_eur if vehicule.type_transport == "drive" else None
        self.balanced_weight = min(1.0, max(0.0, balanced_weight))
        self.router_options = router_options or {}
        self.router = RouterFactory.get_router(
            methode_routage,
            vehicule.type_transport,
            avoid_tolls=self.avoid_tolls,
            router_options=self.router_options,
        )
        self.exporter = HTMLExporter()

    def planifier_parcours(self, adresses, objective=None, budget_eur=None):
        if len(adresses) < 2:
            raise ValueError("Il faut au moins deux adresses")

        objective = self._normalize_objective(objective or self.objective)
        budget_eur = self.budget_eur if budget_eur is None else budget_eur
        if self.vehicule.type_transport in {"bike", "walk"}:
            budget_eur = None
        plan = self._build_plan(adresses, objective, budget_eur)
        if (
            budget_eur is not None
            and not plan.budget_within
            and objective != "cheapest"
        ):
            fallback_plan = self._build_plan(adresses, "cheapest", budget_eur)
            fallback_plan.warnings.append(
                "Budget depasse avec l'objectif choisi; recalcul effectue en mode economique."
            )
            if fallback_plan.cost_eur <= plan.cost_eur:
                plan = fallback_plan
            else:
                plan.warnings.append(
                    "Le recalcul economique n'a pas reduit le cout."
                )
                plan.preferences["fallback_objective"] = "cheapest"
        return plan

    def _build_plan(self, adresses, objective, budget_eur):
        ordered_adresses = list(adresses)
        optimization_strategy = "none"
        warnings = []

        coordinates = [self.router.geocode(adresse) for adresse in adresses]
        if len(adresses) > 2:
            matrix_data = self.router.distance_matrix(adresses, coordinates=coordinates)
            objective_matrix = self._objective_matrix(matrix_data, objective)
            order, optimization_strategy = solve_open_route(objective_matrix)
            ordered_adresses = [adresses[index] for index in order]
            ordered_coordinates = [coordinates[index] for index in order]
            coords, geometry, distance_km, temps_h, etapes = self.router.calculer_route(
                ordered_adresses, coordinates=ordered_coordinates
            )
        else:
            coords, geometry, distance_km, temps_h, etapes = self.router.calculer_route(ordered_adresses)

        cout_total = self._transport_cost(distance_km)
        budget_within = budget_eur is None or cout_total <= budget_eur
        budget_gap = 0.0 if budget_eur is None else max(0.0, cout_total - budget_eur)
        if budget_eur is not None and not budget_within:
            warnings.append(f"Budget depasse de {budget_gap:.2f} €")
        if self.avoid_tolls:
            if getattr(self.router, "toll_fallback_used", False):
                warnings.append(
                    "Le serveur OSRM public a refuse exclude=toll; recalcul effectue sans cette option."
                )
            elif not getattr(self.router, "_should_exclude_tolls", lambda: False)():
                warnings.append("Eviter les peages est supporte par OSRM uniquement; option ignoree par ce moteur.")

        stats = self._build_stats(distance_km, temps_h, cout_total)

        return RoutePlan(
            requested_addresses=list(adresses),
            ordered_addresses=ordered_adresses,
            coordinates=coords,
            geometry=geometry,
            distance_km=distance_km,
            duration_h=temps_h,
            cost_eur=cout_total,
            legs=[RouteLeg(**etape) for etape in etapes],
            routing_engine=self.router.__class__.__name__,
            optimization_strategy=optimization_strategy,
            preferences=RoutePreferences(
                transport_mode=self.vehicule.type_transport,
                objective=objective,
                avoid_tolls=self.avoid_tolls,
                budget_eur=budget_eur,
                balanced_weight=self.balanced_weight,
            ).to_dict(),
            warnings=warnings,
            budget_limit_eur=budget_eur,
            budget_within=budget_within,
            budget_gap_eur=budget_gap,
            stats=stats,
        )

    def generer_parcours(self, adresses, filename):
        plan = self.planifier_parcours(adresses)

        self.exporter.exporter(plan, filename=filename)

        print(f"Parcours généré : {filename}.html")
        print(f"Distance totale : {plan.distance_km:.2f} km")
        print(f"Temps estimé total : {plan.duration_h * 60:.1f} min")
        print(f"Coût total estimé : {plan.cost_eur:.2f} €")
        print(f"Ordre optimisé : {' -> '.join(plan.ordered_addresses)}")
        print(f"Objectif : {plan.preferences.get('objective', 'fastest')}")
        if plan.preferences.get("avoid_tolls"):
            print("Péages évités lorsque supporté par le moteur")
        if plan.budget_limit_eur is not None:
            print(f"Budget : {plan.budget_limit_eur:.2f} €")
            print("Budget respecté" if plan.budget_within else f"Budget dépassé de {plan.budget_gap_eur:.2f} €")

        print("\nDétails par étape :")
        for step in plan.legs:
            print(f"Étape {step.depart} -> {step.arrivee}:")
            print(f"  Distance : {step.distance_km} km")
            print(f"  Durée : {step.duree_h * 60:.1f} min")
            print(f"  Résumé : {step.resume}")

        print("\nStatistiques:")
        for key, value in plan.stats.items():
            print(f"  {key} : {value}")

        return plan

    def _objective_matrix(self, matrix_data, objective):
        objective = self._normalize_objective(objective)
        distance = matrix_data["distance"]
        duration = matrix_data["duration"]
        if objective == "fastest":
            return duration
        if objective == "shortest_km":
            return distance
        if objective == "cheapest":
            return [
                [None if value is None else value * self.vehicule.consommation_l_km * self.vehicule.cout_energie for value in row]
                for row in distance
            ]
        if objective == "balanced":
            return self._balanced_matrix(distance, duration)
        return duration

    def _normalize_objective(self, objective):
        allowed = MODE_OBJECTIVES.get(self.vehicule.type_transport, MODE_OBJECTIVES["drive"])
        return objective if objective in allowed else "fastest"

    def _transport_cost(self, distance_km):
        if self.vehicule.type_transport != "drive":
            return 0.0
        return distance_km * self.vehicule.consommation_l_km * self.vehicule.cout_energie

    def _balanced_matrix(self, distance_matrix, duration_matrix):
        flat_distance = [value for row in distance_matrix for value in row if value is not None]
        flat_duration = [value for row in duration_matrix for value in row if value is not None]
        max_distance = max(flat_distance) if flat_distance else 1.0
        max_duration = max(flat_duration) if flat_duration else 1.0

        result = []
        for d_row, t_row in zip(distance_matrix, duration_matrix):
            row = []
            for distance_value, duration_value in zip(d_row, t_row):
                if distance_value is None or duration_value is None:
                    row.append(None)
                else:
                    norm_distance = distance_value / max_distance if max_distance else 0.0
                    norm_duration = duration_value / max_duration if max_duration else 0.0
                    row.append(
                        self.balanced_weight * norm_duration
                        + (1 - self.balanced_weight) * norm_distance
                    )
            result.append(row)
        return result

    def _build_stats(self, distance_km, duration_h, cost_eur):
        speed_kmh = distance_km / duration_h if duration_h > 0 else 0.0
        reference_consumption = self.vehicule.consommation_l_km or 0.06
        car_co2 = distance_km * reference_consumption * self.vehicule.co2_kg_par_litre
        bike_co2 = distance_km * self.vehicule.co2_kg_par_km_bike
        walk_co2 = distance_km * self.vehicule.co2_kg_par_km_walk
        stats = {
            "average_speed_kmh": round(speed_kmh, 2),
            "distance_km": round(distance_km, 2),
            "duration_min": round(duration_h * 60, 1),
            "cost_eur": round(cost_eur, 2),
            "co2_car_kg": round(car_co2, 3),
            "co2_bike_kg": round(bike_co2, 3),
            "co2_walk_kg": round(walk_co2, 3),
            "co2_saved_vs_car_bike_kg": round(max(0.0, car_co2 - bike_co2), 3),
            "co2_saved_vs_car_walk_kg": round(max(0.0, car_co2 - walk_co2), 3),
            "carbon_intensity_g_per_km": round((car_co2 / distance_km * 1000) if distance_km > 0 else 0.0, 2),
        }
        if self.vehicule.type_transport == "bike":
            stats.update(self._bike_stats(distance_km, duration_h))
        elif self.vehicule.type_transport == "walk":
            stats.update(self._walk_stats(distance_km, duration_h))
        return stats

    def _bike_stats(self, distance_km, duration_h):
        weight_kg = 70.0
        met = 6.8
        calories = met * weight_kg * duration_h
        return {
            "calories_estimees_kcal": round(calories, 1),
            "distance_par_heure_km": round(distance_km / duration_h, 2) if duration_h > 0 else 0.0,
        }

    def _walk_stats(self, distance_km, duration_h):
        weight_kg = 70.0
        met = 3.5
        calories = met * weight_kg * duration_h
        steps = int(distance_km * 1312.0)
        return {
            "calories_estimees_kcal": round(calories, 1),
            "pas_estimes": steps,
            "temps_par_km_min": round((duration_h * 60 / distance_km), 1) if distance_km > 0 else 0.0,
        }
