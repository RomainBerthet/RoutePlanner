"""Data models produced by the AI travel-intelligence service."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ItinerarySuggestion:
    """A structured itinerary proposed by the LLM from a free-text request."""

    stops: List[str]
    transport_mode: str = "drive"
    objective: str = "balanced"
    title: str = ""
    subtitle: str = ""
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ItinerarySuggestion":
        mode = str(data.get("transport_mode", "drive"))
        if mode not in {"drive", "bike", "walk"}:
            mode = "drive"
        objective = str(data.get("objective", "balanced"))
        if objective not in {"fastest", "shortest_km", "cheapest", "balanced"}:
            objective = "balanced"
        stops = [str(s).strip() for s in data.get("stops", []) if str(s).strip()]
        return cls(
            stops=stops,
            transport_mode=mode,
            objective=objective,
            title=str(data.get("title", "")).strip(),
            subtitle=str(data.get("subtitle", "")).strip(),
            rationale=str(data.get("rationale", "")).strip(),
        )


@dataclass
class GuideItem:
    title: str
    body: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GuideItem":
        return cls(title=str(data.get("title", "")).strip(), body=str(data.get("body", "")).strip())


@dataclass
class SecretSpot:
    name: str
    zone: str = ""
    body: str = ""
    gps: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecretSpot":
        return cls(
            name=str(data.get("name", "")).strip(),
            zone=str(data.get("zone", "")).strip(),
            body=str(data.get("body", "")).strip(),
            gps=str(data.get("gps", "")).strip(),
        )


@dataclass
class BudgetRow:
    label: str
    detail: str = ""
    amount: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BudgetRow":
        return cls(
            label=str(data.get("label", "")).strip(),
            detail=str(data.get("detail", "")).strip(),
            amount=str(data.get("amount", "")).strip(),
        )


@dataclass
class BudgetRecap:
    rows: List[BudgetRow] = field(default_factory=list)
    total: str = ""
    note: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BudgetRecap":
        return cls(
            rows=[BudgetRow.from_dict(r) for r in data.get("rows", [])],
            total=str(data.get("total", "")).strip(),
            note=str(data.get("note", "")).strip(),
        )


@dataclass
class GuideContent:
    """Editorial content that enriches the travel guide."""

    intro: str = ""
    tips: List[GuideItem] = field(default_factory=list)
    vigilance: List[GuideItem] = field(default_factory=list)
    secrets: List[SecretSpot] = field(default_factory=list)
    practical: List[GuideItem] = field(default_factory=list)
    budget: Optional[BudgetRecap] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GuideContent":
        budget = data.get("budget")
        return cls(
            intro=str(data.get("intro", "")).strip(),
            tips=[GuideItem.from_dict(x) for x in data.get("tips", [])],
            vigilance=[GuideItem.from_dict(x) for x in data.get("vigilance", [])],
            secrets=[SecretSpot.from_dict(x) for x in data.get("secrets", [])],
            practical=[GuideItem.from_dict(x) for x in data.get("practical", [])],
            budget=BudgetRecap.from_dict(budget) if isinstance(budget, dict) else None,
        )

    @property
    def is_empty(self) -> bool:
        return not any([self.intro, self.tips, self.vigilance, self.secrets, self.practical, self.budget])
