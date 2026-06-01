"""Exportação de resultados de busca (CSV, PDF, TXT)."""

from __future__ import annotations

import csv
import os
from datetime import datetime
from enum import Enum
from pathlib import Path

from olx_imoveis.listing_display import clean_text, item_to_export_row
from olx_imoveis.models import ImovelResumo, SearchFilters

EXPORT_COLUMNS = [
    "list_id",
    "titulo",
    "preco",
    "oferta",
    "local",
    "bairro",
    "cidade",
    "estado",
    "quartos",
    "area_m2",
    "url",
]


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
    items: list[ImovelResumo],
    fmt: ExportFormat,
    path: Path,
    *,
    filter_summary: str | None = None,
    filters: SearchFilters | None = None,
) -> None:
    rows = [item_to_export_row(it, filters) for it in items]
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
    lines.append("=" * 78)

    for i, row in enumerate(rows, start=1):
        lines.append("")
        lines.append(f"{i}. {row['preco']}  ·  {row['oferta']}")
        lines.append(f"   {row['local']}")
        lines.append(f"   {row['titulo']}")
        extras: list[str] = []
        if row["quartos"]:
            q = int(row["quartos"])
            extras.append(f"{q} quarto" if q == 1 else f"{q} quartos")
        if row["area_m2"]:
            extras.append(f"{row['area_m2']} m²")
        extras.append(f"ID {row['list_id']}")
        if extras:
            lines.append(f"   {' · '.join(extras)}")
        lines.append(f"   {row['url']}")
        lines.append("-" * 78)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


def _export_pdf(
    rows: list[dict[str, str]],
    path: Path,
    *,
    filter_summary: str | None,
) -> None:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    font_path = _find_pdf_font()
    if font_path:
        pdf.add_font("ExportFont", "", font_path)
        pdf.add_font("ExportFont", "B", font_path)
        body_font = "ExportFont"
    else:
        body_font = "Helvetica"

    pdf.set_font(body_font, "B", 14)
    pdf.cell(0, 10, "Resultados OLX Imoveis", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(body_font, size=9)
    pdf.cell(
        0,
        6,
        f"Exportado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    if filter_summary:
        pdf.multi_cell(0, 5, f"Filtros: {clean_text(filter_summary)}")
    pdf.cell(0, 6, f"Total: {len(rows)} anuncio(s)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    col_widths = (22, 68, 28, 18, 42, 12, 12, 78)
    headers = ("ID", "Titulo", "Preco", "Oferta", "Local", "Qtd", "m2", "URL")

    pdf.set_font(body_font, "B", 8)
    for header, width in zip(headers, col_widths):
        pdf.cell(width, 7, header, border=1)
    pdf.ln()

    pdf.set_font(body_font, size=7)
    for row in rows:
        local = clean_text(row["local"])[:40]
        titulo = clean_text(row["titulo"])[:55]
        cells = (
            row["list_id"][:12],
            titulo,
            row["preco"][:18],
            row["oferta"][:10],
            local,
            row["quartos"][:4],
            row["area_m2"][:6],
            row["url"][:70],
        )
        for value, width in zip(cells, col_widths):
            pdf.cell(width, 6, value, border=1)
        pdf.ln()

    path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(path))
