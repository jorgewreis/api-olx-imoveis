"""Probe OLX detail page structures."""
import json
import re
import sys
from pathlib import Path

from curl_cffi.requests import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from olx_imoveis.models import SearchFilters, TipoOferta
from olx_imoveis.parsers.common import extract_next_data, find_ad_object, find_ads_list
from olx_imoveis.service import OlxImoveisService

LIST_ID = "1506240881"
SLUG = (
    "apartamento-padrao-com-1-quartos-e-1-banheiros-a-venda-30-m-em-ilheus-ba-1506240881"
)

URLS = [
    f"https://www.olx.com.br/imoveis/{SLUG}",
    f"https://ba.olx.com.br/sul-da-bahia/imoveis/{SLUG}",
    f"https://www.olx.com.br/vi/{LIST_ID}.htm",
    f"https://www.olx.com.br/d/{LIST_ID}",
    f"https://www.olx.com.br/anuncio/{SLUG}",
]

s = Session(impersonate="chrome131")

for url in URLS:
    r = s.get(url, timeout=30, allow_redirects=True)
    print("=" * 80)
    print("req:", url[:90])
    print("final:", r.url[:90])
    print("status:", r.status_code, "len:", len(r.text))
    for pat in ["__NEXT_DATA__", LIST_ID, "pageType", "adDetail", '"body"']:
        print(f"  {pat}: {r.text.count(pat)}")
    if "__NEXT_DATA__" in r.text:
        data = extract_next_data(r.text)
        pp = data.get("props", {}).get("pageProps", {})
        print("  pageType:", pp.get("pageType"))
        ad = find_ad_object(data)
        print("  find_ad_object:", ad is not None)
        if not ad:
            ads = find_ads_list(data)
            if ads:
                match = next((a for a in ads if str(a.get("listId")) == LIST_ID), None)
                print("  ad in listing ads:", match is not None)
                if match:
                    print("  match keys:", list(match.keys())[:12])

# Check if listing page contains full ad data for clicked item
svc = OlxImoveisService()
item = svc.search(
    SearchFilters(estado="ba", regiao="sul-da-bahia/ilheus", tipo_oferta=TipoOferta.VENDA),
    use_cache=False,
).items[0]
html = svc._client.get_html(
    "https://www.olx.com.br/imoveis/venda/apartamentos/estado-ba/sul-da-bahia/ilheus"
)
data = extract_next_data(html)
ads = find_ads_list(data) or []
ad = next((a for a in ads if str(a.get("listId")) == item.list_id), None)
print("=" * 80)
print("Listing ad payload keys:", list(ad.keys()) if ad else None)
if ad:
    for k in ["body", "description", "phone", "user", "images", "properties"]:
        v = ad.get(k)
        print(f"  {k}: {type(v).__name__}", (len(v) if isinstance(v, (list, str)) else v))
svc.close()
