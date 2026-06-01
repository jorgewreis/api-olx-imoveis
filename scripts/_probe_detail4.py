"""Find description text in ba.olx detail HTML."""
import json
import re
from curl_cffi.requests import Session

SLUG = (
    "apartamento-padrao-com-1-quartos-e-1-banheiros-a-venda-30-m-em-ilheus-ba-1506240881"
)
url = f"https://ba.olx.com.br/sul-da-bahia/imoveis/{SLUG}"
html = Session(impersonate="chrome131").get(url, timeout=30).text

for pat in [
    r'"description"\s*:\s*"((?:\\.|[^"\\])*)"',
    r'"observation"\s*:\s*"((?:\\.|[^"\\])*)"',
    r'"adDescription"\s*:\s*"((?:\\.|[^"\\])*)"',
]:
    m = re.search(pat, html)
    if m:
        print(pat[:30], "->", m.group(1)[:200])

# images in html
for pat in [r'"original"\s*:\s*"(https://[^"]+)"', r'"imageUrl"\s*:\s*"(https://[^"]+)"']:
    imgs = re.findall(pat, html)
    print(pat[:25], len(imgs), imgs[:2])

# phone
for pat in [r'"phone"\s*:\s*"([^"]+)"', r'"maskedPhone"\s*:\s*"([^"]+)"', r'"whatsapp"\s*:\s*"([^"]+)"']:
    m = re.search(pat, html)
    if m:
        print("phone pat", pat, m.group(1))

# Look for description in ld+json Object
from bs4 import BeautifulSoup

soup = BeautifulSoup(html, "html.parser")
ld = json.loads(soup.find("script", type="application/ld+json").string)
print("Object keys", ld.get("Object", {}).keys() if isinstance(ld.get("Object"), dict) else ld.get("Object"))
obj = ld.get("Object", {})
if isinstance(obj, dict):
    print("desc", obj.get("description", "")[:200])
