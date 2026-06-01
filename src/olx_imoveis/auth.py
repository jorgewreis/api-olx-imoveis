"""Autenticação OAuth 2.0 OLX Brasil (Authorization Code).

Fluxo oficial: https://developers.olx.com.br/anuncio/api/oauth.html
Referência: https://github.com/olx-brasil/olx-api-client
"""

from __future__ import annotations

import json
import logging
import re
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

from curl_cffi.requests import Session
from curl_cffi.requests.exceptions import RequestException

from olx_imoveis.config import settings
from olx_imoveis.errors import OlxAuthError
from olx_imoveis.token_store import OlxTokenData, TokenStore

logger = logging.getLogger(__name__)

AUTH_URL = "https://auth.olx.com.br/oauth"
TOKEN_URL = "https://auth.olx.com.br/oauth/token"
APPS_API_URL = "https://apps.olx.com.br/oauth_api"


class OlxOAuth:
    """Cliente OAuth — login e senha são informados na página oficial auth.olx.com.br."""

    def __init__(self, store: TokenStore | None = None) -> None:
        self._store = store or TokenStore()
        self._session = Session(impersonate="chrome131")
        self._token: OlxTokenData | None = self._store.load()

    def close(self) -> None:
        self._session.close()

    @property
    def token(self) -> OlxTokenData | None:
        return self._token

    def is_logged_in(self) -> bool:
        return self._token is not None and bool(self._token.access_token)

    def http_session(self) -> Session:
        return self._session

    def user_label(self) -> str | None:
        if not self._token:
            return None
        if self._token.user_email:
            return self._token.user_email
        if self._token.user_name:
            return self._token.user_name
        return "Conta OLX conectada"

    def logout(self) -> None:
        self._token = None
        self._store.clear()

    def _ensure_configured(self) -> None:
        if not settings.oauth_client_id or not settings.oauth_client_secret:
            raise OlxAuthError(
                "Configure OLX_OAUTH_CLIENT_ID e OLX_OAUTH_CLIENT_SECRET no arquivo .env. "
                "Registre a aplicação em suporteintegrador@olxbr.com "
                "(https://developers.olx.com.br/anuncio/api/oauth.html)."
            )
        if not settings.oauth_redirect_uri:
            raise OlxAuthError("Configure OLX_OAUTH_REDIRECT_URI no arquivo .env.")

    def build_authorization_url(self, *, state: str | None = None) -> str:
        self._ensure_configured()
        state = state or secrets.token_urlsafe(16)
        query = urlencode(
            {
                "client_id": settings.oauth_client_id,
                "response_type": "code",
                "scope": settings.oauth_scope,
                "redirect_uri": settings.oauth_redirect_uri,
                "state": state,
            }
        )
        return f"{AUTH_URL}?{query}"

    def exchange_code(self, code: str) -> OlxTokenData:
        self._ensure_configured()
        code = code.strip()
        if not code:
            raise OlxAuthError("Código de autorização vazio.")

        payload = {
            "code": code,
            "client_id": settings.oauth_client_id,
            "client_secret": settings.oauth_client_secret,
            "redirect_uri": settings.oauth_redirect_uri,
            "grant_type": "authorization_code",
        }
        try:
            response = self._session.post(
                TOKEN_URL,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=settings.request_timeout,
            )
        except RequestException as e:
            raise OlxAuthError(f"Falha ao obter token: {e}") from e

        if response.status_code >= 400:
            raise OlxAuthError(f"Token recusado (HTTP {response.status_code}): {response.text[:200]}")

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise OlxAuthError("Resposta inválida ao trocar código por token.") from e

        access_token = data.get("access_token")
        if not access_token:
            err = data.get("error", "unknown")
            raise OlxAuthError(f"Token não retornado: {err}")

        token = OlxTokenData(
            access_token=str(access_token),
            token_type=str(data.get("token_type") or "Bearer"),
        )
        self._enrich_user_info(token)
        self._token = token
        self._store.save(token)
        return token

    def _enrich_user_info(self, token: OlxTokenData) -> None:
        try:
            info = self.fetch_basic_user_info(token.access_token)
        except OlxAuthError:
            logger.warning("Não foi possível obter basic_user_info após login.")
            return
        token.user_name = info.get("user_name")
        token.user_email = info.get("user_email")

    def fetch_basic_user_info(self, access_token: str | None = None) -> dict[str, str]:
        token = access_token or (self._token.access_token if self._token else None)
        if not token:
            raise OlxAuthError("Nenhum access_token disponível.")

        try:
            response = self._session.post(
                f"{APPS_API_URL}/basic_user_info",
                json={"access_token": token},
                headers={"Content-Type": "application/json", "User-Agent": settings.user_agent},
                timeout=settings.request_timeout,
            )
        except RequestException as e:
            raise OlxAuthError(f"Falha ao consultar usuário: {e}") from e

        if response.status_code >= 400:
            raise OlxAuthError(f"basic_user_info falhou (HTTP {response.status_code}).")

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise OlxAuthError("Resposta inválida de basic_user_info.") from e

        return {
            "user_name": str(data.get("user_name") or ""),
            "user_email": str(data.get("user_email") or ""),
        }

    def login_interactive(self, *, timeout: float = 300.0) -> OlxTokenData:
        """Abre o navegador na OLX; usuário informa e-mail e senha no site oficial."""
        state = secrets.token_urlsafe(16)
        auth_url = self.build_authorization_url(state=state)
        redirect_uri = settings.oauth_redirect_uri
        parsed = urlparse(redirect_uri)
        if parsed.hostname not in ("127.0.0.1", "localhost"):
            raise OlxAuthError(
                "OLX_OAUTH_REDIRECT_URI deve apontar para localhost "
                "(ex.: http://127.0.0.1:8765/oauth/callback)."
            )

        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        result: dict[str, str | None] = {"code": None, "error": None}
        done = threading.Event()

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: object) -> None:
                return

            def do_GET(self) -> None:
                req_path = urlparse(self.path).path.rstrip("/") or "/"
                expected = path.rstrip("/") or "/"
                if req_path != expected:
                    self.send_error(404)
                    return
                qs = parse_qs(urlparse(self.path).query)
                if qs.get("state", [None])[0] not in (state, None):
                    result["error"] = "state inválido"
                elif "error" in qs:
                    result["error"] = qs["error"][0]
                elif "code" in qs:
                    result["code"] = qs["code"][0]
                else:
                    result["error"] = "code ausente"

                body = (
                    "<html><body><h2>Login OLX concluído.</h2>"
                    "<p>Você pode fechar esta aba e voltar ao aplicativo.</p></body></html>"
                )
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body.encode("utf-8"))
                done.set()

        server = HTTPServer((parsed.hostname or "127.0.0.1", port), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        logger.info("Abrindo login OLX: %s", auth_url)
        webbrowser.open(auth_url)

        if not done.wait(timeout=timeout):
            server.shutdown()
            raise OlxAuthError("Tempo esgotado aguardando login na OLX.")

        server.shutdown()

        if result["error"]:
            raise OlxAuthError(f"Login recusado: {result['error']}")
        if not result["code"]:
            raise OlxAuthError("Código de autorização não recebido.")

        return self.exchange_code(str(result["code"]))

    @staticmethod
    def extract_code_from_redirect(raw: str) -> str:
        """Extrai `code` de uma URL de callback ou do código puro."""
        raw = raw.strip()
        if not raw:
            raise OlxAuthError("Informe a URL de retorno ou o código de autorização.")
        if "code=" in raw:
            qs = parse_qs(urlparse(raw).query)
            code = qs.get("code", [None])[0]
            if not code:
                raise OlxAuthError("Parâmetro code não encontrado na URL.")
            return str(code)
        if re.fullmatch(r"[A-Za-z0-9/_-]{20,}", raw):
            return raw
        raise OlxAuthError("Código ou URL de retorno inválidos.")


def oauth_configured() -> bool:
    return bool(settings.oauth_client_id and settings.oauth_client_secret and settings.oauth_redirect_uri)
