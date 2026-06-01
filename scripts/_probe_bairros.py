"""Discover valid bairro URL slugs for Ilhéus on OLX."""
import re
import sys
from pathlib import Path

from curl_cffi.requests import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from olx_imoveis.parsers.common import extract_next_data, find_ads_list

BASE = "https://www.olx.com.br/imoveis/venda/apartamentos/estado-ba/sul-da-bahia/ilheus"
s = Session(impersonate="chrome131")
html = s.get(BASE + "?ps=100000", timeout=30).text
text = html
# neighbourhood names from unfiltered
data = extract_next_data(html)
ads = find_ads_list(data) or []
names = sorted(
    {
        (ad.get("locationDetails") or {}).get("neighbourhood")
        for ad in ads
        if (ad.get("locationDetails") or {}).get("neighbourhood")
    }
)
print("Neighbourhoods in city:", names)

candidates = [
    "centro",
    "sao-francisco",
    "nossa-senhora-da-vitoria",
    "olivena",
    "olivenca",
    "pontal",
    "barra-do-riachinho",
    "jardim-atlantico",
    "cidade-nova",
    "boa-vista",
]
for slug in candidates:
    url = f"{BASE}/{slug}?ps=100000"
    r = s.get(url, timeout=30)
    if "__NEXT_DATA__" not in r.text:
        print(slug, "NO DATA")
        continue
    ads = find_ads_list(extract_next_data(r.text)) or []
    nbs = sorted(
        {
            (ad.get("locationDetails") or {}).get("neighbourhood")
            for ad in ads
            if (ad.get("locationDetails") or {}).get("neighbourhood")
        }
    )
    print(f"{slug:30} ads={len(ads):2} nbs={nbs}")
