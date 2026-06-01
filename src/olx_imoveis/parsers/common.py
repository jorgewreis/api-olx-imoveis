"""Utilitários compartilhados de parsing."""

import html as html_module
import json
import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from olx_imoveis.errors import OlxParseError

_LISTING_OFFER_SEGMENTS = {"venda", "aluguel", "temporada", "quartos"}


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
        deep_find(data, "props", "pageProps", "ad"),
        deep_find(data, "props", "pageProps", "adDetail"),
        deep_find(data, "props", "pageProps", "adData"),
        deep_find(data, "pageProps", "ad"),
        deep_find(data, "pageProps", "adDetail"),
        deep_find(data, "pageProps", "adData"),
    ]
    for candidate in candidates:
        ad = _unwrap_ad_object(candidate)
        if ad:
            return ad
    return None


def _unwrap_ad_object(obj: Any) -> dict[str, Any] | None:
    if not isinstance(obj, dict):
        return None
    if obj.get("listId") or obj.get("list_id"):
        return obj
    for key in ("ad", "adDetail", "adData"):
        nested = obj.get(key)
        if isinstance(nested, dict) and (nested.get("listId") or nested.get("list_id")):
            return nested
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


def slugify_label(text: str) -> str:
    """Normaliza texto para slug comparável ao catálogo de bairros."""
    import unicodedata

    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


def _location_parts(ad: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    loc = ad.get("locationDetails") or ad.get("location") or ad.get("locations") or {}
    if isinstance(loc, list) and loc:
        loc = loc[0]
    if isinstance(loc, str):
        parts = [part.strip() for part in loc.split(",") if part.strip()]
        if len(parts) >= 2:
            return parts[-1], parts[0], None
        if len(parts) == 1:
            return None, parts[0], None
        return None, None, None
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


def extract_embedded_json_object(html: str, key: str) -> dict[str, Any] | None:
    """Extrai um objeto JSON embutido após uma chave, ex.: \"adDetail\"."""
    needle = f'"{key}"'
    pos = html.find(needle)
    if pos < 0:
        return None
    start = html.find("{", pos)
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(html)):
        ch = html[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    parsed = json.loads(html[start : i + 1])
                except json.JSONDecodeError:
                    return None
                return parsed if isinstance(parsed, dict) else None
    return None


def extract_ld_json(html: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", type="application/ld+json")
    if not script or not script.string:
        return None
    try:
        parsed = json.loads(script.string)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def is_olx_detail_url(url: str) -> bool:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if not parts:
        return False
    if parts[0] == "vi" or parts[0].startswith("vi"):
        return True
    if "imoveis" not in parts:
        return False
    idx = parts.index("imoveis")
    segment_after = parts[idx + 1] if idx + 1 < len(parts) else ""
    return segment_after not in _LISTING_OFFER_SEGMENTS


def resolve_detail_fetch_url(url: str) -> str:
    """Normaliza URLs de detalhe que apontam para listagem no host www."""
    if not is_olx_detail_url(url):
        return url
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host == "www.olx.com.br":
        match = re.search(r"-(\d+)$", parsed.path.rstrip("/").split("/")[-1])
        if match:
            return f"https://www.olx.com.br/vi/{match.group(1)}.htm"
    return url


def map_ad_detail_payload(
    ad_detail: dict[str, Any],
    *,
    ld_json: dict[str, Any] | None = None,
    page_url: str,
) -> dict[str, Any]:
    """Converte payload adDetail + ld+json para o formato comum de anúncio."""
    properties: list[dict[str, Any]] = []
    for label, key, suffix in [
        ("Quartos", "rooms", ""),
        ("Banheiros", "bathrooms", ""),
        ("Vagas", "garage_spaces", ""),
        ("Área útil", "size", " m²"),
        ("Condomínio", "condominio", ""),
        ("IPTU", "iptu", ""),
    ]:
        value = ad_detail.get(key)
        if value not in (None, ""):
            properties.append({"label": label, "value": f"{value}{suffix}".strip()})

    for label, key in [
        ("Tipo", "real_estate_type"),
        ("Características", "re_features"),
        ("Condomínio", "re_complex_features"),
        ("Tipos", "re_types"),
    ]:
        value = ad_detail.get(key)
        if value:
            properties.append({"label": label, "value": value})

    descricao = None
    imagens: list[dict[str, str]] = []
    canonical_url = page_url
    if ld_json:
        obj = ld_json.get("Object")
        if isinstance(obj, dict):
            descricao = obj.get("description")
            canonical_url = _first_str(obj.get("url"), page_url) or page_url
            image = obj.get("image")
            if isinstance(image, list):
                for item in image:
                    if isinstance(item, dict):
                        img_url = _first_str(item.get("contentUrl"), item.get("url"))
                        if img_url:
                            imagens.append({"original": img_url})
            elif isinstance(image, str):
                imagens.append({"original": image})

    if descricao:
        descricao = html_module.unescape(re.sub(r"<br\s*/?>", "\n", descricao, flags=re.I))

    return {
        "listId": ad_detail.get("listId"),
        "title": ad_detail.get("subject"),
        "priceValue": ad_detail.get("price"),
        "body": descricao,
        "location": {
            "neighbourhood": ad_detail.get("neighbourhood"),
            "municipality": ad_detail.get("municipality"),
            "uf": ad_detail.get("state"),
        },
        "user": {
            "name": ad_detail.get("sellerName"),
            "publicAccountId": ad_detail.get("sellerPublicAccountId"),
            "isProfessional": ad_detail.get("professionalAd"),
        },
        "properties": properties,
        "images": imagens,
        "url": canonical_url,
    }


def _build_url(ad: dict[str, Any], fallback_uf: str = "sp") -> str:
    url = _first_str(ad.get("friendlyUrl"), ad.get("url"), ad.get("permalink"))
    if url:
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            url = f"https://www.olx.com.br{url}"
        if is_olx_detail_url(url):
            return url
        return _normalize_olx_url(url, fallback_uf)

    list_id = ad.get("listId") or ad.get("list_id")
    if list_id:
        uf = fallback_uf
        loc = ad.get("location") or {}
        if isinstance(loc, dict) and loc.get("uf"):
            uf = str(loc["uf"]).lower()
        return f"https://{uf}.olx.com.br/vi/{list_id}.htm"
    return ""


def _normalize_olx_url(url: str, fallback_uf: str = "sp") -> str:
    """Converte URLs legadas por subdomínio para o host www.olx.com.br."""
    if "://" not in url:
        return url

    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not host.endswith("olx.com.br"):
        return url

    path = parsed.path.strip("/")
    if host == "www.olx.com.br" or is_olx_detail_url(url):
        return url

    parts = path.split("/")
    if "imoveis" in parts:
        idx = parts.index("imoveis")
        slug_parts = parts[idx + 1 :]
        if slug_parts and slug_parts[0] in _LISTING_OFFER_SEGMENTS:
            slug_parts = slug_parts[2:]
        if slug_parts:
            slug = slug_parts[-1]
            if slug.isdigit():
                return f"https://www.olx.com.br/vi/{slug}.htm"

    if path.startswith("vi/"):
        return f"https://www.olx.com.br/{path}"

    return f"https://www.olx.com.br/{path}"


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
