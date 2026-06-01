"""Extract seller filter config from OLX."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from olx_imoveis.parsers.common import extract_next_data
from curl_cffi.requests import Session

s = Session(impersonate="chrome131")
html = s.get(
    "https://www.olx.com.br/imoveis/venda/apartamentos/estado-ba/sul-da-bahia/ilheus?ps=100000",
    timeout=30,
).text
ft = extract_next_data(html)["props"]["pageProps"].get("filtersTemplate", {})


def walk(obj, path=""):
    if isinstance(obj, dict):
        label = str(obj.get("label", "")).lower()
        if "particular" in label or "profissional" in label or obj.get("strategy") == "company_ad":
            print("NODE", path, json.dumps(obj, ensure_ascii=False)[:400])
        for k, v in obj.items():
            walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, f"{path}[{i}]")


walk(ft)
