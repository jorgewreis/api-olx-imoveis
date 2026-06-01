"""Parser de página de detalhe do anúncio."""

import re
from typing import Any
from urllib.parse import urlparse

from olx_imoveis.errors import OlxParseError
from olx_imoveis.models import Anunciante, ImovelDetalhe
from olx_imoveis.parsers.common import (
    ad_to_resumo,
    extract_next_data,
    find_ad_object,
)


def parse_detail_page(html: str, url: str) -> ImovelDetalhe:
    data = extract_next_data(html)
    ad = find_ad_object(data)
    if not ad:
        raise OlxParseError("Anúncio não encontrado no JSON da página de detalhe.")

    host = urlparse(url).netloc
    fallback_uf = host.split(".")[0] if host else "sp"
    base = ad_to_resumo(ad, fallback_uf)
    if not base:
        raise OlxParseError("Dados mínimos do anúncio ausentes.")

    descricao = _first_str(
        ad.get("body"),
        ad.get("description"),
        ad.get("observation"),
    )
    imagens = _collect_images(ad)
    atributos = _collect_attributes(ad)
    anunciante = _parse_seller(ad)
    telefone, mascarado = _parse_phone(ad)

    return ImovelDetalhe(
        **base,
        url=url,
        descricao=descricao,
        imagens=imagens,
        atributos=atributos,
        anunciante=anunciante,
        telefone=telefone,
        telefone_mascarado=mascarado,
    )


def _first_str(*values: Any) -> str | None:
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def _collect_images(ad: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    images = ad.get("images") or ad.get("imageUrls") or []
    if isinstance(images, list):
        for img in images:
            if isinstance(img, str) and img not in urls:
                urls.append(img)
            elif isinstance(img, dict):
                u = _first_str(img.get("original"), img.get("url"), img.get("webp"))
                if u and u not in urls:
                    urls.append(u)
    return urls


def _collect_attributes(ad: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    props = ad.get("properties") or ad.get("parameters") or ad.get("params") or []
    if isinstance(props, dict):
        return {str(k): v for k, v in props.items()}
    if isinstance(props, list):
        for p in props:
            if isinstance(p, dict):
                label = _first_str(p.get("label"), p.get("name"))
                val = p.get("value") or p.get("valueLabel")
                if label:
                    out[label] = val
    for key in ("condominio", "iptu", "size", "rooms", "bathrooms", "garage_spaces"):
        if key in ad and ad[key] is not None:
            out[key] = ad[key]
    params = ad.get("params")
    if isinstance(params, dict):
        out.update({str(k): v for k, v in params.items()})
    return out


def _parse_seller(ad: dict[str, Any]) -> Anunciante:
    user = ad.get("user") or ad.get("seller") or ad.get("account") or {}
    if not isinstance(user, dict):
        return Anunciante()
    nome = _first_str(user.get("name"), user.get("nickname"), user.get("publicName"))
    account_id = _first_str(user.get("publicAccountId"), user.get("accountId"), user.get("id"))
    is_pro = bool(user.get("isProfessional") or user.get("professional") or user.get("is_pro"))
    profile = _first_str(user.get("profileUrl"), user.get("url"))
    return Anunciante(
        nome=nome,
        public_account_id=account_id,
        is_professional=is_pro,
        profile_url=profile,
    )


def _parse_phone(ad: dict[str, Any]) -> tuple[str | None, bool]:
    phone = ad.get("phone") or ad.get("phoneNumber")
    if isinstance(phone, dict):
        phone = phone.get("phone") or phone.get("number")
    phones = ad.get("phones")
    if not phone and isinstance(phones, list) and phones:
        first = phones[0]
        if isinstance(first, dict):
            phone = first.get("phone") or first.get("number")
        else:
            phone = first
    contact = ad.get("contact")
    if not phone and isinstance(contact, dict):
        phone = contact.get("phone") or contact.get("phones")

    if not phone:
        return None, False

    s = str(phone).strip()
    masked = "*" in s or "X" in s.upper()
    digits = re.sub(r"\D", "", s)
    if len(digits) >= 10:
        if len(digits) == 11:
            formatted = f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
        elif len(digits) == 10:
            formatted = f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
        else:
            formatted = digits
        return formatted, masked
    return s if not masked else (s, True)
