# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — BG3 모드 자동 한글화 GUI v3.6.1
# 빌드 명령: pyinstaller bg3_autokorean_gui.spec

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_all

block_cipher = None

ctk_datas, ctk_binaries, ctk_hiddenimports = collect_all("customtkinter")
pil_datas, pil_binaries, pil_hiddenimports = collect_all("PIL")

a = Analysis(
    ["bg3_autokorean_gui.py"],
    pathex=["."],
    binaries=ctk_binaries + pil_binaries,
    datas=(
        ctk_datas
        + pil_datas
        + [("bg3core", "bg3core"), ("bg3gui", "bg3gui")]
    ),
    hiddenimports=ctk_hiddenimports + pil_hiddenimports + [
        "tkinter",
        "tkinter.messagebox",
        "tkinter.filedialog",
        "tkinter.ttk",
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
    name="BG3_AutoKorean_GUI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # UPX 비활성 — CTk 리소스 손상 방지
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # 콘솔 창 숨김 (한글 인코딩 이슈 방지)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,          # resources/icon.ico 준비 시 여기에 경로 입력
    onefile=True,
)
