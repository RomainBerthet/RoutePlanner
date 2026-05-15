from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any, Optional


class SQLiteCache:
    def __init__(self, path: Optional[str] = None):
        default_path = Path(
            os.environ.get(
                "ROUTE_PLANNER_CACHE_PATH",
                Path(tempfile.gettempdir()) / "route_planner" / "cache.sqlite3",
            )
        )
        cache_path = Path(path) if path else default_path
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.path = cache_path
        self._lock = RLock()
        self._ensure_schema()

    def get(self, namespace: str, key: str) -> Any:
        with self._lock, sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT value FROM cache WHERE namespace = ? AND key = ?",
                (namespace, key),
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def set(self, namespace: str, key: str, value: Any) -> None:
        payload = json.dumps(value, ensure_ascii=True)
        with self._lock, sqlite3.connect(self.path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO cache(namespace, key, value) VALUES (?, ?, ?)",
                (namespace, key, payload),
            )
            connection.commit()

    def clear(self) -> None:
        with self._lock, sqlite3.connect(self.path) as connection:
            connection.execute("DELETE FROM cache")
            connection.commit()

    def _ensure_schema(self) -> None:
        with self._lock, sqlite3.connect(self.path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY (namespace, key)
                )
                """
            )
            connection.commit()
