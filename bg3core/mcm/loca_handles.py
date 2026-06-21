"""MCM 의존 모드의 비표준 Localization XML 처리기.

Tooltip Manager 같은 일부 MCM 모드는 Localization/English/ 같은 언어
서브폴더 없이 Localization/ 바로 아래에 *.xml을 둔다. 기존
translate_unpacked_mod()는 언어 서브폴더 기반이라 이런 평면 구조를
스킵한다. 이 처리기는 평면 구조에 대해 in-place로 한글 번역을 적용한다.

언어 서브폴더가 있는 모드는 기존 파이프라인에 맡기고 여기서는 건드리지
않는다.
"""

from __future__ import annotations

import shutil
import threading
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..logger import CallbackLogger

from ..translate import process_xml_file
from ..language import LanguageProfile, DEFAULT_PROFILE, script_ratio


def _has_language_subdirs(loc_dir: Path, target_folder: str = "Korean") -> bool:
    """Localization 폴더가 언어 서브폴더 구조인지 — target_folder 제외하고 디렉토리 1개 이상."""
    if not loc_dir.is_dir():
        return False
    for child in loc_dir.iterdir():
        if child.is_dir() and child.name.lower() != target_folder.lower():
            return True
    return False


def find_flat_loca_xmls(unpacked_root: Path, target_folder: str = "Korean") -> List[Path]:
    """언어 서브폴더 없는 Localization/*.xml 목록."""
    results: List[Path] = []
    for loc_dir in unpacked_root.rglob("Localization"):
        if not loc_dir.is_dir():
            continue
        if _has_language_subdirs(loc_dir, target_folder):
            continue
        for xml_file in loc_dir.iterdir():
            if xml_file.is_file() and xml_file.suffix.lower() == ".xml":
                # .loca.xml 형식도 같은 XML이므로 포함
                results.append(xml_file)
    return results


def _looks_translated(text: str, profile: LanguageProfile = DEFAULT_PROFILE) -> bool:
    """대상 언어 스크립트 비율이 충분히 높으면 이미 번역된 파일.

    Latin 등 감지 불가 스크립트(영어·프랑스어 등 대상)는 항상 False다.
    """
    import re
    cleaned = re.sub(r"<[^>]+>", "", text)
    if len(re.sub(r"\s+", "", cleaned)) < 10:
        return False
    return script_ratio(cleaned, profile) >= 0.3


def mirror_loca_to_source_languages(
    unpacked_root: Path,
    target_folder: str = "Korean",
    logger: Optional["CallbackLogger"] = None,
) -> int:
    """{target_folder}의 .loca 바이너리를 같은 Localization의 다른 언어 폴더에
    동명 .loca로 복사한다. **`.xml`(원문)은 절대 건드리지 않는다.**

    BG3MCM 등 일부 모드는 게임 언어 설정과 무관하게 영어 Localization에서 핸들을
    조회한다. 그런 모드도 번역이 표시되게 하려면 번역 텍스트가 영어 폴더의
    .loca에도 들어가야 한다. 번역은 핸들(contentuid)은 그대로 두고 텍스트만
    바꾸므로, target_folder의 .loca를 그대로 복사하면 동일 핸들에 번역 텍스트가
    들어간다. 영어 .xml 원문은 보존되어 검수·원문 유지가 가능하다.

    반드시 ensure_loca()로 .loca가 생성된 뒤 호출해야 한다. 동명 .loca가 없는
    폴더는 건드리지 않는다.
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
        target_dir = loc_dir / target_folder
        if not target_dir.is_dir():
            continue
        # target_folder의 .loca를 prefix별로 매핑. 예: 'english.loca' → prefix='english'
        prefix_to_loca: dict = {}
        for tf in target_dir.iterdir():
            if tf.is_file() and tf.suffix.lower() == ".loca":
                p = tf.name.split(".", 1)[0].lower()
                prefix_to_loca.setdefault(p, tf)
        if not prefix_to_loca:
            continue

        for lang_dir in loc_dir.iterdir():
            if not lang_dir.is_dir() or lang_dir.name.lower() == target_folder.lower():
                continue
            for dst in lang_dir.iterdir():
                if not dst.is_file() or dst.suffix.lower() != ".loca":
                    continue
                dst_prefix = dst.name.split(".", 1)[0].lower()
                src = prefix_to_loca.get(dst_prefix)
                if src is not None:
                    shutil.copyfile(src, dst)
                    mirrored += 1
                    _log(f"    [loca-mirror] {lang_dir.name}/{dst.name} ← {target_folder}/{src.name} (.loca only, .xml preserved)")
    return mirrored


def process_flat_localizations(
    unpacked_root: Path,
    api_key: str,
    log_file: str,
    cancel_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    logger: Optional["CallbackLogger"] = None,
    target_profile: LanguageProfile = DEFAULT_PROFILE,
) -> dict:
    """언팩된 모드 안의 평면 Localization XML들을 in-place로 대상 언어로 번역."""
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)

    xmls = find_flat_loca_xmls(unpacked_root, target_profile.folder_name)
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
        if _looks_translated(original, target_profile):
            _log(f"    [loca] {xml_file.name}: already translated, skipping")
            continue

        translated = process_xml_file(
            original, xml_file.name, api_key, log_file,
            cancel_event=cancel_event,
            pause_event=pause_event,
            logger=logger,
            target_profile=target_profile,
        )
        if translated != original:
            xml_file.write_text(translated, encoding="utf-8")
            translated_files += 1
            _log(f"    [loca] {xml_file.name}: translated in-place")

    return {"files": len(xmls), "translated": translated_files}
