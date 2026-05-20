import re
import shutil
import threading
import time
from pathlib import Path
from typing import List, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .logger import CallbackLogger

from .constants import CONTENT_BLOCK_RE, INPUT_GLOB
from .divine import check_divine_exe, divine_extract, convert_loca_to_xml, strip_loca_artifacts, divine_repack
from .translate import (
    process_xml_file, load_translation_cache, save_translation_cache,
)
from .mcm import process_mcm_for_mod


def find_localization_folders(root_path: Path) -> List[Path]:
    return list(root_path.rglob("Localization"))


def has_korean_folder(loc_path: Path) -> bool:
    return (loc_path / "Korean").exists()


def list_source_language_dirs(loc_path: Path) -> List[Path]:
    if not loc_path.exists():
        return []
    src_dirs = [p for p in loc_path.iterdir() if p.is_dir() and p.name.lower() != "korean"]
    src_dirs.sort(key=lambda x: (0 if x.name.lower() == "english" else 1, x.name.lower()))
    return src_dirs


def is_already_korean(text: str) -> bool:
    blocks = CONTENT_BLOCK_RE.findall(text)
    if not blocks:
        return False
    inner_text = ""
    for block in blocks:
        m = re.search(r">([^<]*)</content>", block, re.IGNORECASE)
        if m:
            inner_text += m.group(1)
    clean = re.sub(r"&[a-zA-Z]+;", "", inner_text)
    clean = re.sub(r"\s+", "", clean)
    if len(clean) < 10:
        return False
    korean_chars = sum(1 for c in clean if '가' <= c <= '힣' or 'ㄱ' <= c <= 'ㆎ')
    return korean_chars / len(clean) >= 0.3


def translate_unpacked_mod(
    unpacked_path: Path,
    api_key: str,
    log_file: str,
    skip_if_korean_exists: bool = True,
    cancel_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    on_progress: Optional[Callable] = None,
    logger: Optional["CallbackLogger"] = None,
) -> bool:
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)
    loc_folders = find_localization_folders(unpacked_path)
    if not loc_folders:
        return False

    any_translated = False

    for loc_path in loc_folders:
        if cancel_event and cancel_event.is_set():
            raise InterruptedError("user_cancelled")
        while pause_event and pause_event.is_set():
            time.sleep(0.2)
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("user_cancelled")

        _log(f"    📂 Localization: {loc_path.relative_to(unpacked_path)}")

        if skip_if_korean_exists and has_korean_folder(loc_path):
            _log("       Korean 폴더가 이미 존재함. 스킵")
            continue

        src_dirs = list_source_language_dirs(loc_path)
        if not src_dirs:
            _log("       하위 언어 폴더를 찾지 못함. 스킵")
            continue

        korean_path = loc_path / "Korean"
        korean_path.mkdir(parents=True, exist_ok=True)

        src_dir = src_dirs[0]
        if len(src_dirs) > 1:
            _log(f"       언어 폴더 {len(src_dirs)}개. '{src_dir.name}'을 소스로 사용")

        xml_files = list(src_dir.glob(INPUT_GLOB))
        if not xml_files:
            for fallback_glob in ["*.loca.xml", "*.lsx", "*.loca"]:
                xml_files = list(src_dir.glob(fallback_glob))
                if xml_files:
                    break
        if not xml_files:
            all_files = list(src_dir.iterdir())
            if all_files:
                names = [f.name for f in all_files[:10]]
                _log(f"       ⚠️ {src_dir.name} 폴더에 XML 파일 없음. 발견된 파일: {names}")
            else:
                _log(f"       ⚠️ {src_dir.name} 폴더가 비어있음")
            continue

        _log(f"       원본 폴더: {src_dir.name} (XML {len(xml_files)}개)")

        total_files = len(xml_files)
        for file_idx, xml_file in enumerate(xml_files, start=1):
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("user_cancelled")
            _log(f"       ▶ 파일 처리: {xml_file.name}")
            if on_progress:
                on_progress("translate", file_idx, total_files, xml_file.name)

            try:
                original = xml_file.read_text(encoding="utf-8", errors="strict")
            except UnicodeDecodeError:
                original = xml_file.read_text(encoding="utf-8", errors="replace")

            if not original.strip():
                _log("         빈 파일. 스킵")
                continue

            if is_already_korean(original):
                _log("         이미 한글화된 파일. 스킵")
                continue

            translated = process_xml_file(
                original, xml_file.name, api_key, log_file,
                cancel_event=cancel_event,
                pause_event=pause_event,
                logger=logger,
            )

            out_file = korean_path / xml_file.name
            out_file.write_text(translated, encoding="utf-8")
            _log(f"         ✅ 저장 완료: {out_file.name}")
            any_translated = True

    return any_translated


