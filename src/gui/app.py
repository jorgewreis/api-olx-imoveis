"""Aplicativo desktop — busca de imóveis OLX."""

from __future__ import annotations

import csv
import logging
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk

from olx_imoveis.config import settings
from olx_imoveis.errors import OlxError, OlxParseError, OlxRateLimitError
from olx_imoveis.locations import DEFAULT_REGIAO_NOME, DEFAULT_UF, ESTADOS, load_neighborhoods, load_regions
from olx_imoveis.models import (
    ImovelDetalhe,
    ImovelResumo,
    SearchFilters,
    SearchResult,
    TipoAnunciante,
    TipoImovel,
    TipoOferta,
)
from olx_imoveis.service import OlxImoveisService

from gui.disclaimer import show_disclaimer

logging.basicConfig(
    filename=settings.logs_dir / "app.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

TIPO_IMOVEL_LABELS = {
    TipoImovel.APARTAMENTOS: "Apartamentos",
    TipoImovel.CASAS: "Casas",
    TipoImovel.TERRENOS: "Terrenos",
    TipoImovel.COMERCIO: "Comércio e indústria",
    TipoImovel.TEMPORADA: "Temporada",
    TipoImovel.QUARTOS: "Aluguel de quartos",
}
MOSTRAR_TODOS = "Mostrar todos"


class OlxImoveisApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title("OLX Imóveis — Busca")
        self.geometry("1100x720")
        self.minsize(900, 600)

        self._service = OlxImoveisService()
        self._last_result: SearchResult | None = None
        self._current_filters: SearchFilters | None = None
        self._selected: ImovelResumo | None = None

        self._build_layout()
        self._populate_estados()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_layout(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._sidebar = ctk.CTkFrame(self, width=280)
        self._sidebar.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        self._build_filters(self._sidebar)

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        self._results_frame = ctk.CTkScrollableFrame(right, label_text="Resultados")
        self._results_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
        self._results_frame.grid_columnconfigure(0, weight=1)

        self._detail_frame = ctk.CTkScrollableFrame(right, label_text="Detalhe do imóvel")
        self._detail_frame.grid(row=1, column=0, sticky="nsew", pady=(4, 0))
        self._detail_frame.grid_columnconfigure(0, weight=1)

        self._status = ctk.CTkLabel(self, text="Pronto.", anchor="w")
        self._status.grid(row=1, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 8))

    def _build_filters(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(parent, text="Filtros", font=ctk.CTkFont(size=16, weight="bold")).pack(
            anchor="w", padx=12, pady=(12, 8)
        )

        ctk.CTkLabel(parent, text="Estado").pack(anchor="w", padx=12)
        self._estado = ctk.CTkComboBox(parent, values=[], command=self._on_estado_change)
        self._estado.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(parent, text="Região / cidade").pack(anchor="w", padx=12)
        self._regiao = ctk.CTkComboBox(parent, values=[], command=self._on_regiao_change)
        self._regiao.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(parent, text="Bairro (opcional)").pack(anchor="w", padx=12)
        self._bairro = ctk.CTkComboBox(parent, values=["— Nenhum —"])
        self._bairro.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(parent, text="Oferta").pack(anchor="w", padx=12)
        self._oferta = ctk.CTkComboBox(parent, values=[MOSTRAR_TODOS, "Venda", "Aluguel"])
        self._oferta.set("Venda")
        self._oferta.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(parent, text="Tipo de imóvel").pack(anchor="w", padx=12)
        self._tipo = ctk.CTkComboBox(
            parent,
            values=[MOSTRAR_TODOS, *[TIPO_IMOVEL_LABELS[t] for t in TipoImovel]],
        )
        self._tipo.set(TIPO_IMOVEL_LABELS[TipoImovel.APARTAMENTOS])
        self._tipo.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(parent, text="Tipo de anunciante").pack(anchor="w", padx=12)
        self._anunciante = ctk.CTkComboBox(
            parent, values=[MOSTRAR_TODOS, "Comum", "Profissional"]
        )
        self._anunciante.set(MOSTRAR_TODOS)
        self._anunciante.pack(fill="x", padx=12, pady=(0, 8))

        price_row = ctk.CTkFrame(parent, fg_color="transparent")
        price_row.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(price_row, text="Preço mín").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(price_row, text="Preço máx").grid(row=0, column=1, sticky="w", padx=(8, 0))
        self._preco_min = ctk.CTkEntry(price_row, placeholder_text="R$")
        self._preco_min.grid(row=1, column=0, sticky="ew")
        self._preco_max = ctk.CTkEntry(price_row, placeholder_text="R$")
        self._preco_max.grid(row=1, column=1, sticky="ew", padx=(8, 0))
        price_row.grid_columnconfigure(0, weight=1)
        price_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(parent, text="Quartos (mín.)").pack(anchor="w", padx=12)
        self._quartos = ctk.CTkEntry(parent, placeholder_text="Ex: 2")
        self._quartos.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(parent, text="Termo de busca").pack(anchor="w", padx=12)
        self._termo = ctk.CTkEntry(parent, placeholder_text="Opcional")
        self._termo.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkButton(parent, text="Buscar", command=self._on_search).pack(
            fill="x", padx=12, pady=(0, 6)
        )
        ctk.CTkButton(
            parent, text="Carregar mais", fg_color="gray", command=self._on_load_more
        ).pack(fill="x", padx=12, pady=(0, 6))
        ctk.CTkButton(
            parent, text="Exportar CSV", fg_color="gray", command=self._export_csv
        ).pack(fill="x", padx=12, pady=(0, 6))
        ctk.CTkButton(parent, text="Sobre / Aviso legal", fg_color="transparent", command=self._show_about).pack(
            fill="x", padx=12, pady=(0, 12)
        )

        self._region_map: dict[str, str] = {}
        self._bairro_map: dict[str, str] = {}

    def _populate_estados(self) -> None:
        labels = [f"{uf.upper()} — {nome}" for uf, nome in sorted(ESTADOS.items())]
        self._estado.configure(values=labels)
        default_label = next(
            (label for label in labels if label.startswith(f"{DEFAULT_UF.upper()} ")),
            labels[0],
        )
        self._estado.set(default_label)
        self._load_regioes(default_label, prefer_regiao=DEFAULT_REGIAO_NOME)

    def _load_regioes(self, estado_label: str, prefer_regiao: str | None = None) -> None:
        uf = self._uf_from_label(estado_label)
        regions = load_regions(uf)
        self._region_map = {r["nome"]: r["slug"] for r in regions}
        names = list(self._region_map.keys())
        self._regiao.configure(values=names)
        if not names:
            return
        selected = prefer_regiao if prefer_regiao in names else names[0]
        self._regiao.set(selected)
        self._on_regiao_change(selected)

    def _on_estado_change(self, _choice: str) -> None:
        self._load_regioes(self._estado.get())

    def _uf_from_label(self, label: str) -> str:
        return label.split("—")[0].strip().lower()

    def _on_regiao_change(self, _choice: str) -> None:
        uf = self._uf_from_label(self._estado.get())
        slug = self._region_map.get(self._regiao.get(), "")
        bairros = load_neighborhoods(uf, slug)
        self._bairro_map = {b["nome"]: b["slug"] for b in bairros}
        values = ["— Nenhum —"] + list(self._bairro_map.keys())
        self._bairro.configure(values=values)
        self._bairro.set("— Nenhum —")

    def _parse_int(self, entry: ctk.CTkEntry) -> int | None:
        raw = entry.get().strip().replace(".", "").replace(",", "")
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def _build_filters_model(self, pagina: int = 1) -> SearchFilters:
        uf = self._uf_from_label(self._estado.get())
        regiao = self._region_map.get(self._regiao.get(), f"estado-{uf}")
        bairro_sel = self._bairro.get()
        bairro = None
        if bairro_sel and bairro_sel != "— Nenhum —":
            bairro = self._bairro_map.get(bairro_sel)

        label_to_tipo = {v: k for k, v in TIPO_IMOVEL_LABELS.items()}
        tipo_raw = self._tipo.get().strip()
        tipo = None if tipo_raw == MOSTRAR_TODOS else label_to_tipo[tipo_raw]

        oferta_raw = self._oferta.get().strip().lower()
        if oferta_raw == MOSTRAR_TODOS.lower():
            oferta = None
        elif oferta_raw == "aluguel":
            oferta = TipoOferta.ALUGUEL
        else:
            oferta = TipoOferta.VENDA

        anunciante_raw = self._anunciante.get().strip().lower()
        if anunciante_raw == MOSTRAR_TODOS.lower():
            tipo_anunciante = None
        elif anunciante_raw == "profissional":
            tipo_anunciante = TipoAnunciante.PROFISSIONAL
        else:
            tipo_anunciante = TipoAnunciante.COMUM

        pmin = self._parse_int(self._preco_min)
        pmax = self._parse_int(self._preco_max)
        if pmin is not None and pmax is not None and pmin > pmax:
            raise ValueError("Preço mínimo não pode ser maior que o máximo.")

        quartos = self._parse_int(self._quartos)
        termo = self._termo.get().strip() or None

        return SearchFilters(
            estado=uf,
            regiao=regiao,
            bairro=bairro,
            tipo_imovel=tipo,
            tipo_oferta=oferta,
            tipo_anunciante=tipo_anunciante,
            preco_min=pmin,
            preco_max=pmax,
            quartos_min=quartos,
            termo=termo,
            pagina=pagina,
        )

    def _set_status(self, text: str) -> None:
        self._status.configure(text=text)

    def _run_bg(self, work: Callable[[], None]) -> None:
        def runner():
            try:
                work()
            except OlxParseError as e:
                logging.exception("Erro de parsing")
                msg = (
                    f"{e}\n\nO site da OLX pode ter mudado. "
                    "Atualize o aplicativo ou tente novamente mais tarde."
                )
                self.after(0, lambda: self._show_error(msg))
            except OlxRateLimitError as e:
                self.after(0, lambda: self._show_error(str(e)))
            except OlxError as e:
                self.after(0, lambda: self._show_error(str(e)))
            except Exception as e:
                logging.exception("Erro em tarefa em background")
                self.after(0, lambda: self._show_error(str(e)))

        threading.Thread(target=runner, daemon=True).start()

    def _show_error(self, msg: str) -> None:
        messagebox.showerror("Erro", msg)
        self._set_status("Erro na operação.")

    def _clear_results_ui(self) -> None:
        for w in self._results_frame.winfo_children():
            w.destroy()

    def _clear_detail_ui(self) -> None:
        for w in self._detail_frame.winfo_children():
            w.destroy()

    def _render_results(self, result: SearchResult, append: bool = False) -> None:
        if not append:
            self._clear_results_ui()

        if not result.items and not append:
            ctk.CTkLabel(
                self._results_frame,
                text="Nenhum imóvel encontrado. Ajuste os filtros.",
            ).grid(sticky="w", padx=8, pady=8)
            return

        start = len(self._results_frame.winfo_children()) if append else 0
        for i, item in enumerate(result.items):
            row = ctk.CTkFrame(self._results_frame)
            row.grid(row=start + i, column=0, sticky="ew", padx=4, pady=4)
            row.grid_columnconfigure(1, weight=1)

            preco = item.preco_label or (
                f"R$ {item.preco:,}".replace(",", ".") if item.preco else "Consulte"
            )
            loc = ", ".join(x for x in [item.bairro, item.cidade, item.estado] if x)
            text = f"{item.titulo}\n{preco} — {loc}"

            btn = ctk.CTkButton(
                row,
                text=text,
                anchor="w",
                fg_color=("gray85", "gray25"),
                text_color=("black", "white"),
                command=lambda it=item: self._on_select_item(it),
            )
            btn.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=8)

        total_txt = f" — total estimado: {result.total}" if result.total else ""
        filtros = self._format_filter_summary(self._current_filters) if self._current_filters else ""
        prefix = f"{filtros} — " if filtros else ""
        self._set_status(f"{prefix}{len(result.items)} anúncio(s) exibido(s){total_txt}.")

    def _format_filter_summary(self, filters: SearchFilters) -> str:
        if filters.tipo_oferta is None:
            oferta = MOSTRAR_TODOS
        else:
            oferta = "Aluguel" if filters.tipo_oferta == TipoOferta.ALUGUEL else "Venda"
        if filters.tipo_imovel is None:
            tipo = MOSTRAR_TODOS
        else:
            tipo = TIPO_IMOVEL_LABELS.get(filters.tipo_imovel, filters.tipo_imovel.value)
        if filters.tipo_anunciante is None:
            anunciante = MOSTRAR_TODOS
        elif filters.tipo_anunciante == TipoAnunciante.PROFISSIONAL:
            anunciante = "Profissional"
        else:
            anunciante = "Comum"
        cidade = self._regiao.get() if hasattr(self, "_regiao") else filters.regiao
        parts = [oferta, tipo, anunciante, cidade]
        if filters.bairro:
            bairro_nome = next(
                (nome for nome, slug in self._bairro_map.items() if slug == filters.bairro),
                filters.bairro,
            )
            parts.append(bairro_nome)
        if filters.preco_min is not None or filters.preco_max is not None:
            pmin = filters.preco_min or "…"
            pmax = filters.preco_max or "…"
            parts.append(f"R$ {pmin}-{pmax}")
        if filters.quartos_min is not None:
            parts.append(f"{filters.quartos_min}+ quartos")
        if filters.termo:
            parts.append(f'"{filters.termo}"')
        return " · ".join(parts)

    def _on_search(self) -> None:
        try:
            filters = self._build_filters_model(pagina=1)
        except ValueError as e:
            self._show_error(str(e))
            return

        self._current_filters = filters
        self._set_status(f"{self._format_filter_summary(filters)} — buscando…")
        self._clear_detail_ui()

        def work():
            result = self._service.search(filters)
            self._last_result = result
            self.after(0, lambda: self._render_results(result))

        self._run_bg(work)

    def _on_load_more(self) -> None:
        if not self._current_filters or not self._last_result or not self._last_result.tem_mais:
            self._show_error("Faça uma busca primeiro ou não há mais páginas.")
            return

        self._current_filters.pagina += 1
        filters = self._current_filters.model_copy()
        self._set_status(f"Carregando página {filters.pagina}…")

        def work():
            result = self._service.search(filters, use_cache=False)
            if self._last_result:
                self._last_result.items.extend(result.items)
                self._last_result.tem_mais = result.tem_mais
            self.after(0, lambda: self._render_results(result, append=True))

        self._run_bg(work)

    def _on_select_item(self, item: ImovelResumo) -> None:
        self._selected = item
        self._set_status(f"Carregando detalhe: {item.titulo[:40]}…")
        self._clear_detail_ui()

        def work():
            detail = self._service.get_detail(item.url)
            self.after(0, lambda: self._render_detail(detail))

        self._run_bg(work)

    def _render_detail(self, d: ImovelDetalhe) -> None:
        self._clear_detail_ui()
        r = 0

        ctk.CTkLabel(
            self._detail_frame, text=d.titulo, font=ctk.CTkFont(size=15, weight="bold"), wraplength=700
        ).grid(row=r, column=0, sticky="w", padx=8, pady=4)
        r += 1

        preco = d.preco_label or (f"R$ {d.preco:,}".replace(",", ".") if d.preco else "")
        if preco:
            ctk.CTkLabel(self._detail_frame, text=preco, font=ctk.CTkFont(size=14)).grid(
                row=r, column=0, sticky="w", padx=8
            )
            r += 1

        loc = ", ".join(x for x in [d.bairro, d.cidade, d.estado] if x)
        if loc:
            ctk.CTkLabel(self._detail_frame, text=loc).grid(row=r, column=0, sticky="w", padx=8)
            r += 1

        if d.atributos:
            attrs = "\n".join(f"• {k}: {v}" for k, v in d.atributos.items())
            ctk.CTkLabel(self._detail_frame, text="Características", font=ctk.CTkFont(weight="bold")).grid(
                row=r, column=0, sticky="w", padx=8, pady=(8, 0)
            )
            r += 1
            ctk.CTkLabel(self._detail_frame, text=attrs, justify="left").grid(row=r, column=0, sticky="w", padx=8)
            r += 1

        if d.descricao:
            ctk.CTkLabel(self._detail_frame, text="Descrição", font=ctk.CTkFont(weight="bold")).grid(
                row=r, column=0, sticky="w", padx=8, pady=(8, 0)
            )
            r += 1
            desc = ctk.CTkTextbox(self._detail_frame, height=120, wrap="word")
            desc.grid(row=r, column=0, sticky="ew", padx=8, pady=4)
            desc.insert("1.0", d.descricao)
            desc.configure(state="disabled")
            r += 1

        ctk.CTkLabel(self._detail_frame, text="Anunciante", font=ctk.CTkFont(weight="bold")).grid(
            row=r, column=0, sticky="w", padx=8, pady=(8, 0)
        )
        r += 1
        nome = d.anunciante.nome or "Não informado"
        pro = " (profissional)" if d.anunciante.is_professional else ""
        ctk.CTkLabel(self._detail_frame, text=f"{nome}{pro}").grid(row=r, column=0, sticky="w", padx=8)
        r += 1

        tel_row = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        tel_row.grid(row=r, column=0, sticky="ew", padx=8, pady=8)
        if d.telefone:
            tel_txt = d.telefone + (" (parcial)" if d.telefone_mascarado else "")
            ctk.CTkLabel(tel_row, text=f"Telefone: {tel_txt}").pack(side="left")
            ctk.CTkButton(
                tel_row, text="Copiar", width=80, command=lambda t=d.telefone: self._copy(t)
            ).pack(side="left", padx=8)
        else:
            ctk.CTkLabel(
                tel_row,
                text="Telefone não disponível nos dados públicos. Abra o anúncio no site.",
            ).pack(side="left")

        btn_row = ctk.CTkFrame(self._detail_frame, fg_color="transparent")
        btn_row.grid(row=r + 1, column=0, sticky="w", padx=8, pady=8)
        ctk.CTkButton(btn_row, text="Abrir na OLX", command=lambda: webbrowser.open(d.url)).pack(
            side="left", padx=(0, 8)
        )

        self._set_status("Detalhe carregado.")

    def _copy(self, text: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(text)
        self._set_status("Telefone copiado.")

    def _export_csv(self) -> None:
        if not self._last_result or not self._last_result.items:
            self._show_error("Não há resultados para exportar.")
            return
        path = settings.app_data_dir / "resultados_olx.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["list_id", "titulo", "preco", "bairro", "cidade", "estado", "url"])
            for it in self._last_result.items:
                w.writerow(
                    [it.list_id, it.titulo, it.preco, it.bairro, it.cidade, it.estado, it.url]
                )
        messagebox.showinfo("Exportado", f"Arquivo salvo em:\n{path}")

    def _show_about(self) -> None:
        messagebox.showinfo(
            "Sobre",
            "OLX Imóveis Desktop v1.0\n\n"
            "Busca pública de imóveis (não oficial).\n"
            "Dados: site olx.com.br\n\n"
            "Logs: " + str(settings.logs_dir),
        )

    def _on_close(self) -> None:
        self._service.close()
        self.destroy()


def main() -> None:
    app = OlxImoveisApp()
    if not show_disclaimer(app):
        app.destroy()
        sys.exit(0)
    app.mainloop()


if __name__ == "__main__":
    main()
