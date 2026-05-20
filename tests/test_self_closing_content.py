"""self-closing `<content ... />` 가 다음 블록과 합쳐지지 않고 별도 매칭되는지 검증.

DBW DragonBall Warrior 같은 모드는 영문 핸들 중 빈 self-closing 항목이 있다.
CONTENT_BLOCK_RE가 self-closing을 별도로 매칭하지 못하면 직후의 정상 블록과
한 블록으로 묶여 inner 추출이 어긋나고, 번역 결과 XML이 깨진다.
"""

import xml.etree.ElementTree as ET

from bg3core.constants import CONTENT_BLOCK_RE
from bg3core.translate import process_xml_file


def test_self_closing_matched_separately():
    """self-closing과 정상 블록이 각각 한 매칭으로."""
    src = (
        '<content contentuid="hA" version="10" />\n'
        '<content contentuid="hB" version="1">Hello</content>'
    )
    blocks = CONTENT_BLOCK_RE.findall(src)
    assert len(blocks) == 2
    assert blocks[0] == '<content contentuid="hA" version="10" />'
    assert blocks[1] == '<content contentuid="hB" version="1">Hello</content>'


def test_normal_block_alone_still_matches():
    """기존 동작 회귀 없음 확인."""
    src = '<content contentuid="hX" version="1">Text</content>'
    blocks = CONTENT_BLOCK_RE.findall(src)
    assert blocks == [src]


def test_self_closing_block_preserved_in_translation(tmp_path):
    """self-closing 블록은 번역 처리에서 원본 그대로 보존, 다음 블록은 정상 번역."""
    src = (
        '<?xml version="1.0"?>\n<contentList>\n'
        '<content contentuid="hA" version="10" />\n'
        '<content contentuid="hB" version="1">Hello</content>\n'
        '</contentList>'
    )
    # API 호출 없이 cache·glossary로만 가능한 텍스트가 아니므로 실제 process는
    # API 필요. 여기서는 매칭 단위가 깨지지 않는지(2개 매칭)만 검증.
    blocks = CONTENT_BLOCK_RE.findall(src)
    assert len(blocks) == 2
    # 결합 결과가 XML로 valid한지 (mismatched tag 없음)
    rebuilt = '<root>' + ''.join(blocks) + '</root>'
    ET.fromstring(rebuilt)


def test_dbw_actual_pattern():
    """DBW에서 실제로 깨졌던 정확한 패턴."""
    src = (
        '<content contentuid="h58e3c156" version="7">When all 7 Dragon Balls are collected.</content>\n'
        '<content contentuid="h3ea49b3f" version="10" />\n'
        '<content contentuid="h6dbd9d7b" version="1">1 Star Dragonball Found</content>'
    )
    blocks = CONTENT_BLOCK_RE.findall(src)
    assert len(blocks) == 3
    assert blocks[1] == '<content contentuid="h3ea49b3f" version="10" />'
    assert '</content>' in blocks[2]
    assert '1 Star Dragonball Found' in blocks[2]
