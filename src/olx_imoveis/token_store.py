"""Persistência local do token OAuth OLX."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from olx_imoveis.config import settings


@dataclass
class OlxTokenData:
    access_token: str
    token_type: str = "Bearer"
    user_name: str | None = None
    user_email: str | None = None


class TokenStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or settings.oauth_token_path

    def load(self) -> OlxTokenData | None:
        if not self._path.exists():
            return None
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        token = raw.get("access_token")
        if not token:
            return None
        return OlxTokenData(
            access_token=str(token),
            token_type=str(raw.get("token_type") or "Bearer"),
            user_name=raw.get("user_name"),
            user_email=raw.get("user_email"),
        )

    def save(self, data: OlxTokenData) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(asdict(data), ensure_ascii=False, indent=2), encoding="utf-8")

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()
