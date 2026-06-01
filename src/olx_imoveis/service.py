"""Serviço de alto nível: busca e detalhe."""

import logging

from olx_imoveis.cache import CacheStore
from olx_imoveis.client import OlxHttpClient
from olx_imoveis.config import settings
from olx_imoveis.listing_display import sort_imoveis
from olx_imoveis.models import ImovelDetalhe, ImovelResumo, SearchFilters, SearchResult
from olx_imoveis.parsers.common import resolve_detail_fetch_url
from olx_imoveis.parsers.detail import parse_detail_page
from olx_imoveis.parsers.listing import parse_listing_page
from olx_imoveis.url_builder import build_search_url

logger = logging.getLogger(__name__)


class OlxImoveisService:
    def __init__(
        self,
        client: OlxHttpClient | None = None,
        cache: CacheStore | None = None,
    ) -> None:
        self._client = client or OlxHttpClient()
        self._cache = cache or CacheStore()
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def search(self, filters: SearchFilters, use_cache: bool = True) -> SearchResult:
        url = build_search_url(filters)
        cache_key = f"listing:{url}"

        if use_cache:
            cached = self._cache.get_json(cache_key)
            if cached:
                result = SearchResult.model_validate(cached)
                result.items = sort_imoveis(result.items, filters)
                result.url_busca = url
                return result

        html = self._client.get_html(url)
        logger.info("Busca OLX: %s", url)
        result = parse_listing_page(
            html,
            pagina=filters.pagina,
            fallback_uf=filters.estado,
            tipo_oferta=filters.tipo_oferta,
            bairro=filters.bairro,
            tipo_anunciante=filters.tipo_anunciante,
        )
        result.items = sort_imoveis(result.items, filters)
        result.url_busca = url

        if use_cache and result.items:
            self._cache.set_json(
                cache_key,
                result.model_dump(mode="json"),
                settings.listing_cache_ttl_seconds,
            )
        return result

    def get_detail(self, url: str, use_cache: bool = True) -> ImovelDetalhe:
        fetch_url = resolve_detail_fetch_url(url)
        cache_key = f"detail:{fetch_url}"

        if use_cache:
            cached = self._cache.get_json(cache_key)
            if cached:
                return ImovelDetalhe.model_validate(cached)

        html = self._client.get_html(fetch_url)
        detail = parse_detail_page(html, fetch_url)

        ttl = settings.detail_cache_ttl_seconds
        if detail.telefone:
            ttl = min(ttl, 86400)

        if use_cache:
            self._cache.set_json(
                cache_key,
                detail.model_dump(mode="json"),
                ttl,
            )
        return detail

    def fetch_export_details(self, items: list[ImovelResumo]) -> list[ImovelDetalhe]:
        """Carrega detalhe de cada anúncio para exportação (descrição, telefone, etc.)."""
        details: list[ImovelDetalhe] = []
        for item in items:
            try:
                details.append(self.get_detail(item.url, use_cache=True))
            except Exception as e:
                logger.warning("Detalhe indisponível para exportação %s: %s", item.list_id, e)
                base = item.model_dump()
                details.append(
                    ImovelDetalhe(
                        **base,
                        descricao=None,
                        imagens=[],
                        atributos={},
                    )
                )
        return details
