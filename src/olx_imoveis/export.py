"""Exportação de resultados de busca (CSV, PDF, TXT)."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from enum import Enum
from pathlib import Path

from olx_imoveis.export_format import detail_to_export_record
from olx_imoveis.listing_display import clean_text, sort_imoveis
from olx_imoveis.models import ImovelDetalhe, SearchFilters

EXPORT_COLUMNS = ["list_id", "linha_1", "linha_2", "url", "descricao"]


class ExportFormat(str, Enum):
    CSV = "CSV"
    PDF = "PDF"
    TXT = "TXT"

    @property
    def extension(self) -> str:
        return self.value.lower()


def default_export_path(base_dir: Path, fmt: ExportFormat) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return base_dir / f"resultados_olx_{stamp}.{fmt.extension}"


def export_results(
    items: list[ImovelDetalhe],
    fmt: ExportFormat,
    path: Path,
    *,
    filter_summary: str | None = None,
    filters: SearchFilters | None = None,
) -> None:
    items = sort_imoveis(items, filters)
    rows = [detail_to_export_record(it, filters) for it in items]
    if fmt == ExportFormat.CSV:
        _export_csv(rows, path)
    elif fmt == ExportFormat.TXT:
        _export_txt(rows, path, filter_summary=filter_summary)
    elif fmt == ExportFormat.PDF:
        _export_pdf(rows, path, filter_summary=filter_summary)
    else:
        raise ValueError(f"Formato não suportado: {fmt}")


def _export_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=EXPORT_COLUMNS, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)


def _export_txt(
    rows: list[dict[str, str]],
    path: Path,
    *,
    filter_summary: str | None,
) -> None:
    lines: list[str] = []
    lines.append("RESULTADOS OLX IMÓVEIS")
    lines.append(f"Exportado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    if filter_summary:
        lines.append(f"Filtros: {filter_summary}")
    lines.append(f"Total: {len(rows)} anúncio(s)")
    lines.append("=" * 100)
    lines.append("")

    for row in rows:
        lines.append(row["linha_1"])
        lines.append(row["linha_2"])
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _find_pdf_font() -> str | None:
    candidates = [
        Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts" / "arial.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def _pdf_safe(text: str) -> str:
    return (
        text.replace("…", "...")
        .replace("m²", "m2")
        .replace("—", "-")
    )


def _export_pdf(
    rows: list[dict[str, str]],
    path: Path,
    *,
    filter_summary: str | None,
) -> None:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    title_size = 11
    body_size = 8
    line_height = 4

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    font_path = _find_pdf_font()
    if font_path:
        pdf.add_font("ExportFont", "", font_path)
        pdf.add_font("ExportFont", "B", font_path)
        body_font = "ExportFont"
    else:
        body_font = "Helvetica"

    pdf.set_font(body_font, "B", title_size)
    pdf.cell(0, line_height + 2, "Resultados OLX Imoveis", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(body_font, size=body_size)
    pdf.cell(
        0,
        line_height,
        f"Exportado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    if filter_summary:
        pdf.multi_cell(
            0,
            line_height,
            f"Filtros: {clean_text(filter_summary)}",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
    pdf.cell(0, line_height, f"Total: {len(rows)} anuncio(s)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(3)

    pdf.set_font(body_font, size=body_size)
    content_width = pdf.epw
    for i, row in enumerate(rows, start=1):
        pdf.set_font(body_font, "B", size=body_size)
        pdf.multi_cell(
            content_width,
            line_height,
            _pdf_safe(f"{i}. {row['linha_1']}"),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.set_font(body_font, size=body_size)
        pdf.multi_cell(
            content_width,
            line_height,
            _pdf_safe(row["linha_2"]),
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        pdf.ln(1.5)

    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))
