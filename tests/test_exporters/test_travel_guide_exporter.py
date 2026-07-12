from route_planner.exporters.travel_guide_exporter import TravelGuideExporter
from route_planner.models import RoutePlan, RouteLeg
from route_planner.recommendations.models import PointOfInterest, StopRecommendations


def _plan():
    coords = [(47.0, 5.5), (46.1, 8.7), (45.5, 13.5)]
    labels = ["Tavaux, France", "Ascona, Suisse", "Piran, Slovénie"]
    legs = [
        RouteLeg(labels[0], labels[1], 350.0, 4.0, "Simplon"),
        RouteLeg(labels[1], labels[2], 400.0, 4.5, "A4"),
    ]
    return RoutePlan(
        requested_addresses=labels,
        ordered_addresses=labels,
        coordinates=coords,
        geometry={},
        distance_km=750.0,
        duration_h=8.5,
        cost_eur=95.0,
        legs=legs,
        routing_engine="OSRMRouter",
        optimization_strategy="exact_dp",
        preferences={"transport_mode": "drive", "objective": "balanced"},
        stats={"average_speed_kmh": 88, "co2_car_kg": 100.0, "cost_eur": 95.0},
    )


def _recommendations():
    return [
        StopRecommendations(
            "Ascona, Suisse",
            (46.1, 8.7),
            [
                PointOfInterest("Isole di Brissago", "sight", 46.13, 8.73, {"wikidata": "Q1"}, "node", 1, 1.2, 5.0),
                PointOfInterest("<Cardada>", "viewpoint", 46.19, 8.80, {}, "node", 2, 0.9, 3.0),
            ],
            index=1,
        ),
    ]


def test_render_contains_core_sections():
    html_doc = TravelGuideExporter().render(_plan(), _recommendations())

    assert "<!doctype html>" in html_doc
    assert "Le parcours en chiffres" in html_doc
    assert "Carte du parcours" in html_doc
    assert "L'itinéraire détaillé" in html_doc
    assert "Que voir, où s'arrêter" in html_doc
    assert "Isole di Brissago" in html_doc


def test_render_is_self_contained_no_remote_assets():
    html_doc = TravelGuideExporter().render(_plan(), _recommendations())

    # No remote scripts/styles/images: Google Maps only appears as click links.
    assert 'src="http' not in html_doc
    assert "<img" not in html_doc
    assert "maps/search" in html_doc  # POI links are present as hrefs


def test_render_escapes_untrusted_names():
    html_doc = TravelGuideExporter().render(_plan(), _recommendations())

    assert "<Cardada>" not in html_doc
    assert "&lt;Cardada&gt;" in html_doc


def test_render_is_theme_aware():
    html_doc = TravelGuideExporter().render(_plan(), _recommendations())

    assert "prefers-color-scheme" in html_doc
    assert '[data-theme="dark"]' in html_doc


def test_map_svg_projects_all_stops():
    html_doc = TravelGuideExporter().render(_plan(), _recommendations())

    assert html_doc.count("<circle") >= 3  # one marker per stop


def test_exporter_writes_html_file(tmp_path):
    out = tmp_path / "carnet"
    path = TravelGuideExporter().exporter(_plan(), _recommendations(), filename=str(out))

    assert path.endswith(".html")
    assert (tmp_path / "carnet.html").read_text(encoding="utf-8").startswith("<!doctype html>")


def test_render_without_recommendations_still_works():
    html_doc = TravelGuideExporter().render(_plan(), [])

    assert "L'itinéraire détaillé" in html_doc
    assert "Que voir" not in html_doc  # address book omitted when empty


def _guide_content():
    from route_planner.ai.models import GuideContent

    return GuideContent.from_dict(
        {
            "intro": "Pas de course, on savoure.",
            "tips": [{"title": "Vignettes", "body": "En ligne avant le départ."}],
            "vigilance": [{"title": "ZTL <Italie>", "body": "Amendes automatiques."}],
            "practical": [{"title": "Piran piéton", "body": "Parking Fornače."}],
            "secrets": [{"name": "Val Verzasca", "zone": "Tessin", "body": "Rivière émeraude.", "gps": "46.25, 8.83"}],
            "budget": {"rows": [{"label": "Carburant", "detail": "2150 km", "amount": "250 €"}], "total": "≈ 1200 €", "note": "À deux : /2"},
        }
    )


def test_render_with_guide_content_adds_ai_sections():
    html_doc = TravelGuideExporter().render(_plan(), [], guide_content=_guide_content())

    assert "Avant de partir" in html_doc  # intro / philosophy
    assert "Astuces &amp; conseils pratiques" in html_doc
    assert "Points de vigilance" in html_doc
    assert "Spots secrets" in html_doc
    assert "Récap budget" in html_doc
    assert "Val Verzasca" in html_doc
    assert "≈ 1200 €" in html_doc


def test_guide_content_names_are_escaped():
    html_doc = TravelGuideExporter().render(_plan(), [], guide_content=_guide_content())

    assert "<Italie>" not in html_doc
    assert "&lt;Italie&gt;" in html_doc


def test_ai_sections_absent_without_guide_content():
    html_doc = TravelGuideExporter().render(_plan(), [])

    assert "Points de vigilance" not in html_doc
    assert "Récap budget" not in html_doc
