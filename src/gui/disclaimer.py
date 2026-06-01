"""Tela de aceite de termos na primeira execução."""

import customtkinter as ctk

from olx_imoveis.config import settings

DISCLAIMER_TEXT = """
AVISO IMPORTANTE

Este aplicativo consulta informações publicamente exibidas no site olx.com.br.
Não é afiliado à OLX nem utiliza a API oficial de integração para anunciantes.

• Use apenas para fins pessoais de busca de imóveis.
• Dados de contato (telefone) são tratados conforme a LGPD — não compartilhe bases de terceiros.
• O site da OLX pode alterar seu formato; neste caso, atualize o aplicativo.
• Respeite os Termos de Uso da OLX e evite excesso de consultas automatizadas.

Ao continuar, você declara estar ciente dessas condições.
"""


def show_disclaimer(parent: ctk.CTk) -> bool:
    if settings.disclaimer_flag_path.is_file():
        return True

    accepted = {"ok": False}

    dialog = ctk.CTkToplevel(parent)
    dialog.title("Termos de uso do aplicativo")
    dialog.geometry("520x420")
    dialog.transient(parent)
    dialog.grab_set()

    text = ctk.CTkTextbox(dialog, wrap="word", height=280)
    text.pack(fill="both", expand=True, padx=16, pady=(16, 8))
    text.insert("1.0", DISCLAIMER_TEXT.strip())
    text.configure(state="disabled")

    def accept():
        settings.disclaimer_flag_path.write_text("accepted", encoding="utf-8")
        accepted["ok"] = True
        dialog.destroy()

    def decline():
        accepted["ok"] = False
        dialog.destroy()

    btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_frame.pack(fill="x", padx=16, pady=16)
    ctk.CTkButton(btn_frame, text="Aceito e desejo continuar", command=accept).pack(
        side="left", padx=(0, 8)
    )
    ctk.CTkButton(btn_frame, text="Sair", fg_color="gray", command=decline).pack(side="left")

    parent.wait_window(dialog)
    return accepted["ok"]
