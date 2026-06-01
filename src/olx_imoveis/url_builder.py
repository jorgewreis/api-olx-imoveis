"""Montagem de URLs de busca compatíveis com o site OLX."""

from urllib.parse import urlencode

from olx_imoveis.models import (
    MAX_ALUGUEL_PRECO,
    MIN_VENDA_PRECO,
    SearchFilters,
    TipoAnunciante,
    TipoOferta,
)


def effective_price_range(filters: SearchFilters) -> tuple[int | None, int | None]:
    """Aplica limites de preço por tipo de oferta."""
    pmin = filters.preco_min
    pmax = filters.preco_max
    if filters.tipo_oferta == TipoOferta.VENDA:
        if pmin is None or pmin < MIN_VENDA_PRECO:
            pmin = MIN_VENDA_PRECO
    elif filters.tipo_oferta == TipoOferta.ALUGUEL:
        if pmax is None or pmax > MAX_ALUGUEL_PRECO:
            pmax = MAX_ALUGUEL_PRECO
    return pmin, pmax


def build_search_url(filters: SearchFilters) -> str:
    uf = filters.estado.lower().strip()
    regiao = filters.regiao.strip("/")

    if regiao == f"estado-{uf}":
        location = [regiao]
    else:
        location = [f"estado-{uf}", *regiao.split("/")]
    if filters.bairro:
        location.append(filters.bairro.strip("/"))

    segments = ["imoveis"]
    if filters.tipo_oferta is not None and filters.tipo_imovel is not None:
        segments.extend([filters.tipo_oferta.value, filters.tipo_imovel.value])
    elif filters.tipo_oferta is not None:
        segments.append(filters.tipo_oferta.value)
    elif filters.tipo_imovel is not None:
        segments.append(filters.tipo_imovel.value)
    segments.extend(location)
    path = "/".join(segments)

    pmin, pmax = effective_price_range(filters)

    query: dict[str, str | int] = {}
    if pmin is not None:
        query["ps"] = pmin
    if pmax is not None:
        query["pe"] = pmax
    if filters.quartos_min is not None:
        query["se"] = filters.quartos_min
    if filters.quartos_max is not None:
        query["ss"] = filters.quartos_max
    if filters.banheiros_min is not None:
        query["bae"] = filters.banheiros_min
    if filters.vagas_min is not None:
        query["gsp"] = filters.vagas_min
    if filters.termo:
        query["q"] = filters.termo.strip()
    if filters.tipo_anunciante == TipoAnunciante.COMUM:
        query["f"] = 0
    elif filters.tipo_anunciante == TipoAnunciante.PROFISSIONAL:
        query["f"] = 1
    if filters.pagina > 1:
        query["page"] = filters.pagina

    base = f"https://www.olx.com.br/{path}"
    if query:
        return f"{base}?{urlencode(query)}"
    return base
