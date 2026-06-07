# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — BG3 Mod Translator v5.0 (PySide6)
# 빌드 명령: pyinstaller bg3_mod_translator.spec

import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all("PySide6")

a = Analysis(
    ["bg3_mod_translator.py"],
    pathex=["."],
    binaries=pyside6_binaries,
    datas=(
        pyside6_datas
        + [("bg3core", "bg3core"), ("bg3gui", "bg3gui")]
    ),
    hiddenimports=pyside6_hiddenimports + [
        "PySide6.QtWidgets",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "bg3gui.i18n.ko",
        "bg3gui.i18n.en",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["customtkinter", "tkinter", "PIL"],
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
    name="BG3_ModTranslator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # 콘솔 창 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,           # resources/icon.ico 준비 시 경로 입력
    onefile=True,
)
