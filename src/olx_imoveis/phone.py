"""Telefone completo via API showphone (requer sessão OAuth)."""

from __future__ import annotations

import json
import logging
import re

from curl_cffi.requests import Session
from curl_cffi.requests.exceptions import RequestException

from olx_imoveis.config import settings
from olx_imoveis.errors import OlxAuthError, OlxFetchError

logger = logging.getLogger(__name__)

SHOWPHONE_URL = "https://apigw.olx.com.br/v1/showphone"


def fetch_full_phone(
    list_id: str,
    access_token: str,
    *,
    referer: str,
    session: Session | None = None,
) -> str | None:
    """Obtém telefone completo do anunciante (conta OLX autenticada)."""
    own_session = session is None
    http = session or Session(impersonate="chrome131")
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Referer": referer,
        "Origin": "https://www.olx.com.br",
        "User-Agent": settings.user_agent,
    }
    url = f"{SHOWPHONE_URL}/{list_id}"

    try:
        response = http.get(url, headers=headers, timeout=settings.request_timeout)
    except RequestException as e:
        raise OlxFetchError(f"Falha ao consultar telefone: {e}") from e
    finally:
        if own_session:
            http.close()

    if response.status_code == 403 and "NOT_LOGGED" in response.text:
        raise OlxAuthError("Sessão OLX expirada ou inválida. Entre novamente.")
    if response.status_code >= 400:
        logger.info("showphone %s -> HTTP %s %s", list_id, response.status_code, response.text[:120])
        return None

    return _parse_phone_response(response.text)


def _parse_phone_response(body: str) -> str | None:
    phone: str | None = None
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            for key in ("phone", "phoneNumber", "maskedPhone", "number"):
                val = data.get(key)
                if isinstance(val, str) and val.strip():
                    phone = val.strip()
                    break
            if not phone and isinstance(data.get("data"), dict):
                nested = data["data"]
                for key in ("phone", "phoneNumber"):
                    val = nested.get(key)
                    if isinstance(val, str) and val.strip():
                        phone = val.strip()
                        break
    except json.JSONDecodeError:
        phone = body.strip() if body.strip().isdigit() else None

    if not phone:
        return None

    digits = re.sub(r"\D", "", phone)
    if len(digits) < 10:
        return None
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return digits
