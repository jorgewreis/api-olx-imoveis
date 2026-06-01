"""Configuração global do aplicativo."""

from __future__ import annotations

import sys
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_env_files() -> tuple[str, ...]:
    """Localiza `.env` fora do CWD (exe, AppData, raiz do projeto)."""
    candidates: list[Path] = []

    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / ".env")

    candidates.append(Path.cwd() / ".env")

    module_dir = Path(__file__).resolve().parent
    for parent in [module_dir, *module_dir.parents]:
        candidates.append(parent / ".env")
        if (parent / "pyproject.toml").exists():
            break

    app_data = Path.home() / "AppData" / "Local" / "OlxImoveis" / ".env"
    candidates.append(app_data)

    seen: set[Path] = set()
    found: list[str] = []
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            found.append(str(resolved))

    return tuple(found) if found else (".env",)


_ENV_FILES = _resolve_env_files()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OLX_",
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    user_agent: str = "OlxImoveisDesktop/1.0 (+uso pessoal; contato via repositorio)"
    request_timeout: float = 30.0
    min_request_interval: float = 1.0
    listing_cache_ttl_seconds: int = 600
    detail_cache_ttl_seconds: int = 86400
    max_retries: int = 3

    oauth_client_id: str = ""
    oauth_client_secret: str = ""
    oauth_redirect_uri: str = "http://127.0.0.1:8765/oauth/callback"
    oauth_scope: str = "basic_user_info"

    @property
    def app_data_dir(self) -> Path:
        base = Path.home() / "AppData" / "Local" / "OlxImoveis"
        base.mkdir(parents=True, exist_ok=True)
        return base

    @property
    def cache_db_path(self) -> Path:
        return self.app_data_dir / "cache.db"

    @property
    def logs_dir(self) -> Path:
        d = self.app_data_dir / "logs"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def disclaimer_flag_path(self) -> Path:
        return self.app_data_dir / ".disclaimer_accepted"

    @property
    def oauth_token_path(self) -> Path:
        return self.app_data_dir / "oauth_token.json"


settings = Settings()
