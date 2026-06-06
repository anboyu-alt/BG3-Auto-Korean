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
