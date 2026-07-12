import route_planner.config as config


def test_load_env_is_boolean_and_idempotent():
    config._LOADED = False
    first = config.load_env()
    assert isinstance(first, bool)
    # Second call is a no-op that reports already-loaded.
    assert config.load_env() is True
