"""Parser de páginas de listagem."""

from typing import Any

from olx_imoveis.errors import OlxParseError
from olx_imoveis.models import (
    MAX_ALUGUEL_PRECO,
    MIN_VENDA_PRECO,
    OLX_CATEGORY_ALUGUEL,
    OLX_CATEGORY_VENDA,
    ImovelResumo,
    SearchResult,
    TipoAnunciante,
    TipoOferta,
)
from olx_imoveis.parsers.common import (
    _location_parts,
    _parse_price,
    ad_to_resumo,
    deep_find,
    extract_next_data,
    find_ads_list,
    slugify_label,
)


def parse_listing_page(
    html: str,
    pagina: int = 1,
    fallback_uf: str = "sp",
    tipo_oferta: TipoOferta | None = None,
    bairro: str | None = None,
    tipo_anunciante: TipoAnunciante | None = None,
) -> SearchResult:
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
        if tipo_oferta and not _matches_offer_type(raw, tipo_oferta):
            continue
        if not _matches_price_range(raw, tipo_oferta):
            continue
        if bairro and not _matches_bairro(raw, bairro):
            continue
        if tipo_anunciante and not _matches_anunciante_tipo(raw, tipo_anunciante):
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


def _matches_offer_type(ad: dict[str, Any], tipo_oferta: TipoOferta) -> bool:
    code = ad.get("searchCategoryLevelOne")
    if code is None:
        return True
    expected = OLX_CATEGORY_VENDA if tipo_oferta == TipoOferta.VENDA else OLX_CATEGORY_ALUGUEL
    return code == expected


def _matches_price_range(ad: dict[str, Any], tipo_oferta: TipoOferta | None) -> bool:
    preco, _ = _parse_price(ad)
    if preco is None:
        return True
    if tipo_oferta == TipoOferta.VENDA:
        return preco >= MIN_VENDA_PRECO
    if tipo_oferta == TipoOferta.ALUGUEL:
        return preco <= MAX_ALUGUEL_PRECO
    code = ad.get("searchCategoryLevelOne")
    if code == OLX_CATEGORY_VENDA:
        return preco >= MIN_VENDA_PRECO
    if code == OLX_CATEGORY_ALUGUEL:
        return preco <= MAX_ALUGUEL_PRECO
    return True


def _matches_bairro(ad: dict[str, Any], bairro_slug: str) -> bool:
    bairro, _, _ = _location_parts(ad)
    if not bairro:
        return False
    return slugify_label(bairro) == bairro_slug


def _matches_anunciante_tipo(ad: dict[str, Any], tipo: TipoAnunciante) -> bool:
    is_pro = bool(ad.get("professionalAd"))
    if tipo == TipoAnunciante.PROFISSIONAL:
        return is_pro
    return not is_pro
