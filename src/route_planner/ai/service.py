"""AI travel-intelligence service.

Turns a free-text request into a structured itinerary the router can plan, and
writes the editorial content (tips, points of vigilance, budget recap, secret
spots, practical advice) that makes the generated guide feel hand-crafted. The
service depends only on the :class:`ILLMProvider` interface, so any backend —
Anthropic, OpenAI, vLLM — or a fake works interchangeably.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from route_planner.ai.models import GuideContent, ItinerarySuggestion

_ITINERARY_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "subtitle": {"type": "string"},
        "transport_mode": {"type": "string", "enum": ["drive", "bike", "walk"]},
        "objective": {
            "type": "string",
            "enum": ["fastest", "shortest_km", "cheapest", "balanced"],
        },
        "stops": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
    },
    "required": ["title", "transport_mode", "objective", "stops"],
}

_GUIDE_ITEM = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
    "required": ["title", "body"],
}

_GUIDE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "intro": {"type": "string"},
        "tips": {"type": "array", "items": _GUIDE_ITEM},
        "vigilance": {"type": "array", "items": _GUIDE_ITEM},
        "practical": {"type": "array", "items": _GUIDE_ITEM},
        "secrets": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "zone": {"type": "string"},
                    "body": {"type": "string"},
                    "gps": {"type": "string"},
                },
                "required": ["name", "body"],
            },
        },
        "budget": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "rows": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "label": {"type": "string"},
                            "detail": {"type": "string"},
                            "amount": {"type": "string"},
                        },
                        "required": ["label", "amount"],
                    },
                },
                "total": {"type": "string"},
                "note": {"type": "string"},
            },
            "required": ["rows", "total"],
        },
    },
    "required": ["intro", "tips", "vigilance", "practical", "secrets", "budget"],
}

_PLANNER_SYSTEM = (
    "Tu es un planificateur de voyage expert. A partir d'une demande en langage "
    "naturel, tu proposes un itineraire realiste. Regles: les etapes doivent etre "
    "des lieux geocodables (ville et pays, ou POI connu avec ville), ordonnees de "
    "facon logique depuis le point de depart; deduis le mode de transport "
    "(drive/bike/walk) et l'objectif (fastest/shortest_km/cheapest/balanced) de la "
    "demande; garde un nombre d'etapes raisonnable (2 a 10). Reponds en francais."
)

_GUIDE_SYSTEM = (
    "Tu es un guide de voyage local et pragmatique. A partir d'un parcours et de "
    "lieux d'interet fournis, tu rediges le contenu editorial d'un carnet de voyage "
    "en francais: une intro qui pose l'esprit du voyage, des astuces concretes, des "
    "points de vigilance (securite, regles locales, arnaques, meteo), un recap "
    "budget realiste (montants en euros, avec un total), et des spots secrets peu "
    "frequentes proches de l'itineraire. Sois concret, honnete et utile; n'invente "
    "pas de faits verifiables douteux."
)


class TravelIntelligence:
    def __init__(self, provider):
        self.provider = provider

    # -- planning -----------------------------------------------------------

    def suggest_itinerary(self, request: str, max_stops: int = 10) -> ItinerarySuggestion:
        user = (
            f"Demande du voyageur:\n{request}\n\n"
            f"Propose au plus {max_stops} etapes."
        )
        data = self.provider.complete_json(_PLANNER_SYSTEM, user, _ITINERARY_SCHEMA, max_tokens=4096)
        suggestion = ItinerarySuggestion.from_dict(data)
        if len(suggestion.stops) < 2:
            raise ValueError("L'IA n'a pas propose assez d'etapes (minimum 2).")
        suggestion.stops = suggestion.stops[:max_stops]
        return suggestion

    # -- enrichment ---------------------------------------------------------

    def write_guide_content(
        self,
        plan,
        recommendations: Optional[List] = None,
        request: str = "",
    ) -> GuideContent:
        user = self._guide_prompt(plan, recommendations or [], request)
        data = self.provider.complete_json(_GUIDE_SYSTEM, user, _GUIDE_SCHEMA, max_tokens=6000)
        return GuideContent.from_dict(data)

    def _guide_prompt(self, plan, recommendations, request: str) -> str:
        mode = plan.preferences.get("transport_mode", "drive")
        lines = [
            f"Mode de transport: {mode}",
            f"Distance totale: {plan.distance_km:.0f} km",
            f"Duree totale estimee: {plan.duration_h:.1f} h",
        ]
        if mode == "drive":
            lines.append(f"Cout carburant estime: {plan.cost_eur:.0f} EUR")
        lines.append("Etapes (dans l'ordre):")
        for i, stop in enumerate(plan.ordered_addresses, 1):
            lines.append(f"  {i}. {stop}")
        if recommendations:
            lines.append("\nLieux d'interet reperes autour des etapes:")
            for stop in recommendations:
                if not stop.pois:
                    continue
                names = ", ".join(f"{p.name} ({p.category})" for p in stop.pois[:6])
                lines.append(f"  - {stop.label}: {names}")
        if request:
            lines.append(f"\nSouhait du voyageur: {request}")
        lines.append(
            "\nRedige le contenu du carnet. Vise 3-5 astuces, 3-5 points de "
            "vigilance, 4-6 lignes de budget, 3-6 spots secrets, 3-5 conseils "
            "pratiques."
        )
        return "\n".join(lines)
