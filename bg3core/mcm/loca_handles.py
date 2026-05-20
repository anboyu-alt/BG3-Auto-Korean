"""MCM 의존 모드의 비표준 Localization XML 처리기.

Tooltip Manager 같은 일부 MCM 모드는 Localization/English/ 같은 언어
서브폴더 없이 Localization/ 바로 아래에 *.xml을 둔다. 기존
translate_unpacked_mod()는 언어 서브폴더 기반이라 이런 평면 구조를
스킵한다. 이 처리기는 평면 구조에 대해 in-place로 한글 번역을 적용한다.

언어 서브폴더가 있는 모드는 기존 파이프라인에 맡기고 여기서는 건드리지
않는다.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..logger import CallbackLogger

from ..translate import process_xml_file


def _has_language_subdirs(loc_dir: Path) -> bool:
    """Localization 폴더가 언어 서브폴더 구조인지 — Korean 제외하고 디렉토리 1개 이상."""
    if not loc_dir.is_dir():
        return False
    for child in loc_dir.iterdir():
        if child.is_dir() and child.name.lower() != "korean":
            return True
    return False


def find_flat_loca_xmls(unpacked_root: Path) -> List[Path]:
    """언어 서브폴더 없는 Localization/*.xml 목록."""
    results: List[Path] = []
    for loc_dir in unpacked_root.rglob("Localization"):
        if not loc_dir.is_dir():
            continue
        if _has_language_subdirs(loc_dir):
            continue
        for xml_file in loc_dir.iterdir():
            if xml_file.is_file() and xml_file.suffix.lower() == ".xml":
                # .loca.xml 형식도 같은 XML이므로 포함
                results.append(xml_file)
    return results


def _looks_translated(text: str) -> bool:
    """한글 비율이 충분히 높으면 이미 번역된 파일."""
    import re
    cleaned = re.sub(r"<[^>]+>", "", text)
    cleaned = re.sub(r"\s+", "", cleaned)
    if len(cleaned) < 10:
        return False
    korean_chars = sum(1 for c in cleaned if "가" <= c <= "힣" or "ㄱ" <= c <= "ㆎ")
    return korean_chars / len(cleaned) >= 0.3


def mirror_korean_to_source_languages(
    unpacked_root: Path,
    logger: Optional["CallbackLogger"] = None,
) -> int:
    """Korean/*.xml을 같은 Localization의 다른 언어 폴더에 동명 파일로 덮어쓰기.

    BG3MCM은 게임 언어 설정과 무관하게 모드의 영어 Localization XML에서 핸들을
    조회하는 경우가 있어, Korean 폴더를 만들기만 해서는 게임에 한글이 표시되지
    않는다. 동명 파일이 있는 다른 언어 폴더에 한글본을 덮어써서 강제로 한글을
    표시하게 한다. 동명 파일이 없는 폴더는 건드리지 않는다.
    """
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)

    mirrored = 0
    for loc_dir in unpacked_root.rglob("Localization"):
        if not loc_dir.is_dir():
            continue
        korean_dir = loc_dir / "Korean"
        if not korean_dir.is_dir():
            continue
        korean_xmls = [x for x in korean_dir.iterdir() if x.is_file() and x.suffix.lower() == ".xml"]
        if not korean_xmls:
            continue
        # Korean의 한글 XML을 베이스 prefix별로 매핑.
        # 예: 'english.xml' → prefix='english', 'english.loca.xml' → prefix='english'
        # (둘 다 같은 prefix이므로 한 내용으로 통일됨)
        prefix_to_content: dict = {}
        for kx in korean_xmls:
            p = kx.name.split(".", 1)[0].lower()
            prefix_to_content.setdefault(p, kx.read_text(encoding="utf-8"))

        for lang_dir in loc_dir.iterdir():
            if not lang_dir.is_dir() or lang_dir.name.lower() == "korean":
                continue
            for dst in lang_dir.iterdir():
                if not dst.is_file():
                    continue
                if dst.suffix.lower() != ".xml":
                    continue
                dst_prefix = dst.name.split(".", 1)[0].lower()
                if dst_prefix in prefix_to_content:
                    dst.write_text(prefix_to_content[dst_prefix], encoding="utf-8")
                    mirrored += 1
                    _log(f"    [loca-mirror] {lang_dir.name}/{dst.name} ← Korean (prefix={dst_prefix})")
    return mirrored


def process_flat_localizations(
    unpacked_root: Path,
    api_key: str,
    log_file: str,
    cancel_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    logger: Optional["CallbackLogger"] = None,
) -> dict:
    """언팩된 모드 안의 평면 Localization XML들을 in-place로 한글화."""
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)

    xmls = find_flat_loca_xmls(unpacked_root)
    if not xmls:
        return {"files": 0, "translated": 0}

    translated_files = 0
    for xml_file in xmls:
        if cancel_event and cancel_event.is_set():
            raise InterruptedError("user_cancelled")

        try:
            original = xml_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            original = xml_file.read_text(encoding="utf-8", errors="replace")

        if not original.strip():
            continue
        if _looks_translated(original):
            _log(f"    [loca] {xml_file.name}: 이미 한글화됨, 스킵")
            continue

        translated = process_xml_file(
            original, xml_file.name, api_key, log_file,
            cancel_event=cancel_event,
            pause_event=pause_event,
            logger=logger,
        )
        if translated != original:
            xml_file.write_text(translated, encoding="utf-8")
            translated_files += 1
            _log(f"    [loca] {xml_file.name}: in-place 한글화 완료")

    return {"files": len(xmls), "translated": translated_files}
