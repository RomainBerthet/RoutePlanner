from dataclasses import dataclass, field
from dataclasses import asdict
from typing import Any, Dict, List, Sequence, Tuple


Coordinate = Tuple[float, float]


@dataclass(frozen=True)
class RoutePreferences:
    transport_mode: str = "drive"
    objective: str = "fastest"
    avoid_tolls: bool = False
    budget_eur: float | None = None
    balanced_weight: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RouteLeg:
    depart: str
    arrivee: str
    distance_km: float
    duree_h: float
    resume: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RoutePlan:
    requested_addresses: List[str]
    ordered_addresses: List[str]
    coordinates: List[Coordinate]
    geometry: Dict[str, Any]
    distance_km: float
    duration_h: float
    cost_eur: float
    legs: List[RouteLeg] = field(default_factory=list)
    routing_engine: str = ""
    optimization_strategy: str = "none"
    preferences: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    budget_limit_eur: float | None = None
    budget_within: bool = True
    budget_gap_eur: float = 0.0
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["legs"] = [leg.to_dict() for leg in self.legs]
        return payload
