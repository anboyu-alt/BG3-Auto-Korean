"""ScriptExtender/Lua/*.lua 안의 IMGUI 표시 문자열 처리기.

자동 치환 대상은 7가지 위젯 패턴(:AddText, :AddButton, :AddCollapsingHeader,
:AddInputText 라벨/초기값, .Hint, .Text)에서 추출한 평문 인자다. 코드 식별자성
문자열(IMGUI 내부 ID, 네트워크 채널, 색상 슬롯, 파일 확장자)과 비교 분기에
쓰일 가능성이 높은 짧은 단어는 검수 큐로 분리해 사람이 처리한다.

옵션 배열(`xxx.Options = { ... }`)은 클라이언트·서버 간 비교 키로 쓰이는
경우가 많아 자동 치환하지 않고 모두 검수 큐로 보낸다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..logger import CallbackLogger

from .whitelist import (
    LUA_WIDGET_PATTERNS,
    LUA_OPTIONS_RE,
    LUA_OPTION_ITEM_RE,
    LUA_FORMAT_SPECIFIER_RE,
    is_lua_skippable,
    is_lua_short_key,
)


def find_lua_files(unpacked_root: Path) -> List[Path]:
    return [
        p for p in unpacked_root.rglob("*.lua")
        if "ScriptExtender" in p.parts and "Lua" in p.parts
    ]


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _classify(text: str) -> str:
    """AUTO | REVIEW_short_key | REVIEW_skip"""
    if is_lua_skippable(text):
        return "REVIEW_skip"
    if is_lua_short_key(text):
        return "REVIEW_short_key"
    return "AUTO"


def scan_lua(content: str) -> Tuple[List[dict], List[dict], List[dict]]:
    """Lua 소스를 스캔해 (자동 치환 후보, 검수 큐, 옵션 배열) 반환."""
    auto: List[dict] = []
    review: List[dict] = []
    options: List[dict] = []
    seen_spans = set()

    for pattern_name, regex in LUA_WIDGET_PATTERNS:
        for m in regex.finditer(content):
            text = m.group(1)
            if not text.strip():
                continue
            span = (m.start(1), m.end(1))
            if span in seen_spans:
                continue
            seen_spans.add(span)
            entry = {
                "pattern": pattern_name,
                "line": _line_of(content, m.start(1)),
                "start": span[0],
                "end": span[1],
                "text": text,
            }
            kind = _classify(text)
            if kind == "AUTO":
                auto.append(entry)
            else:
                entry["kind"] = kind
                review.append(entry)

    for m in LUA_OPTIONS_RE.finditer(content):
        var_name = m.group(1)
        items_text = m.group(2)
        items = LUA_OPTION_ITEM_RE.findall(items_text)
        options.append({
            "variable": var_name,
            "line": _line_of(content, m.start()),
            "items": items,
        })

    return auto, review, options


def _lua_escape(text: str) -> str:
    """파이썬 str를 Lua 큰따옴표 문자열 리터럴 안전 형식으로 변환."""
    return (
        text.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
    )


def apply_translations(content: str, auto_entries: List[dict], translation_map: Dict[str, str]) -> Tuple[str, int]:
    """auto_entries의 span 위치에 translation_map의 한글을 in-place 치환.

    span(start, end)는 원본 인덱스. 역순으로 적용해야 위치가 안 밀린다.
    """
    sorted_entries = sorted(auto_entries, key=lambda e: e["start"], reverse=True)
    count = 0
    for entry in sorted_entries:
        kor = translation_map.get(entry["text"])
        if not kor:
            continue
        # string.format은 포맷 specifier 보존이 깨지면 게임 크래시 위험 — skip
        if entry.get("pattern") == "StringFormat":
            orig_specs = LUA_FORMAT_SPECIFIER_RE.findall(entry["text"])
            new_specs = LUA_FORMAT_SPECIFIER_RE.findall(kor)
            if orig_specs != new_specs:
                continue
        escaped = _lua_escape(kor)
        content = content[: entry["start"]] + escaped + content[entry["end"]:]
        count += 1
    return content, count


def process_lua_files(
    unpacked_root: Path,
    translate_fn: Callable[[List[str], str], Dict[str, str]],
    review_report_path: Optional[Path] = None,
    logger: Optional["CallbackLogger"] = None,
) -> dict:
    """언팩된 모드 루트의 Lua 파일을 처리."""
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)

    lua_files = find_lua_files(unpacked_root)
    if not lua_files:
        return {"files": 0, "auto": 0, "review": 0, "options": 0, "report": None}

    all_auto: List[dict] = []
    per_file: List[dict] = []
    review_payload: dict = {}

    for lua_path in lua_files:
        try:
            raw = lua_path.read_text(encoding="utf-8")
        except Exception as e:
            _log(f"    [lua] 읽기 실패 {lua_path}: {e}")
            continue

        auto, review, options = scan_lua(raw)
        if not (auto or review or options):
            continue

        rel = str(lua_path.relative_to(unpacked_root)) if lua_path.is_relative_to(unpacked_root) else str(lua_path)
        per_file.append({"path": rel, "auto_count": len(auto), "review_count": len(review), "options_count": len(options)})

        all_auto.extend([{**e, "_file": lua_path, "_original_raw_length": len(raw)} for e in auto])

        if review or options:
            review_payload[rel] = {
                "ambiguous": review,
                "option_arrays": options,
            }

    if not all_auto and not review_payload:
        return {"files": len(lua_files), "auto": 0, "review": 0, "options": 0, "report": None}

    unique_texts = sorted({e["text"] for e in all_auto})
    _log(f"    [lua] 파일 {len(per_file)}개, 자동 후보 {len(unique_texts)}개 고유")

    translation_map: Dict[str, str] = {}
    if unique_texts:
        translation_map = translate_fn(unique_texts, "MCM-Lua")

    auto_by_file: Dict[Path, List[dict]] = {}
    for entry in all_auto:
        auto_by_file.setdefault(entry["_file"], []).append(entry)

    total_applied = 0
    for lua_path, entries in auto_by_file.items():
        raw = lua_path.read_text(encoding="utf-8")
        new_content, applied = apply_translations(raw, entries, translation_map)
        if applied > 0:
            lua_path.write_text(new_content, encoding="utf-8", newline="")
            total_applied += applied

    review_total = sum(len(v["ambiguous"]) for v in review_payload.values())
    options_total = sum(len(v["option_arrays"]) for v in review_payload.values())

    report_written: Optional[str] = None
    if review_report_path and review_payload:
        review_report_path.parent.mkdir(parents=True, exist_ok=True)
        review_report_path.write_text(
            json.dumps(review_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        report_written = str(review_report_path)

    return {
        "files": len(per_file),
        "auto": total_applied,
        "review": review_total,
        "options": options_total,
        "report": report_written,
        "per_file": per_file,
    }
