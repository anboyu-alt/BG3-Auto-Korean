"""번역 결과의 raw `<`/`>` 자동 escape 검증.

Viltrumite/DBW 같은 spell·passive 모드에서 Gemini가 `<내성 굴림>` 같은 자작
placeholder를 raw `<>`로 넣어 XML이 깨지고 divine .loca 변환이 실패하던 케이스.
"""

import xml.etree.ElementTree as ET

from bg3core.translate import escape_unescaped_angle_brackets


def _wrap(text: str) -> str:
    """content 안에 넣어 XML 파싱 가능한지 검증용."""
    return f'<root><content>{text}</content></root>'


def test_passthrough_when_no_angle_brackets():
    assert escape_unescaped_angle_brackets("그냥 한글 텍스트") == "그냥 한글 텍스트"


def test_escapes_bare_placeholder():
    """Gemini가 만들어낸 raw <내성 굴림> 케이스."""
    result = escape_unescaped_angle_brackets("적은 <내성 굴림>을 해야 한다.")
    assert result == "적은 &lt;내성 굴림&gt;을 해야 한다."
    ET.fromstring(_wrap(result))  # XML 파싱 가능해야 함


def test_preserves_existing_lstag_entity():
    """이미 escape된 &lt;LSTag .../&gt;는 건드리지 않는다."""
    src = '&lt;LSTag Tooltip="Immune"&gt;면역&lt;/LSTag&gt;이 된다.'
    result = escape_unescaped_angle_brackets(src)
    assert result == src
    ET.fromstring(_wrap(result))


def test_handles_mixed_escaped_and_raw():
    """원본의 escape entity는 보존, Gemini가 새로 추가한 raw bracket만 escape."""
    src = '&lt;LSTag Type="Image" Info="X"/&gt; 처치 시 <지배 굴림>을 해야 한다.'
    result = escape_unescaped_angle_brackets(src)
    # 원본 LSTag entity 보존
    assert '&lt;LSTag Type="Image" Info="X"/&gt;' in result
    # 자작 placeholder는 entity로 변환
    assert '&lt;지배 굴림&gt;' in result
    # raw `<지배` 또는 `굴림>` 잔존 없음
    assert '<지배' not in result
    assert '굴림>' not in result
    ET.fromstring(_wrap(result))


def test_preserves_numeric_and_named_entities():
    """&amp; &quot; &#39; &#x4eee; 같은 entity도 보존."""
    src = '&amp; &quot;인용&quot; &#39;아포&#39; &#x4eee;'
    result = escape_unescaped_angle_brackets(src)
    assert result == src


def test_viltrumite_l148_style_actual_case():
    """실제 사용자 환경에서 divine 파싱 실패를 일으킨 L148 패턴 시뮬레이션."""
    # 원본 영문: "...allies within 5m must make a saving throw..." 같은 텍스트가
    # Gemini에 의해 D&D 용어 placeholder를 포함한 한글로 번역됨
    src = (
        '인간의 아드레날린이 솟구칩니다. '
        '처치할 때마다 5m 반경 내의 모든 적은 <내성 굴림>을 해야 하며, '
        '실패 시 당신의 의지력에 &lt;LSTag Type="Status" Tooltip="DOMINANCE_FEARED"&gt;'
        '공포&lt;/LSTag&gt;를 느낍니다.'
    )
    result = escape_unescaped_angle_brackets(src)
    # XML 파싱이 성공해야 함 (이전엔 L148 position ~264에서 실패)
    parsed = ET.fromstring(_wrap(result))
    content = parsed.find("content")
    assert content is not None
    # LSTag entity는 그대로 (parse 시 자동 unescape됨)
    assert "DOMINANCE_FEARED" in content.text
    # placeholder도 한글로 살아있음
    assert "내성 굴림" in content.text
