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


def test_parse_detail_ad_detail_fixture():
    html = (FIXTURES / "detail_ad_detail_sample.html").read_text(encoding="utf-8")
    detail = parse_detail_page(
        html,
        "https://ba.olx.com.br/sul-da-bahia/imoveis/casa-em-ilheus-100002",
    )
    assert detail.list_id == "100002"
    assert "quintal" in (detail.descricao or "")
    assert detail.cidade == "Ilhéus"
    assert detail.anunciante.nome == "Corretor Exemplo"
    assert len(detail.imagens) == 1


def test_detail_creci_marks_common_seller_as_professional():
    html = (FIXTURES / "detail_sample.html").read_text(encoding="utf-8")
    html = html.replace(
        "Apartamento amplo com varanda.",
        "Apartamento amplo com varanda. CRECI/SP 123456.",
    )
    html = html.replace('"isProfessional": true', '"isProfessional": false')
    detail = parse_detail_page(html, "https://sp.olx.com.br/vi/100001.htm")
    assert detail.anunciante.is_professional is True


def test_parse_listing_missing_data():
    with pytest.raises(OlxParseError):
        parse_listing_page("<html><body>sem dados</body></html>")
