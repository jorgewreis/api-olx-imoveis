"""Cliente HTTP com throttle e retries."""

import logging
import time

import httpx

from olx_imoveis.config import settings
from olx_imoveis.errors import OlxFetchError, OlxRateLimitError

logger = logging.getLogger(__name__)


class OlxHttpClient:
    def __init__(self) -> None:
        self._last_request_at: float = 0.0
        self._client = httpx.Client(
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pt-BR,pt;q=0.9",
            },
            follow_redirects=True,
            timeout=settings.request_timeout,
        )

    def close(self) -> None:
        self._client.close()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        wait = settings.min_request_interval - elapsed
        if wait > 0:
            time.sleep(wait)

    def get_html(self, url: str) -> str:
        last_error: Exception | None = None
        for attempt in range(settings.max_retries):
            self._throttle()
            try:
                response = self._client.get(url)
                self._last_request_at = time.monotonic()
            except httpx.HTTPError as e:
                last_error = e
                time.sleep(2**attempt)
                continue

            if response.status_code == 429:
                raise OlxRateLimitError(
                    "Muitas requisições. Aguarde alguns minutos e tente novamente."
                )
            if response.status_code >= 500:
                last_error = OlxFetchError(f"Servidor OLX retornou {response.status_code}")
                time.sleep(2**attempt)
                continue
            if response.status_code >= 400:
                raise OlxFetchError(
                    f"Não foi possível acessar a página (HTTP {response.status_code})."
                )
            return response.text

        raise OlxFetchError(
            f"Falha ao acessar {url}: {last_error}"
        ) from last_error
