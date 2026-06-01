# -*- mode: python ; coding: utf-8 -*-
# Build: pyinstaller build/olx_imoveis.spec

import sys
from pathlib import Path

block_cipher = None
root = Path(SPECPATH).parent
src = root / "src"
data_dir = root / "data"

a = Analysis(
    [str(src / "gui" / "app.py")],
    pathex=[str(src)],
    binaries=[],
    datas=[(str(data_dir), "data")],
    hiddenimports=[
        "customtkinter",
        "PIL",
        "PIL._tkinter_finder",
        "pydantic",
        "pydantic_settings",
        "httpx",
        "curl_cffi",
        "curl_cffi.requests",
        "bs4",
        "fpdf",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="OlxImoveis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
