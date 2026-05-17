"""MCM 의존 모드 처리 패키지.

`process_mcm_for_mod`이 단일 진입점. 언팩된 모드 루트를 받아
MCM_blueprint.json과 ScriptExtender/Lua/*.lua를 처리한 뒤
통계 dict를 반환한다. MCM 관련 파일이 없으면 즉시 None을 반환한다.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..logger import CallbackLogger

from ..translate import translate_text_list
from .blueprint import find_blueprints, process_blueprints
from .lua_handler import find_lua_files, process_lua_files
from .loca_handles import (
    find_flat_loca_xmls,
    process_flat_localizations,
    mirror_korean_to_source_languages,
)


def has_mcm_artifacts(unpacked_root: Path) -> bool:
    if find_blueprints(unpacked_root):
        return True
    if find_lua_files(unpacked_root):
        return True
    if find_flat_loca_xmls(unpacked_root):
        return True
    return False


def process_mcm_for_mod(
    unpacked_root: Path,
    api_key: str,
    log_file: str,
    review_report_path: Optional[Path] = None,
    cancel_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    logger: Optional["CallbackLogger"] = None,
) -> Optional[dict]:
    """MCM 자산이 없으면 None, 있으면 처리 통계 dict 반환."""
    if not has_mcm_artifacts(unpacked_root):
        return None

    def translate_fn(texts: List[str], label: str) -> Dict[str, str]:
        if not texts:
            return {}
        return translate_text_list(
            texts, label, api_key, log_file,
            cancel_event=cancel_event,
            pause_event=pause_event,
            logger=logger,
        )

    loca_stats = process_flat_localizations(
        unpacked_root, api_key, log_file,
        cancel_event=cancel_event,
        pause_event=pause_event,
        logger=logger,
    )
    mirrored = mirror_korean_to_source_languages(unpacked_root, logger=logger)
    bp_stats = process_blueprints(unpacked_root, translate_fn, logger=logger)
    lua_stats = process_lua_files(
        unpacked_root, translate_fn,
        review_report_path=review_report_path,
        logger=logger,
    )

    return {
        "loca_files": loca_stats.get("files", 0),
        "loca_translated": loca_stats.get("translated", 0),
        "loca_mirrored": mirrored,
        "blueprints": bp_stats.get("blueprints", 0),
        "blueprint_translated": bp_stats.get("translated", 0),
        "lua_files": lua_stats.get("files", 0),
        "lua_auto": lua_stats.get("auto", 0),
        "lua_review": lua_stats.get("review", 0),
        "lua_options": lua_stats.get("options", 0),
        "report": lua_stats.get("report"),
    }