def process_pak_file(
    pak_path: Path,
    divine_path: str,
    api_key: str,
    log_file: str,
    cache_file: str,
    work_dir: Optional[Path] = None,
    skip_if_korean_exists: bool = True,
    mcm_enabled: bool = True,
    cancel_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    on_progress: Optional[Callable] = None,
    logger: Optional["CallbackLogger"] = None,
) -> bool:
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)

    pak_name = pak_path.stem
    output_pak = pak_path.parent / f"{pak_name}_Korean.pak"

    if output_pak.exists():
        _log(f"  ⏩ 이미 번역된 pak 존재: {output_pak.name}. 스킵")
        return False

    base_dir = work_dir if work_dir else pak_path.parent
    temp_dir = base_dir / "_pak_temp" / pak_name
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

    _log(f"  📤 언팩 중: {pak_path.name}")
    if on_progress:
        on_progress("unpack", 0, 1, pak_path.name, pak_name)
    if not divine_extract(divine_path, pak_path, temp_dir):
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    loca_count = convert_loca_to_xml(divine_path, temp_dir)
    if loca_count > 0:
        _log(f"  🔄 .loca → XML 변환: {loca_count}개 파일")

    if cancel_event and cancel_event.is_set():
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise InterruptedError("user_cancelled")

    _log("  🔄 번역 시작...")
    translated = translate_unpacked_mod(
        temp_dir, api_key, log_file,
        skip_if_korean_exists=skip_if_korean_exists,
        cancel_event=cancel_event,
        pause_event=pause_event,
        on_progress=on_progress,
        logger=logger,
    )

    mcm_changed = False
    if mcm_enabled:
        review_path = output_pak.parent / f"{pak_name}_mcm_review.json"
        try:
            mcm_stats = process_mcm_for_mod(
                temp_dir, api_key, log_file,
                review_report_path=review_path,
                cancel_event=cancel_event,
                pause_event=pause_event,
                logger=logger,
            )
        except InterruptedError:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        except Exception as e:
            _log(f"  ⚠️ MCM 처리 중 오류: {e} — Localization 번역만 적용해 진행")
            mcm_stats = None

        if mcm_stats:
            _log(
                "  🧩 MCM 처리: "
                f"Loca {mcm_stats.get('loca_translated', 0)}건, "
                f"미러 {mcm_stats.get('loca_mirrored', 0)}건, "
                f"블루프린트 {mcm_stats['blueprint_translated']}건, "
                f"Lua 자동 {mcm_stats['lua_auto']}건, "
                f"검수 {mcm_stats['lua_review']}건, "
                f"옵션 {mcm_stats['lua_options']}건"
            )
            if mcm_stats.get("report"):
                _log(f"     검수 리포트: {mcm_stats['report']}")
            mcm_changed = (
                mcm_stats.get("loca_translated", 0) > 0
                or mcm_stats.get("loca_mirrored", 0) > 0
                or mcm_stats.get("blueprint_translated", 0) > 0
                or mcm_stats.get("lua_auto", 0) > 0
            )

    if not translated and not mcm_changed:
        _log("  ⚠️ 번역할 Localization도 MCM 자산도 없음")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # .loca 바이너리와 .loca.xml 보조 파일 제거 — BG3 모드는 .xml만으로 작동.
    # 영문 .loca/.loca.xml이 남아 있으면 한국어 폴더의 한글 .xml을 가릴 위험이 있다.
    stripped = strip_loca_artifacts(temp_dir)
    if stripped > 0:
        _log(f"  🧹 .loca/.loca.xml 정리: {stripped}개 (.xml만 남김)")

    save_translation_cache(cache_file)

    _log(f"  📥 리팩 중: → {output_pak.name}")
    if on_progress:
        on_progress("repack", 0, 1, output_pak.name, pak_name)
    if not divine_repack(divine_path, temp_dir, output_pak):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    shutil.rmtree(temp_dir, ignore_errors=True)
    _log(f"  ✅ 한글화 완료: {output_pak.name}")
    if on_progress:
        on_progress("done", 1, 1, output_pak.name, pak_name)
    return True


