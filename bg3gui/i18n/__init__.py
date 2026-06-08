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


def t_for(lang_code: str, key: str, **kwargs) -> str:
    """현재 로드된 언어와 무관하게, 지정한 언어로 문구를 반환한다.

    앱 UI 언어를 막 바꿔 저장했지만 아직 재시작 전이라 전역 _strings가 이전
    언어인 상황에서, 새 언어로 안내를 보여줄 때 사용한다.
    """
    if lang_code == "en":
        from .en import STRINGS
    else:
        from .ko import STRINGS
    text = STRINGS.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text
