"""④ 공식 언어팩 참조 글로서리 — 순수 로직 테스트.

Divine 실행/실제 게임 파일이 필요한 부분은 제외하고, 파싱·조인·조회·캐시키
순수 함수만 검증한다.
"""
import json

import pytest

from bg3core import official_glossary as og


# ── parse_loca_xml: contentuid → 텍스트 ──────────────────────
def test_parse_loca_xml_basic():
    xml = (
        '<contentList>'
        '<content contentuid="h297f1716g1234" version="1">Fireball</content>'
        '<content contentuid="hABCDEF00g0001" version="2">Lightning Bolt</content>'
        '</contentList>'
    )
    result = og.parse_loca_xml(xml)
    assert result == {
        "h297f1716g1234": "Fireball",
        "hABCDEF00g0001": "Lightning Bolt",
    }


def test_parse_loca_xml_unescapes_entities():
    xml = '<content contentuid="h1" version="1">Tasha&apos;s &amp; Bob&quot;s</content>'
    result = og.parse_loca_xml(xml)
    assert result == {"h1": "Tasha's & Bob\"s"}


def test_parse_loca_xml_skips_empty_text():
    xml = (
        '<content contentuid="h1" version="1"></content>'
        '<content contentuid="h2" version="1">Real</content>'
    )
    result = og.parse_loca_xml(xml)
    assert result == {"h2": "Real"}


def test_parse_loca_xml_multiline_text():
    xml = '<content contentuid="h1" version="1">Line one\nLine two</content>'
    result = og.parse_loca_xml(xml)
    assert result == {"h1": "Line one\nLine two"}


# ── build_official_dict: contentuid 조인 ─────────────────────
def test_build_official_dict_joins_on_contentuid():
    english = {"h1": "Fireball", "h2": "Lightning Bolt"}
    target = {"h1": "화염구", "h2": "번개 줄기"}
    result = og.build_official_dict(english, target)
    assert result == {"Fireball": "화염구", "Lightning Bolt": "번개 줄기"}


def test_build_official_dict_skips_handles_missing_in_target():
    english = {"h1": "Fireball", "h2": "Mod-only string"}
    target = {"h1": "화염구"}  # h2 없음
    result = og.build_official_dict(english, target)
    assert result == {"Fireball": "화염구"}


def test_build_official_dict_drops_ambiguous_english():
    # 같은 영어가 서로 다른 번역으로 매핑되면(맥락 의존) 치환 금지 → 제외
    english = {"h1": "Bear", "h2": "Bear"}
    target = {"h1": "곰", "h2": "참다"}
    result = og.build_official_dict(english, target)
    assert "Bear" not in result


def test_build_official_dict_keeps_consistent_duplicate():
    # 같은 영어 → 같은 번역이면 모호하지 않음 → 유지
    english = {"h1": "Fireball", "h2": "Fireball"}
    target = {"h1": "화염구", "h2": "화염구"}
    result = og.build_official_dict(english, target)
    assert result == {"Fireball": "화염구"}


def test_build_official_dict_skips_empty_values():
    english = {"h1": "  ", "h2": "Fireball"}
    target = {"h1": "x", "h2": "화염구"}
    result = og.build_official_dict(english, target)
    assert result == {"Fireball": "화염구"}


# ── lookup_official: 정확 일치 조회 ──────────────────────────
def test_lookup_official_exact():
    d = {"Fireball": "화염구"}
    assert og.lookup_official("Fireball", d) == "화염구"


def test_lookup_official_strips_whitespace():
    d = {"Fireball": "화염구"}
    assert og.lookup_official("  Fireball  ", d) == "화염구"


def test_lookup_official_miss_returns_none():
    d = {"Fireball": "화염구"}
    assert og.lookup_official("Unknown Spell", d) is None


def test_lookup_official_empty_dict():
    assert og.lookup_official("Fireball", {}) is None


# ── build_official_prompt_section: 본문 매칭 용어 주입 ────────
def test_prompt_section_includes_matched_terms_only():
    d = {"Fireball": "화염구", "Lightning Bolt": "번개 줄기", "Haste": "가속"}
    text = "You cast Fireball and then Haste."
    section = og.build_official_prompt_section(text, d)
    assert "Fireball -> 화염구" in section
    assert "Haste -> 가속" in section
    assert "Lightning Bolt" not in section  # 본문에 없음


def test_prompt_section_empty_when_no_match():
    d = {"Fireball": "화염구"}
    section = og.build_official_prompt_section("nothing here", d)
    assert section == ""


def test_prompt_section_empty_dict():
    assert og.build_official_prompt_section("Fireball", {}) == ""


