"""
Route Planner Factory
Flexible routing engine with OSRM and OSMnx support.
"""

from .vehicule import Vehicule
from .route_planner import RoutePlanner
from .models import RoutePlan, RouteLeg, Coordinate, RoutePreferences
from .recommendations import (
    PointOfInterest,
    RecommendationService,
    StopRecommendations,
)
from .exporters.travel_guide_exporter import TravelGuideExporter
from .ai import LLMFactory, TravelIntelligence, GuideContent, ItinerarySuggestion

__version__ = "0.6.0"

__all__ = [
    "Vehicule",
    "RoutePlanner",
    "RoutePlan",
    "RouteLeg",
    "Coordinate",
    "RoutePreferences",
    "RecommendationService",
    "PointOfInterest",
    "StopRecommendations",
    "TravelGuideExporter",
    "LLMFactory",
    "TravelIntelligence",
    "GuideContent",
    "ItinerarySuggestion",
]
