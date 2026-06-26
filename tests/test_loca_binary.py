"""bg3core.loca — `.loca` 바이너리 ↔ XML 변환 단위 테스트 (Divine 비의존)."""
import pytest

from bg3core import loca
from bg3core.loca import LocalizedText


def _sample():
    return [
        LocalizedText("h1234567890abcdef", 1, "Hello world"),
        LocalizedText("hLSTag", 2, 'A <LSTag Tooltip="Strength">Force</LSTag> check & more'),
        LocalizedText("hKorean", 3, "화염구를 시전합니다"),
        LocalizedText("hEmpty", 1, ""),
        LocalizedText("hAngles", 1, "a < b > c & d"),
    ]


def test_binary_roundtrip_preserves_all_fields():
    ents = _sample()
    back = loca.read_loca(loca.write_loca(ents))
    assert [(e.key, e.version, e.text) for e in back] == [
        (e.key, e.version, e.text) for e in ents
    ]


def test_signature_and_offsets():
    data = loca.write_loca(_sample())
    assert data[:4] == b"LOCA"
    sig, num, texts_off = loca._HEADER.unpack_from(data, 0)
    assert sig == loca.LOCA_SIGNATURE
    assert num == 5
    assert texts_off == loca.HEADER_SIZE + loca.ENTRY_SIZE * 5


def test_length_includes_null_terminator():
    data = loca.write_loca([LocalizedText("h", 1, "abc")])
    _key, _ver, length = loca._ENTRY.unpack_from(data, loca.HEADER_SIZE)
    assert length == 4  # 3 bytes + null


def test_bad_signature_raises():
    with pytest.raises(ValueError):
        loca.read_loca(b"XXXX" + b"\x00" * 8)


def test_too_small_raises():
    with pytest.raises(ValueError):
        loca.read_loca(b"LO")


def test_xml_escapes_angle_brackets_and_amp():
    xml = loca.to_xml(_sample())
    assert "&lt;LSTag" in xml and "&gt;" in xml
    assert "check &amp; more" in xml
    assert "<contentList>" in xml and 'contentuid="hLSTag"' in xml


def test_xml_roundtrip_unescapes():
    ents = _sample()
    back = loca.from_xml(loca.to_xml(ents))
    assert [(e.key, e.version, e.text) for e in back] == [
        (e.key, e.version, e.text) for e in ents
    ]


def test_from_xml_defaults_version_to_1_when_absent():
    xml = '<contentList><content contentuid="hX">hi</content></contentList>'
    assert loca.from_xml(xml) == [LocalizedText("hX", 1, "hi")]


def test_from_xml_handles_self_closing_empty():
    xml = '<contentList><content contentuid="hX" version="2"/></contentList>'
    assert loca.from_xml(xml) == [LocalizedText("hX", 2, "")]


def test_loca_text_stores_raw_lstag_xml_stores_escaped():
    ents = [LocalizedText("h", 1, "<LSTag>x</LSTag>")]
    assert b"<LSTag>x</LSTag>" in loca.write_loca(ents)  # raw in binary
    assert "&lt;LSTag&gt;x&lt;/LSTag&gt;" in loca.to_xml(ents)  # escaped in xml


def test_multibyte_length_counts_bytes_not_chars():
    # '화' = 3 UTF-8 bytes; Length must be byte count + 1.
    data = loca.write_loca([LocalizedText("h", 1, "화")])
    _k, _v, length = loca._ENTRY.unpack_from(data, loca.HEADER_SIZE)
    assert length == 4
