from route_planner.cache import SQLiteCache
from route_planner.routers.osrm_router import OSRMRouter


def test_sqlite_cache_roundtrip(tmp_path):
    cache = SQLiteCache(tmp_path / "cache.sqlite3")
    cache.set("geocode", "key-1", [48.85, 2.35])
    assert cache.get("geocode", "key-1") == [48.85, 2.35]


def test_osrm_router_uses_persistent_cache(tmp_path):
    cache = SQLiteCache(tmp_path / "cache.sqlite3")
    router = OSRMRouter("drive", cache=cache)

    calls = []

    def fake_geocode(_):
        calls.append(1)
        return type("Location", (object,), {"latitude": 48.85, "longitude": 2.35})

    router.geocoder.geocode = fake_geocode
    first = router.geocode("Paris")
    assert first == (48.85, 2.35)

    router2 = OSRMRouter("drive", cache=cache)
    router2.geocoder.geocode = lambda _: (_ for _ in ()).throw(RuntimeError("should not be called"))
    second = router2.geocode("Paris")

    assert second == (48.85, 2.35)
    assert len(calls) == 1
