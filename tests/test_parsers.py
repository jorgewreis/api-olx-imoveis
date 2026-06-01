from pathlib import Path

import pytest

from olx_imoveis.errors import OlxParseError
from olx_imoveis.parsers.detail import parse_detail_page
from olx_imoveis.parsers.listing import parse_listing_page

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_listing_fixture():
    html = (FIXTURES / "listing_sample.html").read_text(encoding="utf-8")
    result = parse_listing_page(html, pagina=1, fallback_uf="sp")
    assert len(result.items) == 2
    assert result.items[0].list_id == "100001"
    assert result.items[0].preco == 450000
    assert result.items[0].bairro == "Centro"
    assert result.total == 42


def test_parse_detail_fixture():
    html = (FIXTURES / "detail_sample.html").read_text(encoding="utf-8")
    detail = parse_detail_page(html, "https://sp.olx.com.br/vi/100001.htm")
    assert detail.list_id == "100001"
    assert "varanda" in (detail.descricao or "")
    assert detail.anunciante.nome == "Imobiliária Exemplo"
    assert detail.anunciante.is_professional is True
    assert detail.telefone is not None
    assert len(detail.imagens) == 2
    assert "Quartos" in detail.atributos


def test_parse_listing_missing_data():
    with pytest.raises(OlxParseError):
        parse_listing_page("<html><body>sem dados</body></html>")
