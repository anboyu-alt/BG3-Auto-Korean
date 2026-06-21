# bg3gui/i18n/__init__.py
from __future__ import annotations

import importlib

# 지원 UI 언어 코드 → 모듈명(이 패키지 내). 파일명에 하이픈을 못 쓰므로 _ 사용.
# 아직 없는 언어 파일은 자동으로 영어로 폴백된다(키 단위 폴백 포함).
_LANG_MODULES = {
    "ko": ".ko", "en": ".en", "fr": ".fr", "de": ".de", "es": ".es",
    "pl": ".pl", "ru": ".ru", "zh": ".zh", "tr": ".tr", "pt_br": ".pt_br",
    "it": ".it", "es_la": ".es_la", "zh_tw": ".zh_tw", "uk": ".uk", "ja": ".ja",
}

_strings: dict = {}
_fallback: dict = {}  # 항상 영어 — 활성 언어에 없는 키를 메운다


def _load_strings(lang_code: str) -> dict | None:
    mod = _LANG_MODULES.get(lang_code)
    if not mod:
        return None
    try:
        m = importlib.import_module(mod, __package__)
        s = getattr(m, "STRINGS", None)
        return s if isinstance(s, dict) else None
    except Exception:
        return None


def load(lang_code: str) -> None:
    global _strings, _fallback
    _fallback = _load_strings("en") or {}
    _strings = _load_strings(lang_code) or _fallback


def _format(text: str, kwargs: dict) -> str:
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            return text
    return text


def t(key: str, **kwargs) -> str:
    # 활성 언어 → 영어 폴백 → 키 자체
    text = _strings.get(key)
    if text is None:
        text = _fallback.get(key, key)
    return _format(text, kwargs)


def t_for(lang_code: str, key: str, **kwargs) -> str:
    """현재 로드된 언어와 무관하게 지정 언어로 문구를 반환(없으면 영어→키 폴백)."""
    s = _load_strings(lang_code) or {}
    text = s.get(key)
    if text is None:
        fb = _load_strings("en") or {}
        text = fb.get(key, key)
    return _format(text, kwargs)
