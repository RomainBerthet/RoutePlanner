"""Provider abstraction for point-of-interest discovery."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Sequence

from route_planner.recommendations.categories import Category
from route_planner.recommendations.models import Coordinate, PointOfInterest


class IRecommendationProvider(ABC):
    """Fetch raw points of interest around a coordinate.

    Implementations should be resilient: on any network/parsing error they must
    return an empty list rather than raising, so a failed lookup for one stop
    never breaks a whole itinerary.
    """

    @abstractmethod
    def fetch(
        self,
        coordinate: Coordinate,
        radius_m: int,
        categories: Sequence[Category],
    ) -> List[PointOfInterest]:
        ...
