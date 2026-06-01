"""Discover OLX URL patterns for todos filters."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from olx_imoveis.parsers.common import extract_next_data, find_ads_list

from curl_cffi.requests import Session

s = Session(impersonate="chrome131")
urls = [
    "https://www.olx.com.br/imoveis/estado-ba/sul-da-bahia/ilheus?ps=100000",
    "https://www.olx.com.br/imoveis/apartamentos/estado-ba/sul-da-bahia/ilheus?ps=100000",
    "https://www.olx.com.br/imoveis/venda/estado-ba/sul-da-bahia/ilheus?ps=100000",
    "https://www.olx.com.br/imoveis/aluguel/estado-ba/sul-da-bahia/ilheus?pe=20000",
]
for url in urls:
    r = s.get(url, timeout=30)
    ok = "__NEXT_DATA__" in r.text
    route = cats = n = None
    if ok:
        data = extract_next_data(r.text)
        pp = data["props"]["pageProps"]
        route = pp.get("ssrQuery", {}).get("route")
        ads = find_ads_list(data) or []
        n = len(ads)
        cats = set(ad.get("searchCategoryLevelOne") for ad in ads if ad.get("searchCategoryLevelOne"))
    print(ok, n, cats, route)
