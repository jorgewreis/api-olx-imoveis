"""Catálogo de estados, regiões e bairros (editável via JSON)."""

import json
import sys
from pathlib import Path


def _data_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "data"
    return Path(__file__).resolve().parents[2] / "data"


DATA_DIR = _data_dir()

ESTADOS: dict[str, str] = {
    "ac": "Acre",
    "al": "Alagoas",
    "ap": "Amapá",
    "am": "Amazonas",
    "ba": "Bahia",
    "ce": "Ceará",
    "df": "Distrito Federal",
    "es": "Espírito Santo",
    "go": "Goiás",
    "ma": "Maranhão",
    "mt": "Mato Grosso",
    "ms": "Mato Grosso do Sul",
    "mg": "Minas Gerais",
    "pa": "Pará",
    "pb": "Paraíba",
    "pr": "Paraná",
    "pe": "Pernambuco",
    "pi": "Piauí",
    "rj": "Rio de Janeiro",
    "rn": "Rio Grande do Norte",
    "rs": "Rio Grande do Sul",
    "ro": "Rondônia",
    "rr": "Roraima",
    "sc": "Santa Catarina",
    "sp": "São Paulo",
    "se": "Sergipe",
    "to": "Tocantins",
}

DEFAULT_UF = "ba"
DEFAULT_REGIAO_NOME = "Ilhéus"

DEFAULT_REGIOES: dict[str, list[dict[str, str]]] = {
    "sp": [
        {"slug": "estado-sp", "nome": "Todo o estado"},
        {"slug": "sao-paulo-e-regiao", "nome": "São Paulo e região"},
        {"slug": "campinas-e-regiao", "nome": "Campinas e região"},
    ],
    "rj": [
        {"slug": "estado-rj", "nome": "Todo o estado"},
        {"slug": "rio-de-janeiro-e-regiao", "nome": "Rio de Janeiro e região"},
    ],
    "mg": [
        {"slug": "estado-mg", "nome": "Todo o estado"},
        {"slug": "belo-horizonte-e-regiao", "nome": "Belo Horizonte e região"},
    ],
    "ba": [
        {"slug": "estado-ba", "nome": "Todo o estado"},
        {"slug": "sul-da-bahia/ilheus", "nome": "Ilhéus"},
    ],
}


def _regions_file(uf: str) -> Path:
    return DATA_DIR / f"regions_{uf.lower()}.json"


def load_regions(uf: str) -> list[dict[str, str]]:
    uf = uf.lower()
    path = _regions_file(uf)
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("regioes", data) if isinstance(data, dict) else data
    return DEFAULT_REGIOES.get(uf, [{"slug": f"estado-{uf}", "nome": f"Todo o estado ({uf.upper()})"}])


def load_neighborhoods(uf: str, regiao_slug: str) -> list[dict[str, str]]:
    uf = uf.lower()
    path = _regions_file(uf)
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
        bairros = data.get("bairros", {})
        return bairros.get(regiao_slug, [])
    return []