def run_batch(
    api_key: str,
    divine_path: str,
    target_pak: str,
    log_file: str,
    cache_file: str,
    work_dir: Optional[Path] = None,
    skip_if_korean_exists: bool = True,
    mcm_enabled: bool = True,
    cancel_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    on_progress: Optional[Callable] = None,
    logger: Optional["CallbackLogger"] = None,
) -> None:
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)
    if not check_divine_exe(divine_path):
        return

    load_translation_cache(cache_file)

    target = Path(target_pak)

    if target.is_file() and target.suffix.lower() == ".pak":
        _log(f"\n[단일 pak 모드] {target.name}")
        _log("=" * 50)
        process_pak_file(
            target, divine_path, api_key, log_file, cache_file,
            work_dir=work_dir,
            skip_if_korean_exists=skip_if_korean_exists,
            mcm_enabled=mcm_enabled,
            cancel_event=cancel_event,
            pause_event=pause_event,
            on_progress=on_progress,
            logger=logger,
        )

    elif target.is_dir():
        pak_files = sorted(target.glob("*.pak"))
        pak_files = [p for p in pak_files if not p.stem.endswith("_Korean")]

        if not pak_files:
            _log(f"❌ 폴더에 .pak 파일이 없습니다: {target}")
            return

        _log(f"\n[다중 pak 모드] {target}")
        _log(f"총 {len(pak_files)}개의 .pak 파일을 처리합니다.")
        _log("=" * 50)

        stats = {"done": 0, "skipped": 0, "failed": 0}

        for i, pak_file in enumerate(pak_files, start=1):
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("user_cancelled")
            _log(f"\n[{i}/{len(pak_files)}] 📦 {pak_file.name}")
            result = process_pak_file(
                pak_file, divine_path, api_key, log_file, cache_file,
                work_dir=work_dir,
                skip_if_korean_exists=skip_if_korean_exists,
                mcm_enabled=mcm_enabled,
                cancel_event=cancel_event,
                pause_event=pause_event,
                on_progress=on_progress,
                logger=logger,
            )
            if result:
                stats["done"] += 1
            elif (pak_file.parent / f"{pak_file.stem}_Korean.pak").exists():
                stats["skipped"] += 1
            else:
                stats["failed"] += 1

        _log("\n" + "=" * 50)
        _log("[결과 요약]")
        _log(f"  ✅ 번역 완료: {stats['done']}개")
        _log(f"  ⏩ 스킵:     {stats['skipped']}개")
        _log(f"  ❌ 실패:     {stats['failed']}개")

    else:
        _log(f"❌ 지정한 경로가 .pak 파일도 폴더도 아닙니다: {target}")
        return

    save_translation_cache(cache_file)
    cache = load_translation_cache(cache_file)
    _log(f"\n💾 번역 캐시: {len(cache)}개 항목 저장됨")

    if work_dir:
        temp_root = work_dir / "_pak_temp"
        if temp_root.exists():
            shutil.rmtree(temp_root, ignore_errors=True)
