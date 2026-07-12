from types import SimpleNamespace

import pytest

from route_planner.ai.service import TravelIntelligence
from route_planner.recommendations.models import PointOfInterest, StopRecommendations


def _plan():
    return SimpleNamespace(
        preferences={"transport_mode": "drive"},
        distance_km=2150.0,
        duration_h=22.5,
        cost_eur=270.0,
        ordered_addresses=["Tavaux", "Ascona", "Piran"],
    )


def test_suggest_itinerary_returns_structured_plan(fake_provider):
    service = TravelIntelligence(fake_provider)
    suggestion = service.suggest_itinerary("Road trip lacs depuis Tavaux, en voiture")

    assert suggestion.stops[0] == "Tavaux, France"
    assert suggestion.transport_mode == "drive"
    assert suggestion.title == "Escapade lacs"
    # The planner system prompt drove the JSON call.
    assert "planificateur" in fake_provider.json_calls[0]["system"]


def test_suggest_itinerary_rejects_too_few_stops():
    provider = SimpleNamespace(
        complete_json=lambda system, user, schema, max_tokens=4096: {
            "stops": ["only one"],
            "transport_mode": "drive",
            "objective": "balanced",
            "title": "x",
        },
        complete_text=lambda *a, **k: "",
    )
    with pytest.raises(ValueError):
        TravelIntelligence(provider).suggest_itinerary("trop court")


def test_suggest_itinerary_caps_stops():
    stops = [f"Ville {i}" for i in range(20)]
    provider = SimpleNamespace(
        complete_json=lambda system, user, schema, max_tokens=4096: {
            "stops": stops,
            "transport_mode": "drive",
            "objective": "balanced",
            "title": "x",
        },
        complete_text=lambda *a, **k: "",
    )
    suggestion = TravelIntelligence(provider).suggest_itinerary("beaucoup", max_stops=5)
    assert len(suggestion.stops) == 5


def test_write_guide_content_uses_plan_and_recommendations(fake_provider):
    service = TravelIntelligence(fake_provider)
    recs = [
        StopRecommendations(
            "Piran",
            (45.5, 13.5),
            [PointOfInterest("Punta", "sight", 45.5, 13.5, {}, "node", 1)],
            index=2,
        )
    ]
    content = service.write_guide_content(_plan(), recs, request="détente")

    assert content.intro
    assert content.budget.total == "≈ 1200 €"
    # The prompt embedded the itinerary and the reperage of POIs.
    guide_prompt = fake_provider.json_calls[0]["user"]
    assert "Tavaux" in guide_prompt and "Punta" in guide_prompt
    assert "détente" in guide_prompt
