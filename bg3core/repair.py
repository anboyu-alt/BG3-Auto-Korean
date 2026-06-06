import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .constants import CONTENT_BLOCK_RE, CONTENT_INNER_RE, CONTENTUID_RE
from .translate import escape_unescaped_angle_brackets


@dataclass
class RepairResult:
    new_text: str
    changed: bool
    reescaped: int
    backfilled: int
    unfixable: List[Tuple[str, str]] = field(default_factory=list)


def parse_content_blocks(text: str) -> Dict[str, str]:
    """{contentuid: 전체 <content> 블록} 매핑. contentuid 없는 블록은 무시."""
    blocks: Dict[str, str] = {}
    for block in CONTENT_BLOCK_RE.findall(text):
        m = CONTENTUID_RE.search(block)
        if m:
            blocks[m.group(1)] = block
    return blocks


def base_stem(name: str) -> str:
    """파일명에서 .xml / .loca.xml / .loca 확장자를 제거한 베이스 스템."""
    low = name.lower()
    if low.endswith(".loca.xml"):
        return name[: -len(".loca.xml")]
    if low.endswith(".xml"):
        return name[: -len(".xml")]
    if low.endswith(".loca"):
        return name[: -len(".loca")]
    return name


def has_korean_localization(entries: List[str]) -> bool:
    """list-package 엔트리 목록에 Localization/.../Korean 경로가 있으면 True."""
    for e in entries:
        el = e.lower().replace("\\", "/")
        if "localization/" in el and "/korean/" in el:
            return True
    return False


def _reescape_inner(text: str) -> Tuple[str, int]:
    """각 <content>의 inner에만 escape_unescaped_angle_brackets 적용. (open/close/uid 보존)"""
    count = 0

    def repl(m: "re.Match") -> str:
        nonlocal count
        open_tag, inner, close = m.group(1), m.group(2), m.group(3)
        fixed = escape_unescaped_angle_brackets(inner)
        if fixed != inner:
            count += 1
        return open_tag + fixed + close

    return CONTENT_INNER_RE.sub(repl, text), count


# 안전한 XML 파서: 가능하면 defusedxml(외부 엔티티·billion-laughs 차단), 없으면 stdlib 폴백.
try:
    from defusedxml.ElementTree import fromstring as _xml_fromstring
except ImportError:  # defusedxml 미설치 시 stdlib 폴백
    from xml.etree.ElementTree import fromstring as _xml_fromstring


def _is_valid_xml(text: str) -> bool:
    # 검증 전용 프로브: 파싱 실패·위험 엔티티 등 어떤 예외든 '무효'로 보고 원본을 보존,
    # 상위에서 unfixable로 기록한다(에러 은폐가 아니라 의도된 분기).
    try:
        _xml_fromstring(text.encode("utf-8"))  # bytes → XML 선언 인코딩 문제 회피
        return True
    except Exception:
        return False


def repair_xml_text(korean_text: str, english_text: Optional[str]) -> RepairResult:
    """깨진 Korean loca XML을 오프라인 수리한다.

    1) 각 <content> inner 재escape (원인 1 복구)
    2) XML 파싱 검증 — 실패하면 원본 유지 + unfixable
    3) (english_text 있으면) 누락 핸들을 English 블록으로 backfill — Task 3
    """
    reescaped_text, reescaped = _reescape_inner(korean_text)

    if not _is_valid_xml(reescaped_text):
        return RepairResult(korean_text, False, 0, 0,
                            [("<file>", "xml_parse_failed_after_reescape")])

    new_text = reescaped_text
    changed = new_text != korean_text
    return RepairResult(new_text, changed, reescaped, 0, [])
