from types import SimpleNamespace

from route_planner.recommendations.models import PointOfInterest
from route_planner.recommendations.service import RecommendationService


class FakeProvider:
    def __init__(self, pois):
        self._pois = pois
        self.calls = []

    def fetch(self, coordinate, radius_m, categories):
        self.calls.append(coordinate)
        return list(self._pois)


def _poi(name, category, lat, lon, tags=None, osm_id=1):
    return PointOfInterest(
        name=name,
        category=category,
        lat=lat,
        lon=lon,
        tags=tags or {},
        osm_type="node",
        osm_id=osm_id,
    )


def test_wikidata_bonus_beats_pure_proximity():
    provider = FakeProvider([
        _poi("Château", "sight", 45.05, 13.05, {"wikidata": "Q1"}, osm_id=1),
        _poi("Café du coin", "drink", 45.001, 13.001, {}, osm_id=2),
    ])
    service = RecommendationService(provider=provider, radius_m=10000)

    rec = service.recommend_for_coordinate((45.0, 13.0), "Stop")

    assert rec.pois[0].name == "Château"
    assert rec.pois[0].distance_km > rec.pois[1].distance_km


def test_duplicate_names_are_collapsed():
    provider = FakeProvider([
        _poi("Resto", "food", 45.001, 13.001, {"amenity": "restaurant"}, osm_id=2),
        _poi("Resto", "food", 45.001, 13.001, {"amenity": "restaurant"}, osm_id=3),
    ])
    service = RecommendationService(provider=provider, radius_m=8000)

    rec = service.recommend_for_coordinate((45.0, 13.0))

    assert len([p for p in rec.pois if p.name == "Resto"]) == 1


def test_per_category_and_per_stop_limits():
    pois = [_poi(f"Sight {i}", "sight", 45.0 + i / 1000, 13.0, osm_id=i) for i in range(10)]
    service = RecommendationService(
        provider=FakeProvider(pois), radius_m=20000, per_stop_limit=5, per_category_limit=3
    )

    rec = service.recommend_for_coordinate((45.0, 13.0))

    assert len(rec.pois) == 3  # capped by per_category_limit (all "sight")


def test_recommend_for_plan_dedupes_across_stops():
    shared = _poi("Vieille ville", "sight", 45.01, 13.01, {"wikidata": "Q9"}, osm_id=42)
    provider = FakeProvider([shared])
    service = RecommendationService(provider=provider, radius_m=15000)
    plan = SimpleNamespace(
        ordered_addresses=["A", "B"],
        coordinates=[(45.0, 13.0), (45.02, 13.02)],
    )

    results = service.recommend_for_plan(plan)

    # The shared POI must appear only for the first stop, not repeated.
    assert results[0].pois[0].osm_id == 42
    assert results[1].pois == []


def test_recommend_for_plan_skips_duplicate_coordinates():
    provider = FakeProvider([_poi("X", "sight", 45.01, 13.01, osm_id=1)])
    service = RecommendationService(provider=provider, radius_m=10000)
    plan = SimpleNamespace(
        ordered_addresses=["A", "A-again"],
        coordinates=[(45.0, 13.0), (45.0, 13.0)],
    )

    results = service.recommend_for_plan(plan)

    assert len(results) == 1


def test_poi_maps_url_and_gps():
    poi = _poi("Piran", "sight", 45.5285, 13.5636)
    assert poi.gps == "45.5285, 13.5636"
    assert poi.maps_url.startswith("https://www.google.com/maps/search/?api=1&query=")
