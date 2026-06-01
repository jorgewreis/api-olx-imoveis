"""Testes de exportação e formatação."""

from pathlib import Path

from olx_imoveis.export import ExportFormat, export_results
from olx_imoveis.export_format import (
    format_export_line1,
    format_export_line2,
    format_phone_export,
    summarize_description,
)
from olx_imoveis.listing_display import clean_text, format_location, format_price
from olx_imoveis.models import Anunciante, ImovelDetalhe, SearchFilters, TipoOferta


def _sample_detail() -> ImovelDetalhe:
    return ImovelDetalhe(
        list_id="123",
        titulo="Apartamento 2 quartos Centro",
        preco=350_000,
        url="https://www.olx.com.br/vi/123.htm",
        bairro="Pontal",
        cidade="Ilhéus",
        estado="BA",
        quartos=2,
        area_m2=64,
        tipo_oferta=TipoOferta.VENDA,
        descricao="Apartamento amplo com varanda gourmet e vista para o mar. Ótima localização.",
        atributos={
            "Quartos": "2",
            "Banheiros": "3",
            "Vagas": "1",
            "Área útil": "64 m²",
            "Características": "Varanda, Elevador",
        },
        anunciante=Anunciante(nome="Joaquim Souza"),
        telefone="(73) 98832-1232",
    )


def test_clean_text_normalizes_spaces():
    assert clean_text("  Apartamento   amplo  ") == "Apartamento amplo"


def test_format_price():
    assert format_price(_sample_detail()) == "R$ 350.000,00"


def test_format_location():
    assert format_location(_sample_detail()) == "Pontal · Ilhéus · BA"


def test_format_phone_export():
    assert format_phone_export("(73) 98832-1232") == "73 98832-1232"


def test_export_lines_format():
    detail = _sample_detail()
    filters = SearchFilters(estado="ba", regiao="ilheus", tipo_oferta=TipoOferta.VENDA)
    line1 = format_export_line1(detail, filters)
    line2 = format_export_line2(detail)

    assert line1 == "BA - ILHÉUS - PONTAL | VENDA: R$ 350.000,00 | JOAQUIM SOUZA - 73 98832-1232"
    assert "2 quartos" in line2
    assert "3 banheiros" in line2
    assert "1 garagem" in line2
    assert "64m²" in line2
    assert "varanda" in line2
    assert "| Apartamento amplo" in line2


def test_summarize_description_truncates():
    long_text = "A " * 200
    summary = summarize_description(long_text, max_len=50)
    assert len(summary) <= 51
    assert summary.endswith("…")


def test_export_csv_and_txt(tmp_path: Path):
    detail = _sample_detail()
    filters = SearchFilters(estado="ba", regiao="ilheus", tipo_oferta=TipoOferta.VENDA)

    csv_path = tmp_path / "out.csv"
    export_results([detail], ExportFormat.CSV, csv_path, filters=filters)
    content = csv_path.read_text(encoding="utf-8-sig")
    assert "linha_1" in content
    assert "BA - ILHÉUS - PONTAL" in content
    assert "350.000" in content

    txt_path = tmp_path / "out.txt"
    export_results([detail], ExportFormat.TXT, txt_path, filter_summary="Venda", filters=filters)
    txt = txt_path.read_text(encoding="utf-8")
    assert "BA - ILHÉUS - PONTAL | VENDA: R$ 350.000,00" in txt
    assert "2 quartos, 3 banheiros" in txt


def test_export_pdf(tmp_path: Path):
    detail = _sample_detail()
    pdf_path = tmp_path / "out.pdf"
    export_results([detail], ExportFormat.PDF, pdf_path, filter_summary="Teste")
    assert pdf_path.stat().st_size > 500
