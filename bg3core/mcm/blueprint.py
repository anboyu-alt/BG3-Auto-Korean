"""MCM_blueprint.json 처리기.

게임은 노드에 Handles가 있으면 Localization XML 측 번역을 우선 사용한다.
따라서 (a) Handles만 있는 노드는 XML 처리만으로 한글화가 자동 적용되고,
(b) 평문 필드만 있는 노드는 블루프린트를 직접 치환해야 한다. 이 처리기는
(b)에 해당하는 평문 필드만 자동 한글화한다.
"""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..logger import CallbackLogger

from .whitelist import (
    BLUEPRINT_TRANSLATABLE_KEYS,
    BLUEPRINT_NEVER_TOUCH_KEYS,
    BLUEPRINT_HANDLE_PROTECTIONS,
)


def find_blueprints(unpacked_root: Path) -> List[Path]:
    return list(unpacked_root.rglob("MCM_blueprint.json"))


def _node_has_handle_for(node: dict, plain_key: str) -> bool:
    """노드의 Handles 객체에 plain_key를 보호하는 *Handle이 정의돼 있는지."""
    handles = node.get("Handles")
    if not isinstance(handles, dict):
        return False
    for handle_key, protected_keys in BLUEPRINT_HANDLE_PROTECTIONS.items():
        if plain_key in protected_keys and handles.get(handle_key):
            return True
    return False


def _collect_strings_recursive(node, plain_texts: List[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in BLUEPRINT_NEVER_TOUCH_KEYS:
                continue
            if isinstance(value, str) and value.strip():
                if key in BLUEPRINT_TRANSLATABLE_KEYS and not _node_has_handle_for(node, key):
                    plain_texts.append(value)
            elif isinstance(value, list):
                if key == "Choices":
                    for item in value:
                        if isinstance(item, str) and item.strip():
                            plain_texts.append(item)
                        else:
                            _collect_strings_recursive(item, plain_texts)
                else:
                    for item in value:
                        _collect_strings_recursive(item, plain_texts)
            elif isinstance(value, dict):
                _collect_strings_recursive(value, plain_texts)
    elif isinstance(node, list):
        for item in node:
            _collect_strings_recursive(item, plain_texts)


def _apply_recursive(node, translation_map: Dict[str, str]) -> int:
    """translation_map에 매핑된 문자열을 in-place로 치환. 치환 횟수 반환."""
    count = 0
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if key in BLUEPRINT_NEVER_TOUCH_KEYS:
                continue
            if isinstance(value, str):
                if (
                    key in BLUEPRINT_TRANSLATABLE_KEYS
                    and not _node_has_handle_for(node, key)
                    and value in translation_map
                ):
                    node[key] = translation_map[value]
                    count += 1
            elif isinstance(value, list):
                if key == "Choices":
                    for i, item in enumerate(value):
                        if isinstance(item, str) and item in translation_map:
                            value[i] = translation_map[item]
                            count += 1
                        else:
                            count += _apply_recursive(item, translation_map)
                else:
                    for item in value:
                        count += _apply_recursive(item, translation_map)
            elif isinstance(value, dict):
                count += _apply_recursive(value, translation_map)
    elif isinstance(node, list):
        for item in node:
            count += _apply_recursive(item, translation_map)
    return count


def _read_indent(text: str) -> str:
    """원본 JSON에서 사용된 들여쓰기 추정 — 첫 ' '<n>의 n을 반환. 못 찾으면 4."""
    for line in text.splitlines():
        stripped = line.lstrip(" ")
        diff = len(line) - len(stripped)
        if diff > 0 and stripped:
            return " " * diff
    return "    "


def process_blueprints(
    unpacked_root: Path,
    translate_fn: Callable[[List[str], str], Dict[str, str]],
    logger: Optional["CallbackLogger"] = None,
) -> dict:
    """언팩된 모드 루트의 모든 MCM_blueprint.json을 처리.

    translate_fn(texts, label) -> {english: korean} 매핑을 받는다.
    """
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)

    blueprints = find_blueprints(unpacked_root)
    if not blueprints:
        return {"blueprints": 0, "translated": 0, "files": []}

    stats = {"blueprints": len(blueprints), "translated": 0, "files": []}
    for bp_path in blueprints:
        try:
            raw = bp_path.read_text(encoding="utf-8")
        except Exception as e:
            _log(f"    [blueprint] 읽기 실패 {bp_path}: {e}")
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            _log(f"    [blueprint] JSON 파싱 실패 {bp_path}: {e}")
            continue

        plain_texts: List[str] = []
        _collect_strings_recursive(data, plain_texts)

        if not plain_texts:
            _log(f"    [blueprint] {bp_path.name}: 직접 치환 대상 없음 (Handles로 처리됨)")
            stats["files"].append({"path": str(bp_path), "translated": 0, "candidates": 0})
            continue

        rel = bp_path.relative_to(unpacked_root) if bp_path.is_relative_to(unpacked_root) else bp_path
        _log(f"    [blueprint] {rel}: 평문 후보 {len(plain_texts)}개")

        translation_map = translate_fn(plain_texts, f"MCM:{bp_path.parent.name}")
        if not translation_map:
            stats["files"].append({"path": str(bp_path), "translated": 0, "candidates": len(plain_texts)})
            continue

        applied = _apply_recursive(data, translation_map)
        indent = _read_indent(raw)
        new_text = json.dumps(data, ensure_ascii=False, indent=indent)
        bp_path.write_text(new_text + ("\n" if raw.endswith("\n") else ""), encoding="utf-8")
        stats["translated"] += applied
        stats["files"].append({"path": str(bp_path), "translated": applied, "candidates": len(plain_texts)})
        _log(f"    [blueprint] {rel}: {applied}개 치환 완료")

    return stats
