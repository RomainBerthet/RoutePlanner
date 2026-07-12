from route_planner.ai.models import GuideContent, ItinerarySuggestion


def test_itinerary_normalizes_invalid_mode_and_objective():
    s = ItinerarySuggestion.from_dict(
        {"stops": ["A", "B"], "transport_mode": "teleport", "objective": "vibes"}
    )
    assert s.transport_mode == "drive"
    assert s.objective == "balanced"


def test_itinerary_strips_and_drops_blank_stops():
    s = ItinerarySuggestion.from_dict({"stops": ["  A ", "", "B", "  "]})
    assert s.stops == ["A", "B"]


def test_guide_content_parses_all_sections():
    gc = GuideContent.from_dict(
        {
            "intro": "hi",
            "tips": [{"title": "t", "body": "b"}],
            "vigilance": [{"title": "v", "body": "b"}],
            "practical": [{"title": "p", "body": "b"}],
            "secrets": [{"name": "s", "body": "b", "gps": "1,2"}],
            "budget": {"rows": [{"label": "l", "amount": "5 €"}], "total": "5 €"},
        }
    )
    assert gc.intro == "hi"
    assert gc.tips[0].title == "t"
    assert gc.secrets[0].gps == "1,2"
    assert gc.budget.total == "5 €"
    assert not gc.is_empty


def test_guide_content_is_empty_when_blank():
    assert GuideContent.from_dict({}).is_empty


def test_guide_content_tolerates_missing_budget():
    gc = GuideContent.from_dict({"intro": "x"})
    assert gc.budget is None
