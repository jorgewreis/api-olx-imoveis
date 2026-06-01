"""Probe OLX advertiser type filter."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from olx_imoveis.parsers.common import extract_next_data, find_ads_list

from curl_cffi.requests import Session

BASE = "https://www.olx.com.br/imoveis/venda/apartamentos/estado-ba/sul-da-bahia/ilheus?ps=100000"
s = Session(impersonate="chrome131")

for extra in ["", "&fp=1", "&fp=2", "&seller_type=professional", "&seller_type=private"]:
    url = BASE + extra
    r = s.get(url, timeout=30)
    data = extract_next_data(r.text)
    ads = find_ads_list(data) or []
    pro = sum(1 for a in ads if a.get("professionalAd"))
    filt = data["props"]["pageProps"].get("filters") or {}
    print(extra or "(none)", "n", len(ads), "pro", pro, "filters", {k: filt[k] for k in filt if "sell" in k.lower() or "part" in k.lower() or "prof" in k.lower() or k in ("fp",)})

html = s.get(BASE, timeout=30).text
for m in re.finditer(r'"(particular|profissional|professional|seller[^"]*)"', html, re.I):
    if m.group(1).lower() in ("particular", "profissional", "professional", "seller", "sellertype"):
        print("match", m.group(0)[:80])

ft = extract_next_data(html)["props"]["pageProps"].get("filtersTemplate", {})
text = json.dumps(ft, ensure_ascii=False)
for needle in ["particular", "profissional", "Particular", "Profissional", "seller_type", "fp"]:
    idx = text.lower().find(needle.lower())
    if idx >= 0:
        print("ctx", text[max(0, idx - 40) : idx + 120])
