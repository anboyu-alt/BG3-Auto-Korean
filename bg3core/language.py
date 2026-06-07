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
