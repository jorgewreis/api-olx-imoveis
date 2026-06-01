"""Testes de carregamento de configuração."""

from pathlib import Path

from olx_imoveis import config


def test_resolve_env_files_finds_project_env():
    paths = config._resolve_env_files()
    assert any(Path(p).name == ".env" and Path(p).is_file() for p in paths)


def test_settings_load_oauth_from_env():
    assert config.settings.oauth_client_id
    assert config.settings.oauth_client_secret
