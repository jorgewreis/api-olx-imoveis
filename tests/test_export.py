"""Testes de exportação e formatação."""

from pathlib import Path

import pytest

from olx_imoveis.export import ExportFormat, export_results
from olx_imoveis.listing_display import clean_text, format_location, format_price
from olx_imoveis.models import ImovelResumo, SearchFilters, TipoOferta


def _sample_item() -> ImovelResumo:
    return ImovelResumo(
        list_id="123",
        titulo="Apartamento 2 quartos  Centro",
        preco=450_000,
        url="https://www.olx.com.br/vi/123.htm",
        bairro="Centro",
        cidade="Ilhéus",
        estado="BA",
        quartos=2,
        area_m2=65,
        tipo_oferta=TipoOferta.VENDA,
    )


def test_clean_text_normalizes_spaces():
    assert clean_text("  Apartamento   amplo  ") == "Apartamento amplo"


def test_format_price():
    assert format_price(_sample_item()) == "R$ 450.000,00"


def test_format_location():
    assert format_location(_sample_item()) == "Centro · Ilhéus · BA"


def test_export_csv_and_txt(tmp_path: Path):
    item = _sample_item()
    filters = SearchFilters(estado="ba", regiao="ilheus", tipo_oferta=TipoOferta.VENDA)

    csv_path = tmp_path / "out.csv"
    export_results([item], ExportFormat.CSV, csv_path, filters=filters)
    content = csv_path.read_text(encoding="utf-8-sig")
    assert "list_id" in content
    assert "123" in content
    assert "450.000" in content

    txt_path = tmp_path / "out.txt"
    export_results([item], ExportFormat.TXT, txt_path, filter_summary="Venda", filters=filters)
    txt = txt_path.read_text(encoding="utf-8")
    assert "RESULTADOS OLX" in txt
    assert "Apartamento 2 quartos" in txt


def test_export_pdf(tmp_path: Path):
    item = _sample_item()
    pdf_path = tmp_path / "out.pdf"
    export_results([item], ExportFormat.PDF, pdf_path, filter_summary="Teste")
    assert pdf_path.stat().st_size > 500
