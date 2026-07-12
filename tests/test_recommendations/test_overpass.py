from unittest.mock import patch

from route_planner.cache import SQLiteCache
from route_planner.recommendations.categories import resolve_categories
from route_planner.recommendations.providers.overpass import OverpassProvider


CATEGORIES = resolve_categories(["sight", "food"])


def _response(elements):
    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"elements": elements}

    return Resp()


@patch("route_planner.recommendations.providers.overpass.requests.post")
def test_parses_nodes_and_way_centers(mock_post, tmp_path):
    mock_post.return_value = _response([
        {"type": "node", "id": 1, "lat": 45.0, "lon": 13.0, "tags": {"name": "Fort", "historic": "fort"}},
        {"type": "way", "id": 2, "center": {"lat": 45.1, "lon": 13.1},
         "tags": {"name": "Resto", "amenity": "restaurant"}},
        {"type": "node", "id": 3, "lat": 45.2, "lon": 13.2, "tags": {"amenity": "restaurant"}},  # no name
    ])
    provider = OverpassProvider(base_url="http://overpass.test", cache=SQLiteCache(tmp_path / "c.sqlite3"))

    pois = provider.fetch((45.0, 13.0), 5000, CATEGORIES)

    names = {p.name for p in pois}
    assert names == {"Fort", "Resto"}  # unnamed element dropped
    fort = next(p for p in pois if p.name == "Fort")
    assert fort.category == "sight"
    resto = next(p for p in pois if p.name == "Resto")
    assert resto.category == "food" and resto.lat == 45.1


@patch("route_planner.recommendations.providers.overpass.requests.post")
def test_result_is_cached(mock_post, tmp_path):
    mock_post.return_value = _response([
        {"type": "node", "id": 1, "lat": 45.0, "lon": 13.0, "tags": {"name": "Fort", "historic": "fort"}},
    ])
    cache = SQLiteCache(tmp_path / "c.sqlite3")
    provider = OverpassProvider(base_url="http://overpass.test", cache=cache)

    provider.fetch((45.0, 13.0), 5000, CATEGORIES)
    provider.fetch((45.0, 13.0), 5000, CATEGORIES)

    assert mock_post.call_count == 1  # second call served from cache


@patch("route_planner.recommendations.providers.overpass.requests.post", side_effect=RuntimeError("boom"))
def test_network_error_returns_empty(mock_post, tmp_path):
    provider = OverpassProvider(base_url="http://overpass.test", cache=SQLiteCache(tmp_path / "c.sqlite3"))

    assert provider.fetch((45.0, 13.0), 5000, CATEGORIES) == []


def test_query_groups_values_per_key_with_regex():
    provider = OverpassProvider(base_url="http://overpass.test")
    query = provider._build_query((45.0, 13.0), 4000, CATEGORIES)

    assert "around:4000,45.0,13.0" in query
    # Values are grouped into one regex clause per OSM key (cheap on Overpass).
    assert '["amenity"~"^(restaurant)$"]' in query
    assert query.count('["historic"~') == 1
    assert "out center tags" in query
    # No expensive per-value clause explosion.
    assert query.count("nwr(around") <= 3
