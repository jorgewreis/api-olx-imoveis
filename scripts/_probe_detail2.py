"""Inspect ba.olx detail HTML for embedded JSON."""
import json
import re
import sys
from pathlib import Path

from curl_cffi.requests import Session

LIST_ID = "1506240881"
SLUG = (
    "apartamento-padrao-com-1-quartos-e-1-banheiros-a-venda-30-m-em-ilheus-ba-1506240881"
)
url = f"https://ba.olx.com.br/sul-da-bahia/imoveis/{SLUG}"

s = Session(impersonate="chrome131")
r = s.get(url, timeout=30)
html = r.text
print("len", len(html))

# script tags
for m in re.finditer(r'<script[^>]*(?:id|type)=["\']([^"\']+)["\'][^>]*>', html):
    print("script attr:", m.group(1))

# adDetail JSON blob
for pat in [
    r'"adDetail"\s*:\s*(\{)',
    r'window\.__[A-Z_]+\s*=\s*(\{)',
    r'<script[^>]*type="application/json"[^>]*>(\{.*?\})</script>',
]:
    m = re.search(pat, html, re.DOTALL)
    print("pattern", pat[:40], "match", bool(m))

idx = html.find("adDetail")
print("adDetail context:", html[idx - 40 : idx + 120].replace("\n", " ")[:200])

# Try to extract JSON around adDetail
m = re.search(r'"adDetail"\s*:\s*(\{.*?\})\s*,\s*"', html)
if m:
    print("adDetail snippet len", len(m.group(1)))

# Find all application/json scripts
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "html.parser")
for script in soup.find_all("script"):
    sid = script.get("id") or script.get("type") or "no-id"
    content = script.string or ""
    if len(content) > 100:
        print("script", sid, "len", len(content), "start", content[:80].replace("\n", " "))
        if LIST_ID in content:
            print("  contains listId")
        if "adDetail" in content or "body" in content:
            print("  contains adDetail/body")

# Search for listId with body nearby in raw html
for m in re.finditer(r'"listId"\s*:\s*' + LIST_ID, html):
    start = max(0, m.start() - 200)
    end = min(len(html), m.end() + 400)
    chunk = html[start:end]
    if "body" in chunk or "description" in chunk:
        print("listId context with body:", chunk[:500])
        break

# Try ld+json
for script in soup.find_all("script", type="application/ld+json"):
    try:
        data = json.loads(script.string)
        print("ld+json type", data.get("@type"))
    except Exception as e:
        print("ld+json err", e)
