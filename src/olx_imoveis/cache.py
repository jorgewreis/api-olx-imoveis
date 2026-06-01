"""Cache SQLite com TTL."""

import json
import sqlite3
import time
from pathlib import Path

from olx_imoveis.config import settings


class CacheStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self._path = db_path or settings.cache_db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def get(self, key: str) -> str | None:
        now = time.time()
        with sqlite3.connect(self._path) as conn:
            row = conn.execute(
                "SELECT payload FROM cache WHERE key = ? AND expires_at > ?",
                (key, now),
            ).fetchone()
        return row[0] if row else None

    def set(self, key: str, payload: str, ttl_seconds: int) -> None:
        expires = time.time() + ttl_seconds
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """
                INSERT INTO cache (key, payload, expires_at) VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET payload = excluded.payload,
                    expires_at = excluded.expires_at
                """,
                (key, payload, expires),
            )
            conn.commit()

    def get_json(self, key: str):
        raw = self.get(key)
        return json.loads(raw) if raw else None

    def set_json(self, key: str, data, ttl_seconds: int) -> None:
        self.set(key, json.dumps(data, ensure_ascii=False), ttl_seconds)

    def purge_expired(self) -> None:
        with sqlite3.connect(self._path) as conn:
            conn.execute("DELETE FROM cache WHERE expires_at <= ?", (time.time(),))
            conn.commit()
