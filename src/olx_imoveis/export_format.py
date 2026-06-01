"""Formato de exportação: 2 linhas por imóvel."""

from __future__ import annotations

import re
from typing import Any

from olx_imoveis.listing_display import clean_text, format_price, oferta_label
from olx_imoveis.models import ImovelDetalhe, SearchFilters

DESCRIPTION_SUMMARY_MAX = 140


def format_phone_export(phone: str | None) -> str:
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11:
        return f"{digits[:2]} {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"{digits[:2]} {digits[2:6]}-{digits[6:]}"
    return clean_text(phone.replace("(", "").replace(")", ""))


def format_export_location(item: ImovelDetalhe) -> str:
    parts: list[str] = []
    if item.estado:
        parts.append(clean_text(item.estado).upper())
    if item.cidade:
        parts.append(clean_text(item.cidade).upper())
    if item.bairro:
        parts.append(clean_text(item.bairro).upper())
    return " - ".join(parts) if parts else "LOCAL NÃO INFORMADO"


def summarize_description(text: str | None, max_len: int = DESCRIPTION_SUMMARY_MAX) -> str:
    if not text:
        return ""
    single = clean_text(text.replace("\n", " "))
    if len(single) <= max_len:
        return single
    cut = single[:max_len].rsplit(" ", 1)[0]
    return f"{cut}…"


def _digits_from_value(value: Any) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d+", str(value))
    return int(match.group()) if match else None


def _attr_value(atributos: dict[str, Any], *needles: str) -> Any | None:
    for key, value in atributos.items():
        key_l = key.lower()
        for needle in needles:
            if needle in key_l:
                return value
    return None


def _extract_count(item: ImovelDetalhe, *needles: str) -> int | None:
    val = _attr_value(item.atributos, *needles)
    if val is not None:
        parsed = _digits_from_value(val)
        if parsed is not None:
            return parsed
    return None


def _extract_area_m2(item: ImovelDetalhe) -> int | None:
    if item.area_m2 is not None:
        return item.area_m2
    val = _attr_value(item.atributos, "área", "area", "size")
    return _digits_from_value(val)


def _extract_extra_features(item: ImovelDetalhe) -> list[str]:
    extras: list[str] = []
    seen: set[str] = set()

    raw = _attr_value(item.atributos, "característica", "caracteristica", "re_features")
    if raw:
        for part in re.split(r"[,;|]", str(raw)):
            feat = clean_text(part)
            if not feat or len(feat) > 40:
                continue
            key = feat.lower()
            if key in seen:
                continue
            seen.add(key)
            extras.append(feat.lower())

    desc = (item.descricao or "").lower()
    for keyword in ("varanda", "piscina", "suíte", "suite", "mobiliado", "vista mar", "elevador"):
        if keyword in desc and keyword not in seen:
            seen.add(keyword)
            extras.append(keyword)

    return extras[:4]


def format_export_line1(item: ImovelDetalhe, filters: SearchFilters | None = None) -> str:
    loc = format_export_location(item)
    oferta = oferta_label(item, filters)
    preco = format_price(item)
    nome = clean_text(item.anunciante.nome or "Anunciante não informado").upper()
    phone = format_phone_export(item.telefone)
    if phone:
        contact = f"{nome} - {phone}"
    else:
        contact = nome
    return f"{loc} | {oferta}: {preco} | {contact}"


def format_export_line2(item: ImovelDetalhe) -> str:
    specs: list[str] = []

    quartos = item.quartos if item.quartos is not None else _extract_count(item, "quarto")
    if quartos is not None:
        specs.append(f"{quartos} quarto" if quartos == 1 else f"{quartos} quartos")

    banheiros = _extract_count(item, "banheiro", "bathroom")
    if banheiros is not None:
        specs.append(f"{banheiros} banheiro" if banheiros == 1 else f"{banheiros} banheiros")

    vagas = _extract_count(item, "vaga", "garagem", "garage")
    if vagas is not None:
        specs.append(f"{vagas} garagem" if vagas == 1 else f"{vagas} garagens")

    area = _extract_area_m2(item)
    if area is not None:
        specs.append(f"{area}m²")

    specs.extend(_extract_extra_features(item))

    left = ", ".join(specs) if specs else "—"
    summary = summarize_description(item.descricao)
    if summary:
        return f"{left} | {summary}"
    return left


def detail_to_export_record(item: ImovelDetalhe, filters: SearchFilters | None = None) -> dict[str, str]:
    return {
        "list_id": item.list_id,
        "linha_1": format_export_line1(item, filters),
        "linha_2": format_export_line2(item),
        "url": item.url,
        "descricao": clean_text(item.descricao or ""),
    }