# ── 캐시 키: 소스 pak mtime/size 기반 무효화 ─────────────────
def test_cache_signature_changes_with_mtime(tmp_path):
    p = tmp_path / "English.pak"
    p.write_bytes(b"x" * 10)
    sig1 = og.cache_signature([p])
    # 크기 변경 → 시그니처 변경
    p.write_bytes(b"x" * 20)
    sig2 = og.cache_signature([p])
    assert sig1 != sig2


def test_cache_signature_stable_for_same_files(tmp_path):
    p = tmp_path / "English.pak"
    p.write_bytes(b"x" * 10)
    assert og.cache_signature([p]) == og.cache_signature([p])


def test_cache_signature_order_independent(tmp_path):
    a = tmp_path / "a.pak"
    b = tmp_path / "b.pak"
    a.write_bytes(b"a")
    b.write_bytes(b"bb")
    assert og.cache_signature([a, b]) == og.cache_signature([b, a])


# ── 캐시 로드/저장 라운드트립 ────────────────────────────────
def test_cache_roundtrip(tmp_path):
    cache_path = tmp_path / "official_ko.json"
    data = {"Fireball": "화염구", "Haste": "가속"}
    og.save_cache(cache_path, "sig-123", data)
    loaded = og.load_cache(cache_path, "sig-123")
    assert loaded == data


def test_cache_load_returns_none_on_signature_mismatch(tmp_path):
    cache_path = tmp_path / "official_ko.json"
    og.save_cache(cache_path, "sig-123", {"Fireball": "화염구"})
    assert og.load_cache(cache_path, "different-sig") is None


def test_cache_load_returns_none_when_missing(tmp_path):
    assert og.load_cache(tmp_path / "nope.json", "sig") is None


# ── find_language_paks: 설치 폴더에서 공식 팩 위치 ───────────
def _make_loc(tmp_path):
    loc = tmp_path / "Data" / "Localization"
    loc.mkdir(parents=True)
    return loc


def test_find_language_paks_standard_layout(tmp_path):
    loc = _make_loc(tmp_path)
    (loc / "English.pak").write_bytes(b"e")
    (loc / "Korean").mkdir()
    (loc / "Korean" / "Korean.pak").write_bytes(b"k")
    (loc / "Korean" / "KoreanData.pak").write_bytes(b"kd")
    english, target = og.find_language_paks(str(tmp_path), "Korean")
    assert [p.name for p in english] == ["English.pak"]
    assert sorted(p.name for p in target) == ["Korean.pak", "KoreanData.pak"]


def test_find_language_paks_english_in_subfolder(tmp_path):
    loc = _make_loc(tmp_path)
    (loc / "English").mkdir()
    (loc / "English" / "English.pak").write_bytes(b"e")
    (loc / "Korean").mkdir()
    (loc / "Korean" / "Korean.pak").write_bytes(b"k")
    english, target = og.find_language_paks(str(tmp_path), "Korean")
    assert [p.name for p in english] == ["English.pak"]
    assert [p.name for p in target] == ["Korean.pak"]


def test_find_language_paks_missing_localization(tmp_path):
    english, target = og.find_language_paks(str(tmp_path), "Korean")
    assert english == []
    assert target == []


def test_find_language_paks_no_target_pak(tmp_path):
    loc = _make_loc(tmp_path)
    (loc / "English.pak").write_bytes(b"e")
    english, target = og.find_language_paks(str(tmp_path), "French")
    assert [p.name for p in english] == ["English.pak"]
    assert target == []


def test_find_language_paks_empty_install_path():
    english, target = og.find_language_paks("", "Korean")
    assert english == []
    assert target == []


# ── translate 통합: 공식 사전 정확 일치 시 API 없이 번역 ──────
def test_process_xml_official_exact_match_skips_api(tmp_path):
    from bg3core.translate import process_xml_file
    from bg3core.language import get_profile

    fr = get_profile("French")
    # 글로서리에 없는 가상 고유명사 → 공식 사전 경로만 검증. api_key=""이므로
    # API로 새면 번역되지 않는다(원문 유지). 공식 사전이 잡아야 번역됨.
    content = '<content contentuid="h1" version="1">Zorblax the Unmaker</content>'
    official = {"Zorblax the Unmaker": "Zorblax le Defaiseur"}
    out = process_xml_file(
        content, "t.xml", "", str(tmp_path / "log.txt"),
        official=official, target_profile=fr,
    )
    assert "Zorblax le Defaiseur" in out


def test_process_xml_no_official_is_noop(tmp_path):
    # official=None이면 기존 동작과 동일(공식 사전 분기 미적용).
    from bg3core.translate import process_xml_file
    from bg3core.language import get_profile

    fr = get_profile("French")
    content = '<content contentuid="h1" version="1">Zorblax the Unmaker</content>'
    out = process_xml_file(
        content, "t.xml", "", str(tmp_path / "log.txt"),
        official=None, target_profile=fr,
    )
    # API 미연결 → 번역 실패 → 원문 보존
    assert "Zorblax the Unmaker" in out
