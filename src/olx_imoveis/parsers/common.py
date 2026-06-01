"""Utilitários compartilhados de parsing."""

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from olx_imoveis.errors import OlxParseError


def extract_next_data(html: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if script and script.string:
        try:
            return json.loads(script.string)
        except json.JSONDecodeError as e:
            raise OlxParseError("JSON __NEXT_DATA__ inválido.") from e

    match = re.search(
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError as e:
            raise OlxParseError("JSON __NEXT_DATA__ inválido (regex).") from e

    raise OlxParseError(
        "Não foi possível encontrar __NEXT_DATA__ na página. "
        "O layout da OLX pode ter mudado — atualize o aplicativo."
    )


def deep_find(obj: Any, *keys: str) -> Any | None:
    """Busca a primeira ocorrência de uma sequência de chaves em árvore JSON."""
    if not keys:
        return obj
    key = keys[0]
    rest = keys[1:]

    if isinstance(obj, dict):
        if key in obj:
            found = deep_find(obj[key], *rest)
            if found is not None:
                return found
        for v in obj.values():
            found = deep_find(v, *rest)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = deep_find(item, *rest)
            if found is not None:
                return found
    return None


def find_ads_list(data: dict[str, Any]) -> list[dict[str, Any]] | None:
    candidates = [
        deep_find(data, "pageProps", "ads"),
        deep_find(data, "pageProps", "searchResults", "ads"),
        deep_find(data, "pageProps", "initialData", "ads"),
        deep_find(data, "pageProps", "adList", "ads"),
    ]
    for c in candidates:
        if isinstance(c, list) and c:
            return c
    return None


def find_ad_object(data: dict[str, Any]) -> dict[str, Any] | None:
    candidates = [
        deep_find(data, "pageProps", "ad"),
        deep_find(data, "pageProps", "adDetail"),
        deep_find(data, "pageProps", "adData"),
    ]
    for c in candidates:
        if isinstance(c, dict) and (c.get("listId") or c.get("list_id")):
            return c
    return None


def _first_str(*values: Any) -> str | None:
    for v in values:
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def _parse_price(ad: dict[str, Any]) -> tuple[int | None, str | None]:
    price = ad.get("priceValue") or ad.get("price")
    label = ad.get("price") if isinstance(ad.get("price"), str) else None
    if isinstance(price, dict):
        val = price.get("value") or price.get("raw")
        label = price.get("label") or label
        price = val
    if isinstance(price, str):
        label = label or price
        digits = re.sub(r"\D", "", price)
        return (int(digits) if digits else None, label)
    if isinstance(price, (int, float)):
        return int(price), label
    return None, label


def _location_parts(ad: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    loc = ad.get("location") or ad.get("locations") or {}
    if isinstance(loc, list) and loc:
        loc = loc[0]
    if not isinstance(loc, dict):
        return None, None, None
    bairro = _first_str(
        loc.get("neighbourhood"),
        loc.get("neighborhood"),
        loc.get("district"),
        loc.get("name"),
    )
    cidade = _first_str(loc.get("municipality"), loc.get("city"), loc.get("region"))
    uf = _first_str(loc.get("uf"), loc.get("state"))
    return bairro, cidade, uf


def _image_url(ad: dict[str, Any]) -> str | None:
    images = ad.get("images") or ad.get("imageUrls") or []
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, str):
            return first
        if isinstance(first, dict):
            return _first_str(
                first.get("original"),
                first.get("url"),
                first.get("webp"),
                first.get("thumbnail"),
            )
    return _first_str(ad.get("thumbnail"), ad.get("image"))


def _build_url(ad: dict[str, Any], fallback_uf: str = "sp") -> str:
    url = _first_str(ad.get("friendlyUrl"), ad.get("url"), ad.get("permalink"))
    if url:
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return f"https://{fallback_uf}.olx.com.br{url}"
        return url
    list_id = ad.get("listId") or ad.get("list_id")
    if list_id:
        uf = fallback_uf
        loc = ad.get("location") or {}
        if isinstance(loc, dict) and loc.get("uf"):
            uf = str(loc["uf"]).lower()
        return f"https://{uf}.olx.com.br/vi/{list_id}.htm"
    return ""


def ad_to_resumo(ad: dict[str, Any], fallback_uf: str = "sp") -> dict[str, Any] | None:
    list_id = ad.get("listId") or ad.get("list_id") or ad.get("id")
    if list_id is None:
        return None
    titulo = _first_str(ad.get("title"), ad.get("subject"), ad.get("name")) or "Sem título"
    preco, preco_label = _parse_price(ad)
    bairro, cidade, uf = _location_parts(ad)
    url = _build_url(ad, fallback_uf)
    if not url:
        return None

    quartos = None
    props = ad.get("properties") or ad.get("parameters") or []
    if isinstance(props, list):
        for p in props:
            if not isinstance(p, dict):
                continue
            label = str(p.get("label", "")).lower()
            val = p.get("value")
            if "quarto" in label and val:
                try:
                    quartos = int(re.sub(r"\D", "", str(val)) or 0) or None
                except ValueError:
                    pass
            if "área" in label or "area" in label:
                pass

    return {
        "list_id": str(list_id),
        "titulo": titulo,
        "preco": preco,
        "preco_label": preco_label,
        "url": url,
        "bairro": bairro,
        "cidade": cidade,
        "estado": uf,
        "imagem_url": _image_url(ad),
        "quartos": quartos,
        "area_m2": None,
    }
