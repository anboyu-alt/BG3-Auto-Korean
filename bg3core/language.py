"""Language profile management and multi-language support for v5.0."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .constants import CONTENT_BLOCK_RE


@dataclass(frozen=True)
class LanguageProfile:
    """Immutable language profile for BG3 localization."""

    folder_name: str    # BG3 Localization subfolder (e.g. "Korean")
    display_name: str   # UI label (e.g. "한국어 (Korean)")
    lang_code: str      # Pak suffix / UUID namespace (e.g. "KR")
    script_type: str    # "hangul" | "cjk" | "japanese" | "cyrillic" | "latin"


# Character ranges for each script type to detect pre-translated content
_SCRIPT_RANGES: Dict[str, List[Tuple[str, str]]] = {
    "hangul":   [("가", "힣"), ("㄰", "㆏")],  # Hangul syllables + Hangul compatibility jamo
    "cjk":      [("一", "鿿")],                # CJK Unified Ideographs
    "japanese": [("ぁ", "ゖ"), ("ァ", "ヿ")],  # Hiragana + Katakana
    "cyrillic": [("А", "я")],                  # Cyrillic letters
}

# All 15 BG3 languages with metadata
LANGUAGE_PROFILES: Dict[str, LanguageProfile] = {
    "Korean":              LanguageProfile("Korean",              "한국어 (Korean)",                        "KR",    "hangul"),
    "English":             LanguageProfile("English",             "English",                                "EN",    "latin"),
    "French":              LanguageProfile("French",              "Français (French)",                      "FR",    "latin"),
    "German":              LanguageProfile("German",              "Deutsch (German)",                       "DE",    "latin"),
    "Spanish":             LanguageProfile("Spanish",             "Español (Spanish)",                      "ES",    "latin"),
    "Polish":              LanguageProfile("Polish",              "Polski (Polish)",                        "PL",    "latin"),
    "Russian":             LanguageProfile("Russian",             "Русский (Russian)",                      "RU",    "cyrillic"),
    "Chinese":             LanguageProfile("Chinese",             "中文(简体) (Chinese Simplified)",         "ZH",    "cjk"),
    "Turkish":             LanguageProfile("Turkish",             "Türkçe (Turkish)",                       "TR",    "latin"),
    "BrazilianPortuguese": LanguageProfile("BrazilianPortuguese", "Português Brasileiro (Brazilian Port.)", "PT",    "latin"),
    "Italian":             LanguageProfile("Italian",             "Italiano (Italian)",                     "IT",    "latin"),
    "LatinSpanish":        LanguageProfile("LatinSpanish",        "Español Latino (Latin Spanish)",         "LATAM", "latin"),
    "ChineseTraditional":  LanguageProfile("ChineseTraditional",  "中文(繁體) (Chinese Traditional)",        "ZHT",   "cjk"),
    "Ukrainian":           LanguageProfile("Ukrainian",           "Українська (Ukrainian)",                 "UA",    "cyrillic"),
    "Japanese":            LanguageProfile("Japanese",            "日本語 (Japanese)",                       "JA",    "japanese"),
}

DEFAULT_PROFILE: LanguageProfile = LANGUAGE_PROFILES["Korean"]


# 번역 프롬프트에 넣을 대상 언어 이름. Gemini가 명확히 알아듣도록 한글명(영문명)을
# 함께 적는다. folder_name이 BrazilianPortuguese처럼 붙어 있어 display_name에서
# 깔끔히 뽑기 어렵기 때문에 별도로 둔다.
_PROMPT_NAMES: Dict[str, str] = {
    "Korean":              "한국어 (Korean)",
    "English":             "영어 (English)",
    "French":              "프랑스어 (French)",
    "German":              "독일어 (German)",
    "Spanish":             "스페인어 (Spanish, Spain)",
    "Polish":              "폴란드어 (Polish)",
    "Russian":             "러시아어 (Russian)",
    "Chinese":             "중국어 간체 (Simplified Chinese)",
    "Turkish":             "튀르키예어 (Turkish)",
    "BrazilianPortuguese": "브라질 포르투갈어 (Brazilian Portuguese)",
    "Italian":             "이탈리아어 (Italian)",
    "LatinSpanish":        "중남미 스페인어 (Latin American Spanish)",
    "ChineseTraditional":  "중국어 번체 (Traditional Chinese)",
    "Ukrainian":           "우크라이나어 (Ukrainian)",
    "Japanese":            "일본어 (Japanese)",
}


def prompt_language_name(profile: LanguageProfile) -> str:
    """번역 지시문에 쓸 대상 언어 이름. 매핑에 없으면 folder_name으로 폴백."""
    return _PROMPT_NAMES.get(profile.folder_name, profile.folder_name)


def script_ratio(text: str, profile: LanguageProfile) -> float:
    """text 안에서 대상 언어 스크립트 문자가 차지하는 비율(0.0~1.0).

    Latin 등 문자 범위로 구분 불가한 스크립트는 항상 0.0을 반환한다(사전 감지 불가).
    공백은 제외하고 계산한다. is_already_translated와 달리 <content> 블록을 요구하지
    않고 임의 문자열에 바로 쓸 수 있다.
    """
    ranges = _SCRIPT_RANGES.get(profile.script_type, [])
    if not ranges:
        return 0.0
    clean = re.sub(r"\s+", "", text)
    if not clean:
        return 0.0
    target = sum(1 for c in clean if any(lo <= c <= hi for lo, hi in ranges))
    return target / len(clean)


def get_profile(folder_name: str) -> LanguageProfile:
    """Get language profile by folder name, or return DEFAULT_PROFILE if not found.

    Args:
        folder_name: BG3 Localization subfolder name (e.g. "Korean", "French")

    Returns:
        LanguageProfile instance, or DEFAULT_PROFILE if not found.
    """
    return LANGUAGE_PROFILES.get(folder_name, DEFAULT_PROFILE)


def is_already_translated(text: str, profile: LanguageProfile) -> bool:
    """Detect if XML content is already translated in the target language.

    For non-Latin scripts (CJK, Cyrillic, Hangul, Japanese), checks if the text
    contains at least 30% characters in the target script. For Latin scripts,
    always returns False (impossible to pre-detect Latin text translation).

    Args:
        text: XML string containing <content> blocks
        profile: LanguageProfile for target language

    Returns:
        True if text appears to be already translated in target script, False otherwise.
    """
    ranges = _SCRIPT_RANGES.get(profile.script_type, [])

    # Latin scripts are never pre-detected
    if not ranges:
        return False

    # Extract content blocks
    blocks = CONTENT_BLOCK_RE.findall(text)
    if not blocks:
        return False

    # Extract inner text from all blocks
    inner_text = ""
    for block in blocks:
        m = re.search(r">([^<]*)</content>", block, re.IGNORECASE)
        if m:
            inner_text += m.group(1)

    # Remove HTML entities and whitespace
    clean = re.sub(r"&[a-zA-Z]+;", "", inner_text)
    clean = re.sub(r"\s+", "", clean)

    # Too short to reliably detect
    if len(clean) < 10:
        return False

    # Count characters matching target script ranges
    target_chars = sum(
        1 for c in clean if any(lo <= c <= hi for lo, hi in ranges)
    )

    # At least 30% of characters should be in target script
    return target_chars / len(clean) >= 0.3
