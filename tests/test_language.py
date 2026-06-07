"""Language profile management and multi-language support for v5.0."""

from bg3core.language import (
    LANGUAGE_PROFILES, DEFAULT_PROFILE, get_profile, is_already_translated,
)


def test_all_15_profiles_exist():
    """Verify all 15 BG3 supported languages are defined."""
    expected = {
        "Korean", "English", "French", "German", "Spanish", "Polish", "Russian",
        "Chinese", "Turkish", "BrazilianPortuguese", "Italian", "LatinSpanish",
        "ChineseTraditional", "Ukrainian", "Japanese",
    }
    assert set(LANGUAGE_PROFILES.keys()) == expected


def test_default_is_korean():
    """DEFAULT_PROFILE must be Korean."""
    assert DEFAULT_PROFILE.folder_name == "Korean"
    assert DEFAULT_PROFILE.lang_code == "KR"


def test_get_profile_unknown_returns_default():
    """get_profile() returns DEFAULT_PROFILE for unknown folder name."""
    assert get_profile("DoesNotExist") == DEFAULT_PROFILE


def test_is_already_translated_korean():
    """Korean text should be detected as already translated."""
    xml = '<content contentuid="a">가나다라마바사아자차카타파하</content>'
    assert is_already_translated(xml, LANGUAGE_PROFILES["Korean"]) is True


def test_is_already_translated_latin_always_false():
    """Latin scripts (French, Spanish, etc.) always return False (never pre-translated)."""
    xml = '<content contentuid="a">Bonjour le monde bienvenue ici tout</content>'
    assert is_already_translated(xml, LANGUAGE_PROFILES["French"]) is False


def test_is_already_translated_russian():
    """Russian (Cyrillic) text should be detected as already translated."""
    xml = '<content contentuid="a">Привет мир добро пожаловать здесь</content>'
    assert is_already_translated(xml, LANGUAGE_PROFILES["Russian"]) is True


def test_is_already_translated_chinese():
    """Chinese (CJK) text should be detected as already translated."""
    xml = '<content contentuid="a">你好世界欢迎来到这里吗</content>'
    assert is_already_translated(xml, LANGUAGE_PROFILES["Chinese"]) is True


def test_is_already_translated_japanese():
    """Japanese (hiragana/katakana) text should be detected as already translated."""
    xml = '<content contentuid="a">こんにちは世界へようこそここに</content>'
    assert is_already_translated(xml, LANGUAGE_PROFILES["Japanese"]) is True


def test_is_already_translated_short_text_returns_false():
    """Text shorter than 10 characters should return False (too short to reliably detect)."""
    xml = '<content contentuid="a">가나</content>'
    assert is_already_translated(xml, LANGUAGE_PROFILES["Korean"]) is False
