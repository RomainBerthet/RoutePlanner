from route_planner.models import RouteLeg, RoutePlan
from route_planner.webapp import _parse_addresses, _render_form, _render_result


def test_parse_addresses_requires_two_entries():
    payload = {"addresses": ["A", "B", "C"]}

    assert _parse_addresses(payload) == ["A", "B", "C"]


def test_render_result_contains_stats():
    plan = RoutePlan(
        requested_addresses=["A", "B"],
        ordered_addresses=["A", "B"],
        coordinates=[(48.0, 2.0), (48.1, 2.1)],
        geometry={"type": "LineString", "coordinates": [[2.0, 48.0], [2.1, 48.1]]},
        distance_km=12.34,
        duration_h=0.5,
        cost_eur=3.21,
        legs=[RouteLeg("A", "B", 12.34, 0.5, "summary")],
        routing_engine="OSRMRouter",
        optimization_strategy="exact_dp",
        preferences={"transport_mode": "drive", "objective": "fastest", "avoid_tolls": True},
    )

    plan.stats = {
        "average_speed_kmh": 24.68,
        "distance_km": 12.34,
        "duration_min": 30.0,
        "cost_eur": 3.21,
        "co2_car_kg": 2.848,
        "co2_saved_vs_car_bike_kg": 2.848,
        "co2_saved_vs_car_walk_kg": 2.848,
        "carbon_intensity_g_per_km": 230.9,
    }

    status, headers, body = _render_result(plan, {"html": "/files/route.html", "json": "/files/route.json", "pdf": "/files/route.pdf"})

    assert status == "200 OK"
    assert any(name == "Content-Type" for name, _ in headers)
    html = body.decode("utf-8")
    assert "12.34 km" in html
    assert "30.0 min" in html
    assert "exact_dp" in html
    assert "Télécharger HTML" in html
    assert "Feuille de route PDF" in html
    assert "Données JSON" in html
    assert "Coût total" in html
    assert "CO2 voiture" in html
    assert "Intensite carbone" in html
    assert "CO2 economise velo" not in html
    assert "CO2 economise marche" not in html


def test_render_result_hides_none_optimization():
    plan = RoutePlan(
        requested_addresses=["A", "B"],
        ordered_addresses=["A", "B"],
        coordinates=[(48.0, 2.0), (48.1, 2.1)],
        geometry={"type": "LineString", "coordinates": [[2.0, 48.0], [2.1, 48.1]]},
        distance_km=12.34,
        duration_h=0.5,
        cost_eur=3.21,
        legs=[RouteLeg("A", "B", 12.34, 0.5, "summary")],
        routing_engine="OSRMRouter",
        optimization_strategy="none",
        preferences={"transport_mode": "drive", "objective": "fastest", "avoid_tolls": False},
    )
    plan.stats = {
        "average_speed_kmh": 24.68,
        "distance_km": 12.34,
        "duration_min": 30.0,
        "cost_eur": 3.21,
        "co2_car_kg": 2.848,
        "carbon_intensity_g_per_km": 230.9,
    }

    _, _, body = _render_result(plan, {"html": "/files/route.html"})

    html = body.decode("utf-8")
    assert "Optimisation" not in html
    assert ">none<" not in html


def test_render_result_bike_stats_are_mode_specific():
    plan = RoutePlan(
        requested_addresses=["A", "B"],
        ordered_addresses=["A", "B"],
        coordinates=[(48.0, 2.0), (48.1, 2.1)],
        geometry={"type": "LineString", "coordinates": [[2.0, 48.0], [2.1, 48.1]]},
        distance_km=12.34,
        duration_h=0.5,
        cost_eur=0.0,
        legs=[RouteLeg("A", "B", 12.34, 0.5, "summary")],
        routing_engine="OSRMRouter",
        optimization_strategy="exact_dp",
        preferences={"transport_mode": "bike", "objective": "fastest", "avoid_tolls": False},
    )
    plan.stats = {
        "average_speed_kmh": 24.68,
        "distance_km": 12.34,
        "duration_min": 30.0,
        "calories_estimees_kcal": 210.5,
        "co2_saved_vs_car_bike_kg": 2.848,
        "distance_par_heure_km": 24.68,
    }

    _, _, body = _render_result(plan, {"html": "/files/route.html", "json": "/files/route.json", "pdf": "/files/route.pdf"})

    html = body.decode("utf-8")
    assert "Calories estimees" in html
    assert "Distance par heure" in html
    assert "Coût total" not in html
    assert "Péages" not in html


def test_render_result_walk_stats_are_mode_specific():
    plan = RoutePlan(
        requested_addresses=["A", "B"],
        ordered_addresses=["A", "B"],
        coordinates=[(48.0, 2.0), (48.1, 2.1)],
        geometry={"type": "LineString", "coordinates": [[2.0, 48.0], [2.1, 48.1]]},
        distance_km=12.34,
        duration_h=0.5,
        cost_eur=0.0,
        legs=[RouteLeg("A", "B", 12.34, 0.5, "summary")],
        routing_engine="OSRMRouter",
        optimization_strategy="exact_dp",
        preferences={"transport_mode": "walk", "objective": "fastest", "avoid_tolls": False},
    )
    plan.stats = {
        "average_speed_kmh": 24.68,
        "distance_km": 12.34,
        "duration_min": 30.0,
        "calories_estimees_kcal": 123.4,
        "pas_estimes": 16200,
        "temps_par_km_min": 2.4,
        "co2_saved_vs_car_walk_kg": 2.848,
    }

    _, _, body = _render_result(plan, {"html": "/files/route.html", "json": "/files/route.json", "pdf": "/files/route.pdf"})

    html = body.decode("utf-8")
    assert "Calories estimees" in html
    assert "Pas estimees" in html
    assert "Temps par km" in html
    assert "Coût total" not in html
    assert "Péages" not in html


def test_render_form_exposes_objective_controls():
    _, _, body = _render_form()
    html = body.decode("utf-8")

    assert 'name="objective"' in html
    assert 'name="budget"' in html
    assert 'name="avoid_tolls"' in html
    assert 'data-modes="drive"' in html
    assert 'Parametres disponibles uniquement pour la voiture.' in html
    assert 'Les peages ne sont pas pertinents en velo' in html
    assert 'La marche retire elle aussi budget et peages' in html
    assert 'name="output"' not in html
    assert 'name="json_output"' not in html


def test_render_form_exposes_router_configuration_fields():
    _, _, body = _render_form()
    html = body.decode("utf-8")

    assert 'name="valhalla_url"' in html
    assert 'name="graphhopper_url"' in html
    assert 'name="graphhopper_api_key"' in html
    assert 'name="brouter_url"' in html
    assert 'class="method-config" data-methods="valhalla"' in html
    assert 'class="method-config" data-methods="graphhopper"' in html
    assert 'class="method-config" data-methods="brouter"' in html
