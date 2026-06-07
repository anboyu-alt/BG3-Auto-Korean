# bg3gui/i18n/__init__.py
from __future__ import annotations

_strings: dict = {}


def load(lang_code: str) -> None:
    global _strings
    if lang_code == "en":
        from .en import STRINGS
    else:
        from .ko import STRINGS
    _strings = STRINGS


def t(key: str, **kwargs) -> str:
    text = _strings.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text
