# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — BG3 Mod Translator v6.0 (PySide6)
# 빌드 명령: pyinstaller bg3_mod_translator.spec

import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# 필요한 Qt 모듈만 선택적으로 수집 (QtWebEngine 등 불필요한 모듈 제외)
_qt_datas, _qt_binaries, _qt_hiddenimports = [], [], []
for mod in ("PySide6.QtWidgets", "PySide6.QtCore", "PySide6.QtGui"):
    d, b, h = collect_all(mod)
    _qt_datas += d
    _qt_binaries += b
    _qt_hiddenimports += h

a = Analysis(
    ["bg3_mod_translator.py"],
    pathex=["."],
    binaries=_qt_binaries,
    datas=(
        _qt_datas
        + [("bg3core", "bg3core"), ("bg3gui", "bg3gui")]
    ),
    hiddenimports=_qt_hiddenimports + [
        "PySide6.QtWidgets",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "bg3gui.i18n.ko",
        "bg3gui.i18n.en",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "customtkinter", "tkinter", "PIL",
        "PySide6.QtWebEngine", "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets", "PySide6.QtMultimedia",
        "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtCharts",
        "PySide6.QtDataVisualization", "PySide6.QtQuick", "PySide6.QtQml",
        "PySide6.QtNetwork", "PySide6.QtBluetooth", "PySide6.QtSensors",
        "PySide6.QtLocation", "PySide6.QtPositioning", "PySide6.QtPdf",
    ],
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
