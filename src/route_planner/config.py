"""Environment configuration helpers."""

from __future__ import annotations

_LOADED = False


def load_env() -> bool:
    """Load a local ``.env`` into the process environment, once, best-effort.

    Uses python-dotenv when available (searches the working directory and its
    parents). Existing environment variables are never overridden, and a
    missing python-dotenv simply results in a no-op — so the app runs fine
    without either the package or a ``.env`` file.
    """

    global _LOADED
    if _LOADED:
        return True
    _LOADED = True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    load_dotenv(override=False)
    return True
