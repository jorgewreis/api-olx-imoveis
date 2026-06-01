"""Extract adDetail JSON from ba.olx detail page."""
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup
from curl_cffi.requests import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from olx_imoveis.parsers.common import ad_to_resumo

LIST_ID = "1506240881"
SLUG = (
    "apartamento-padrao-com-1-quartos-e-1-banheiros-a-venda-30-m-em-ilheus-ba-1506240881"
)
url = f"https://ba.olx.com.br/sul-da-bahia/imoveis/{SLUG}"

s = Session(impersonate="chrome131")
html = s.get(url, timeout=30).text


def extract_json_after_key(text: str, key: str) -> dict | None:
    needle = f'"{key}"'
    pos = text.find(needle)
    if pos < 0:
        return None
    start = text.find("{", pos)
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                blob = text[start : i + 1]
                try:
                    return json.loads(blob)
                except json.JSONDecodeError:
                    return None
    return None


ad_detail = extract_json_after_key(html, "adDetail")
print("adDetail keys:", list(ad_detail.keys())[:25] if ad_detail else None)
if ad_detail:
    for k in sorted(ad_detail.keys()):
        v = ad_detail[k]
        if isinstance(v, (dict, list)):
            print(f"  {k}: {type(v).__name__} len={len(v)}")
        elif v not in (None, "", 0, False):
            print(f"  {k}: {str(v)[:100]}")

for key in ["description", "body", "observation", "phones", "phone", "images", "properties"]:
    print("html count", key, html.count(f'"{key}"'))

# ld+json
soup = BeautifulSoup(html, "html.parser")
ld = soup.find("script", type="application/ld+json")
if ld and ld.string:
    data = json.loads(ld.string)
    print("ld+json keys:", list(data.keys()))

# Can ad_to_resumo work with adDetail?
if ad_detail:
    mapped = dict(ad_detail)
    if "subject" in mapped and "title" not in mapped:
        mapped["title"] = mapped["subject"]
    resumo = ad_to_resumo(mapped, "ba")
    print("ad_to_resumo:", resumo)
