"""Parser de páginas de listagem."""

from typing import Any

from olx_imoveis.errors import OlxParseError
from olx_imoveis.models import ImovelResumo, SearchResult
from olx_imoveis.parsers.common import (
    ad_to_resumo,
    deep_find,
    extract_next_data,
    find_ads_list,
)


def parse_listing_page(html: str, pagina: int = 1, fallback_uf: str = "sp") -> SearchResult:
    data = extract_next_data(html)
    ads = find_ads_list(data)
    if ads is None:
        raise OlxParseError(
            "Lista de anúncios não encontrada no JSON da página. "
            "Verifique filtros ou atualize o aplicativo."
        )

    items: list[ImovelResumo] = []
    seen: set[str] = set()
    for raw in ads:
        if not isinstance(raw, dict):
            continue
        parsed = ad_to_resumo(raw, fallback_uf)
        if not parsed:
            continue
        lid = parsed["list_id"]
        if lid in seen:
            continue
        seen.add(lid)
        items.append(ImovelResumo(**parsed))

    total = _extract_total(data)
    tem_mais = _has_next_page(data, pagina, len(items))

    return SearchResult(
        items=items,
        total=total,
        pagina=pagina,
        tem_mais=tem_mais,
    )


def _extract_total(data: dict[str, Any]) -> int | None:
    for path in [
        ("pageProps", "totalAds"),
        ("pageProps", "searchResults", "total"),
        ("pageProps", "total"),
    ]:
        val = deep_find(data, *path)
        if isinstance(val, int):
            return val
    return None


def _has_next_page(data: dict[str, Any], pagina: int, count: int) -> bool:
    next_page = deep_find(data, "pageProps", "nextPage")
    if next_page is not None:
        return bool(next_page)
    total = _extract_total(data)
    if total is not None:
        return pagina * max(count, 1) < total
    return count >= 20
