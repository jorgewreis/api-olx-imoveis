"""Testes OAuth OLX."""

import json
from unittest.mock import MagicMock, patch

import pytest

from olx_imoveis.auth import OlxOAuth, oauth_configured
from olx_imoveis.errors import OlxAuthError
from olx_imoveis.models import ImovelDetalhe
from olx_imoveis.phone import _parse_phone_response
from olx_imoveis.service import OlxImoveisService
from olx_imoveis.token_store import OlxTokenData, TokenStore


def test_extract_code_from_url():
    url = "http://127.0.0.1:8765/oauth/callback?code=abc123xyz&state=test"
    assert OlxOAuth.extract_code_from_redirect(url) == "abc123xyz"


def test_extract_code_raw():
    assert OlxOAuth.extract_code_from_redirect("abc123xyz0123456789012345678901234") == (
        "abc123xyz0123456789012345678901234"
    )


def test_token_store_roundtrip(tmp_path):
    store = TokenStore(tmp_path / "token.json")
    data = OlxTokenData(access_token="tok123", user_email="a@b.com")
    store.save(data)
    loaded = store.load()
    assert loaded is not None
    assert loaded.access_token == "tok123"
    assert loaded.user_email == "a@b.com"
    store.clear()
    assert store.load() is None


def test_exchange_code_success(tmp_path):
    store = TokenStore(tmp_path / "token.json")
    oauth = OlxOAuth(store=store)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "new_token", "token_type": "Bearer"}

    with patch.object(oauth, "_ensure_configured"), patch.object(
        oauth._session, "post", return_value=mock_response
    ), patch.object(
        oauth,
        "_enrich_user_info",
    ):
        token = oauth.exchange_code("code1234567890123456789012345678901234")
    assert token.access_token == "new_token"
    assert store.load() is not None


def test_parse_phone_response_json():
    body = json.dumps({"phone": "73999887766"})
    assert _parse_phone_response(body) == "(73) 99988-7766"


def test_oauth_configured_false(monkeypatch):
    monkeypatch.setattr("olx_imoveis.auth.settings.oauth_client_id", "")
    assert oauth_configured() is False


def test_enrich_phone_optional_without_login():
    svc = OlxImoveisService()
    detail = ImovelDetalhe(
        list_id="1",
        titulo="Teste",
        url="https://www.olx.com.br/vi/1.htm",
        telefone="(73) 9917-88...",
        telefone_mascarado=True,
    )
    enriched = svc._enrich_phone(detail, detail.url)
    assert enriched.telefone == detail.telefone
    svc.close()


def test_enrich_phone_auth_failure_does_not_raise():
    svc = OlxImoveisService()
    svc.oauth._token = OlxTokenData(access_token="expired")
    detail = ImovelDetalhe(list_id="1", titulo="Teste", url="https://www.olx.com.br/vi/1.htm")

    with patch("olx_imoveis.service.fetch_full_phone", side_effect=OlxAuthError("expirada")):
        enriched = svc._enrich_phone(detail, detail.url)

    assert enriched.list_id == "1"
    assert not svc.oauth.is_logged_in()
    svc.close()
