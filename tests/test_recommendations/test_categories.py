from route_planner.recommendations.categories import (
    CATEGORY_BY_KEY,
    classify,
    resolve_categories,
)


def test_classify_prefers_more_specific_category():
    assert classify({"historic": "castle", "name": "X"}) == "sight"
    assert classify({"tourism": "viewpoint", "name": "X"}) == "viewpoint"
    assert classify({"natural": "waterfall", "name": "X"}) == "nature"
    assert classify({"amenity": "restaurant", "name": "X"}) == "food"


def test_classify_returns_none_when_no_match():
    assert classify({"shop": "supermarket", "name": "X"}) is None


def test_resolve_categories_filters_unknown_keys():
    resolved = resolve_categories(["sight", "unknown", "food"])
    assert [c.key for c in resolved] == ["sight", "food"]


def test_resolve_categories_defaults_to_all_when_empty():
    assert len(resolve_categories([])) == len(CATEGORY_BY_KEY)
    assert len(resolve_categories(None)) == len(CATEGORY_BY_KEY)
