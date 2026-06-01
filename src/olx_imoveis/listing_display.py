"""Formatação de textos para listagem e exportação."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from olx_imoveis.models import ImovelResumo, SearchFilters, TipoOferta

from olx_imoveis.models import MAX_ALUGUEL_PRECO, MIN_VENDA_PRECO, TipoOferta


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    normalized = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()


def format_price(item: ImovelResumo) -> str:
    if item.preco is not None:
        inteiro = f"{item.preco:,}".replace(",", ".")
        return f"R$ {inteiro},00"
    if item.preco_label:
        label = clean_text(item.preco_label)
        if not label.upper().startswith("R$"):
            label = f"R$ {label}"
        if "," not in label:
            label = f"{label},00"
        return label
    return "Consulte"


def format_location(item: ImovelResumo) -> str:
    parts: list[str] = []
    if item.bairro:
        parts.append(clean_text(item.bairro))
    if item.cidade:
        parts.append(clean_text(item.cidade))
    if item.estado:
        parts.append(clean_text(item.estado).upper())
    return " · ".join(parts) if parts else "Local não informado"


def format_features(item: ImovelResumo) -> str:
    parts: list[str] = []
    if item.quartos is not None:
        q = item.quartos
        parts.append(f"{q} quarto" if q == 1 else f"{q} quartos")
    if item.area_m2 is not None:
        parts.append(f"{item.area_m2} m²")
    return " · ".join(parts)


def oferta_label(item: ImovelResumo, filters: SearchFilters | None = None) -> str:
    ot = (filters.tipo_oferta if filters else None) or item.tipo_oferta
    if ot is not None:
        return ot.value.upper()
    if item.preco is not None:
        if item.preco >= MIN_VENDA_PRECO:
            return "VENDA"
        if item.preco <= MAX_ALUGUEL_PRECO:
            return "ALUGUEL"
    return "VENDA"


def item_to_export_row(item: ImovelResumo, filters: SearchFilters | None = None) -> dict[str, str]:
    return {
        "list_id": item.list_id,
        "titulo": clean_text(item.titulo),
        "preco": format_price(item),
        "oferta": oferta_label(item, filters),
        "local": format_location(item),
        "bairro": clean_text(item.bairro or ""),
        "cidade": clean_text(item.cidade or ""),
        "estado": clean_text(item.estado or "").upper(),
        "quartos": str(item.quartos) if item.quartos is not None else "",
        "area_m2": str(item.area_m2) if item.area_m2 is not None else "",
        "url": item.url,
    }
