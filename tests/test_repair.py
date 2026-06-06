from bg3core.repair import (
    RepairResult, parse_content_blocks, base_stem, has_korean_localization,
)


def test_parse_content_blocks_basic():
    text = ('<content contentuid="h1" version="1">A</content>'
            '<content contentuid="h2">B</content>')
    blocks = parse_content_blocks(text)
    assert set(blocks) == {"h1", "h2"}
    assert blocks["h1"] == '<content contentuid="h1" version="1">A</content>'


def test_parse_content_blocks_self_closing():
    text = '<content contentuid="h3" version="1"/>'
    blocks = parse_content_blocks(text)
    assert "h3" in blocks


def test_base_stem_variants():
    assert base_stem("Foo.xml") == "Foo"
    assert base_stem("english.loca.xml") == "english"
    assert base_stem("english.loca") == "english"
    assert base_stem("Bar") == "Bar"


def test_has_korean_localization_true():
    entries = ["Mods/Foo/Localization/English/Foo.xml",
               "Mods/Foo/Localization/Korean/Foo.xml"]
    assert has_korean_localization(entries) is True


def test_has_korean_localization_backslash():
    assert has_korean_localization(["Mods\\Foo\\Localization\\Korean\\Foo.loca"]) is True


def test_has_korean_localization_false():
    entries = ["Mods/Foo/Localization/English/Foo.xml", "Public/Foo/Stats/x.txt"]
    assert has_korean_localization(entries) is False


def test_repair_result_defaults():
    r = RepairResult("x", False, 0, 0)
    assert r.unfixable == []


import xml.etree.ElementTree as ET
from bg3core.repair import repair_xml_text

VALID = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
         '<content contentuid="h1" version="1">안녕</content>\n</contentList>\n')


def _assert_valid_xml(text):
    ET.fromstring(text.encode("utf-8"))  # raises if invalid


def test_clean_korean_unchanged():
    r = repair_xml_text(VALID, None)
    assert r.changed is False
    assert r.reescaped == 0


def test_raw_angle_brackets_fixed():
    broken = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
              '<content contentuid="h1" version="1">2d6 <화염> 피해</content>\n'
              '</contentList>\n')
    r = repair_xml_text(broken, None)
    assert r.changed is True
    assert r.reescaped == 1
    assert "&lt;화염&gt;" in r.new_text
    _assert_valid_xml(r.new_text)


def test_raw_ampersand_fixed():
    broken = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
              '<content contentuid="h1" version="1">[3] & [4]</content>\n'
              '</contentList>\n')
    r = repair_xml_text(broken, None)
    assert "&amp;" in r.new_text
    assert r.changed is True
    _assert_valid_xml(r.new_text)


def test_valid_entities_and_lstag_preserved():
    text = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
            '<content contentuid="h1" version="1">'
            '&lt;LSTag Tooltip="x"&gt;효과&lt;/LSTag&gt; &amp; 끝</content>\n'
            '</contentList>\n')
    r = repair_xml_text(text, None)
    assert r.changed is False
    assert "&lt;LSTag" in r.new_text and "&amp;" in r.new_text


def test_idempotent():
    broken = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
              '<content contentuid="h1" version="1">a <b> c</content>\n'
              '</contentList>\n')
    r1 = repair_xml_text(broken, None)
    r2 = repair_xml_text(r1.new_text, None)
    assert r1.changed is True
    assert r2.changed is False


def test_unparseable_reported_not_written():
    broken = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
              '<content contentuid="h1" version="1">ok</content>\n'
              '<content >dangling')  # 닫힘 태그/루트 닫힘 없음
    r = repair_xml_text(broken, None)
    assert r.changed is False
    assert r.new_text == broken
    assert any("parse" in reason for _, reason in r.unfixable)
