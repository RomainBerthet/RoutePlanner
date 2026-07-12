import pytest


class FakeLLMProvider:
    """Records calls and returns canned JSON, mimicking any ILLMProvider."""

    def __init__(self, itinerary=None, guide=None):
        self.itinerary = itinerary or {
            "title": "Escapade lacs",
            "subtitle": "3 pays",
            "transport_mode": "drive",
            "objective": "balanced",
            "stops": ["Tavaux, France", "Ascona, Suisse", "Piran, Slovénie"],
            "rationale": "Détente au bord de l'eau",
        }
        self.guide = guide or {
            "intro": "Un voyage tranquille au fil de l'eau.",
            "tips": [{"title": "Vignettes", "body": "À acheter en ligne avant le départ."}],
            "vigilance": [{"title": "ZTL", "body": "Zones à trafic limité en Italie."}],
            "practical": [{"title": "Plein", "body": "Moins cher en Slovénie."}],
            "secrets": [{"name": "Val Verzasca", "zone": "Tessin", "body": "Rivière émeraude.", "gps": "46.25, 8.83"}],
            "budget": {"rows": [{"label": "Carburant", "detail": "2150 km", "amount": "250 €"}], "total": "≈ 1200 €", "note": "À deux : /2"},
        }
        self.json_calls = []
        self.text_calls = []

    def complete_json(self, system, user, schema, max_tokens=4096):
        self.json_calls.append({"system": system, "user": user, "schema": schema})
        return self.itinerary if "planificateur" in system else self.guide

    def complete_text(self, system, user, max_tokens=2048):
        self.text_calls.append(user)
        return "texte"


@pytest.fixture
def fake_provider():
    return FakeLLMProvider()
