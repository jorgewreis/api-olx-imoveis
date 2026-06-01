"""Configuração global do aplicativo."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OLX_", env_file=".env", extra="ignore")

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
