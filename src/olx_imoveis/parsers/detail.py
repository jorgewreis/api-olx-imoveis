"""Parser de página de detalhe do anúncio."""

import re
from typing import Any
from urllib.parse import urlparse

from olx_imoveis.errors import OlxParseError
from olx_imoveis.models import Anunciante, ImovelDetalhe
from olx_imoveis.parsers.common import (
    ad_to_resumo,
    extract_embedded_json_object,
    extract_ld_json,
    extract_next_data,
    find_ad_object,
    is_professional_ad,
    map_ad_detail_payload,
    merge_seller_contact,
    resolve_detail_fetch_url,
)


def parse_detail_page(html: str, url: str) -> ImovelDetalhe:
    ad = _extract_ad_from_html(html, url)
    if not ad:
        raise OlxParseError("Anúncio não encontrado no JSON da página de detalhe.")

    fetch_url = resolve_detail_fetch_url(url)
    host = urlparse(fetch_url).netloc
    fallback_uf = host.split(".")[0] if host else "sp"
    base = ad_to_resumo(ad, fallback_uf)
    if not base:
        raise OlxParseError("Dados mínimos do anúncio ausentes.")
    base.pop("url", None)

    descricao = _first_str(
        ad.get("body"),
        ad.get("description"),
        ad.get("observation"),
    )
    imagens = _collect_images(ad)
    atributos = _collect_attributes(ad)
    anunciante = _parse_seller(ad, descricao=descricao)
    telefone, mascarado = _parse_phone(ad, descricao=descricao)

    return ImovelDetalhe(
        **base,
        url=_first_str(ad.get("url"), fetch_url, url) or url,
        descricao=descricao,
        imagens=imagens,
        atributos=atributos,
        anunciante=anunciante,
        telefone=telefone,
        telefone_mascarado=mascarado,
    )


def _extract_ad_from_html(html: str, url: str) -> dict[str, Any] | None:
    ad: dict[str, Any] | None = None
    if "__NEXT_DATA__" in html:
        try:
            data = extract_next_data(html)
            ad = find_ad_object(data)
        except OlxParseError:
            pass

    if not ad:
        ad_detail = extract_embedded_json_object(html, "adDetail")
        if ad_detail:
            ld_json = extract_ld_json(html)
            ad = map_ad_detail_payload(ad_detail, ld_json=ld_json, page_url=url)

    if ad:
        merge_seller_contact(ad, html)
    return ad


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


def _parse_seller(ad: dict[str, Any], *, descricao: str | None = None) -> Anunciante:
    user = ad.get("user") or ad.get("seller") or ad.get("account") or {}
    if not isinstance(user, dict):
        user = {}
    nome = _first_str(user.get("name"), user.get("nickname"), user.get("publicName"))
    account_id = _first_str(user.get("publicAccountId"), user.get("accountId"), user.get("id"))
    is_pro = is_professional_ad(ad, descricao=descricao)
    profile = _first_str(user.get("profileUrl"), user.get("url"))
    return Anunciante(
        nome=nome,
        public_account_id=account_id,
        is_professional=is_pro,
        profile_url=profile,
    )


def _parse_phone(ad: dict[str, Any], *, descricao: str | None = None) -> tuple[str | None, bool]:
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

    if phone:
        formatted, masked = _normalize_phone(str(phone).strip())
        if formatted:
            return formatted, masked

    masked_phone = _first_str(ad.get("maskedPhone"))
    if masked_phone:
        return _format_masked_phone(masked_phone, _first_str(ad.get("ddd"))), True

    if descricao:
        from_text = _phone_from_text(descricao)
        if from_text:
            return from_text, False

    return None, False


def _normalize_phone(raw: str) -> tuple[str | None, bool]:
    masked = "*" in raw or "..." in raw or "X" in raw.upper()
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 10:
        return (raw, True) if masked else (None, False)
    return _format_digits(digits), masked


def _format_digits(digits: str) -> str:
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    return digits


def _format_masked_phone(masked: str, ddd: str | None) -> str:
    cleaned = masked.strip()
    has_ellipsis = "..." in cleaned
    digits = re.sub(r"\D", "", cleaned.replace(".", ""))

    if len(digits) >= 11:
        return _format_digits(digits[:11]) + ("..." if has_ellipsis else "")
    if len(digits) >= 8:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}{'...' if has_ellipsis else ''}"
    if ddd and digits:
        return f"({ddd}) {digits}{'...' if has_ellipsis else ''}"
    return cleaned


_PHONE_IN_TEXT = re.compile(
    r"(?<!\d)(?:\+55\s?)?(?:\(?(\d{2})\)?[\s.-]?)?((?:9[\s.-]?)?\d{4}[\s.-]?\d{4})(?!\d)"
)


def _phone_from_text(text: str) -> str | None:
    for match in _PHONE_IN_TEXT.finditer(text):
        ddd = match.group(1) or ""
        local = re.sub(r"\D", "", match.group(2) or "")
        digits = re.sub(r"\D", "", ddd + local)
        if len(digits) == 10 and digits[0] == "9":
            continue
        if len(digits) not in (10, 11):
            continue
        if len(digits) == 11 and digits[2] != "9":
            continue
        return _format_digits(digits)
    return None
