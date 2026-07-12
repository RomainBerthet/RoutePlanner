"""Reusable services to recommend things to visit along a route."""

from route_planner.recommendations.categories import (
    CATEGORIES,
    Category,
    resolve_categories,
)
from route_planner.recommendations.models import (
    PointOfInterest,
    StopRecommendations,
)
from route_planner.recommendations.providers import (
    IRecommendationProvider,
    OverpassProvider,
)
from route_planner.recommendations.service import RecommendationService

__all__ = [
    "CATEGORIES",
    "Category",
    "resolve_categories",
    "PointOfInterest",
    "StopRecommendations",
    "IRecommendationProvider",
    "OverpassProvider",
    "RecommendationService",
]
