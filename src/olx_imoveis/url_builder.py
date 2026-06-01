"""Montagem de URLs de busca compatíveis com o site OLX."""

from urllib.parse import urlencode

from olx_imoveis.models import SearchFilters


def build_search_url(filters: SearchFilters) -> str:
    uf = filters.estado.lower().strip()
    parts = [filters.regiao.strip("/")]
    if filters.bairro:
        parts.append(filters.bairro.strip("/"))
    parts.extend(["imoveis", filters.tipo_oferta.value, filters.tipo_imovel.value])
    path = "/".join(parts)

    query: dict[str, str | int] = {}
    if filters.preco_min is not None:
        query["ps"] = filters.preco_min
    if filters.preco_max is not None:
        query["pe"] = filters.preco_max
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
    if filters.pagina > 1:
        query["page"] = filters.pagina

    base = f"https://{uf}.olx.com.br/{path}"
    if query:
        return f"{base}?{urlencode(query)}"
    return base
