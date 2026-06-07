# tests/test_i18n.py
import importlib, sys

def _reload_i18n():
    for mod in list(sys.modules.keys()):
        if "bg3gui.i18n" in mod:
            del sys.modules[mod]

def test_t_returns_korean_by_default():
    _reload_i18n()
    from bg3gui.i18n import load, t
    load("ko")
    assert t("menu.translate") == "번역"

def test_t_returns_english():
    _reload_i18n()
    from bg3gui.i18n import load, t
    load("en")
    assert t("menu.translate") == "Translate"

def test_t_falls_back_to_key():
    _reload_i18n()
    from bg3gui.i18n import load, t
    load("ko")
    assert t("nonexistent.key") == "nonexistent.key"

def test_t_format_kwargs():
    _reload_i18n()
    from bg3gui.i18n import load, t
    load("ko")
    result = t("translate.progress", current=3, total=7, pct=42)
    assert "3" in result and "7" in result and "42" in result
