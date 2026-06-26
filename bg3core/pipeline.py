import re
import shutil
import threading
import time
from pathlib import Path
from typing import List, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .logger import CallbackLogger

from .constants import INPUT_GLOB
from .packio import extract_pak, convert_loca_to_xml, ensure_loca, repack_pak
from .language import LanguageProfile, get_profile, is_already_translated, DEFAULT_PROFILE
from .translate import (
    process_xml_file, load_translation_cache, save_translation_cache,
)
from .official_glossary import extract_official_glossary
from .mcm import process_mcm_for_mod
from .mcm.loca_handles import mirror_loca_to_source_languages


def find_localization_folders(root_path: Path) -> List[Path]:
    return list(root_path.rglob("Localization"))


def has_target_folder(loc_path: Path, folder_name: str) -> bool:
    return (loc_path / folder_name).exists()


def list_source_language_dirs(loc_path: Path, target_folder_name: str = "Korean") -> List[Path]:
    if not loc_path.exists():
        return []
    src_dirs = [
        p for p in loc_path.iterdir()
        if p.is_dir() and p.name.lower() != target_folder_name.lower()
    ]
    src_dirs.sort(key=lambda x: (0 if x.name.lower() == "english" else 1, x.name.lower()))
    return src_dirs


def translate_unpacked_mod(
    unpacked_path: Path,
    api_key: str,
    log_file: str,
    skip_if_target_exists: bool = True,
    target_profile: LanguageProfile = DEFAULT_PROFILE,
    cancel_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    on_progress: Optional[Callable] = None,
    logger: Optional["CallbackLogger"] = None,
    official: Optional[dict] = None,
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

        if skip_if_target_exists and has_target_folder(loc_path, target_profile.folder_name):
            _log(f"       {target_profile.folder_name} folder already exists. Skipping")
            continue

        src_dirs = list_source_language_dirs(loc_path, target_profile.folder_name)
        if not src_dirs:
            _log("       No source language subfolder found. Skipping")
            continue

        target_path = loc_path / target_profile.folder_name
        target_path.mkdir(parents=True, exist_ok=True)

        src_dir = src_dirs[0]
        if len(src_dirs) > 1:
            _log(f"       {len(src_dirs)} language folders. Using '{src_dir.name}' as source")

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
                _log(f"       ⚠️ No XML files in {src_dir.name}. Found: {names}")
            else:
                _log(f"       ⚠️ {src_dir.name} folder is empty")
            continue

        _log(f"       Source folder: {src_dir.name} (XML: {len(xml_files)})")

        total_files = len(xml_files)
        for file_idx, xml_file in enumerate(xml_files, start=1):
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("user_cancelled")
            _log(f"       ▶ Processing: {xml_file.name}")
            if on_progress:
                on_progress("translate", file_idx, total_files, xml_file.name)

            try:
                original = xml_file.read_text(encoding="utf-8", errors="strict")
            except UnicodeDecodeError:
                original = xml_file.read_text(encoding="utf-8", errors="replace")

            if not original.strip():
                _log("         Empty file. Skipping")
                continue

            if is_already_translated(original, target_profile):
                _log("         Already translated. Skipping")
                continue

            translated = process_xml_file(
                original, xml_file.name, api_key, log_file,
                cancel_event=cancel_event,
                pause_event=pause_event,
                logger=logger,
                target_profile=target_profile,
                official=official,
            )

            out_file = target_path / xml_file.name
            out_file.write_text(translated, encoding="utf-8")
            _log(f"         ✅ Saved: {out_file.name}")
            any_translated = True

    return any_translated


def process_pak_file(
    pak_path: Path,
    api_key: str,
    log_file: str,
    cache_file: str,
    work_dir: Optional[Path] = None,
    skip_if_target_exists: bool = True,
    target_profile: LanguageProfile = DEFAULT_PROFILE,
    mcm_enabled: bool = True,
    cancel_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    on_progress: Optional[Callable] = None,
    logger: Optional["CallbackLogger"] = None,
    official: Optional[dict] = None,
) -> bool:
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)

    pak_name = pak_path.stem
    output_pak = pak_path.parent / f"{pak_name}_{target_profile.folder_name}.pak"

    if output_pak.exists():
        _log(f"  ⏩ Translated pak already exists: {output_pak.name}. Skipping")
        return False

    base_dir = work_dir if work_dir else pak_path.parent
    temp_dir = base_dir / "_pak_temp" / pak_name
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

    _log(f"  📤 Unpacking: {pak_path.name}")
    if on_progress:
        on_progress("unpack", 0, 1, pak_path.name, pak_name)
    if not extract_pak(pak_path, temp_dir):
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    loca_count = convert_loca_to_xml(temp_dir, logger=logger)
    if loca_count > 0:
        _log(f"  🔄 .loca → XML: {loca_count} files")

    if cancel_event and cancel_event.is_set():
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise InterruptedError("user_cancelled")

    _log("  🔄 Translating...")
    translated = translate_unpacked_mod(
        temp_dir, api_key, log_file,
        skip_if_target_exists=skip_if_target_exists,
        target_profile=target_profile,
        cancel_event=cancel_event,
        pause_event=pause_event,
        on_progress=on_progress,
        logger=logger,
        official=official,
    )

    mcm_changed = False
    if mcm_enabled:
        review_path = output_pak.parent / f"{pak_name}_mcm_review.json"
        try:
            mcm_stats = process_mcm_for_mod(
                temp_dir, api_key, log_file,
                target_profile=target_profile,
                review_report_path=review_path,
                cancel_event=cancel_event,
                pause_event=pause_event,
                logger=logger,
            )
        except InterruptedError:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise
        except Exception as e:
            _log(f"  ⚠️ MCM processing error: {e} — continuing with Localization only")
            mcm_stats = None

        if mcm_stats:
            _log(
                "  🧩 MCM: "
                f"loca {mcm_stats.get('loca_translated', 0)}, "
                f"mirror {mcm_stats.get('loca_mirrored', 0)}, "
                f"blueprint {mcm_stats['blueprint_translated']}, "
                f"Lua auto {mcm_stats['lua_auto']}, "
                f"review {mcm_stats['lua_review']}, "
                f"options {mcm_stats['lua_options']}"
            )
            if mcm_stats.get("report"):
                _log(f"     Review report: {mcm_stats['report']}")
            mcm_changed = (
                mcm_stats.get("loca_translated", 0) > 0
                or mcm_stats.get("loca_mirrored", 0) > 0
                or mcm_stats.get("blueprint_translated", 0) > 0
                or mcm_stats.get("lua_auto", 0) > 0
            )

    if not translated and not mcm_changed:
        _log("  ⚠️ No Localization or MCM assets to translate")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    # BG3는 표준 구조 모드의 로컬라이제이션을 .loca 바이너리에서 읽는다.
    # 번역된 xml에서 각 언어 .loca를 생성해 포함시킨다(없는 것만 — 멱등).
    generated = ensure_loca(temp_dir, logger=logger)
    if generated > 0:
        _log(f"  🧩 Generated .loca: {generated}")

    # 일부 모드는 게임 언어와 무관하게 영어 Localization에서 텍스트를 읽는다. 영어
    # .xml 원문은 보존하면서, 번역된 .loca를 영어 등 소스 언어 폴더의 .loca로 복사해
    # 인게임 번역 표시를 보장한다(검수·원문 유지와 양립).
    mirrored_loca = mirror_loca_to_source_languages(
        temp_dir, target_folder=target_profile.folder_name, logger=logger
    )
    if mirrored_loca > 0:
        _log(f"  🧩 Mirrored .loca: {mirrored_loca} (English .xml preserved)")

    save_translation_cache(cache_file)

    _log(f"  📥 Repacking → {output_pak.name}")
    if on_progress:
        on_progress("repack", 0, 1, output_pak.name, pak_name)
    if not repack_pak(temp_dir, output_pak):
        shutil.rmtree(temp_dir, ignore_errors=True)
        return False

    shutil.rmtree(temp_dir, ignore_errors=True)
    _log(f"  ✅ {target_profile.display_name} done: {output_pak.name}")
    if on_progress:
        on_progress("done", 1, 1, output_pak.name, pak_name)
    return True


def run_batch(
    api_key: str,
    target_pak: str,
    log_file: str,
    cache_file: str,
    work_dir: Optional[Path] = None,
    skip_if_target_exists: bool = True,
    target_language: str = "Korean",
    mcm_enabled: bool = True,
    cancel_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    on_progress: Optional[Callable] = None,
    logger: Optional["CallbackLogger"] = None,
    bg3_install_path: str = "",
    use_official_glossary: bool = False,
) -> None:
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)
    target_profile = get_profile(target_language)

    load_translation_cache(cache_file)

    # ④ 공식 언어팩 참조 사전: 활성화 시 게임 팩에서 한 번 빌드(또는 캐시 로드)해
    # 모든 pak 처리에 공유한다. 비활성/미발견이면 None → 기존 동작.
    official = None
    if use_official_glossary:
        try:
            official = extract_official_glossary(
                bg3_install_path, target_profile.folder_name,
                logger=logger,
            )
            if official is None:
                _log("  ℹ️ Official glossary unavailable (check BG3 path / language pack)")
        except Exception as e:
            _log(f"  ⚠️ Official glossary build failed: {e} — continuing without it")
            official = None

    target = Path(target_pak)

    if target.is_file() and target.suffix.lower() == ".pak":
        _log(f"\n[Single pak] {target.name}")
        _log("=" * 50)
        process_pak_file(
            target, api_key, log_file, cache_file,
            work_dir=work_dir,
            skip_if_target_exists=skip_if_target_exists,
            target_profile=target_profile,
            mcm_enabled=mcm_enabled,
            cancel_event=cancel_event,
            pause_event=pause_event,
            on_progress=on_progress,
            logger=logger,
            official=official,
        )

    elif target.is_dir():
        pak_files = sorted(target.glob("*.pak"))
        pak_files = [p for p in pak_files if not p.stem.endswith(f"_{target_profile.folder_name}")]

        if not pak_files:
            _log(f"❌ No .pak files in folder: {target}")
            return

        _log(f"\n[Batch pak] {target}")
        _log(f"Processing {len(pak_files)} .pak files.")
        _log("=" * 50)

        stats = {"done": 0, "skipped": 0, "failed": 0}

        for i, pak_file in enumerate(pak_files, start=1):
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("user_cancelled")
            _log(f"\n[{i}/{len(pak_files)}] 📦 {pak_file.name}")
            result = process_pak_file(
                pak_file, api_key, log_file, cache_file,
                work_dir=work_dir,
                skip_if_target_exists=skip_if_target_exists,
                target_profile=target_profile,
                mcm_enabled=mcm_enabled,
                cancel_event=cancel_event,
                pause_event=pause_event,
                on_progress=on_progress,
                logger=logger,
                official=official,
            )
            if result:
                stats["done"] += 1
            elif (pak_file.parent / f"{pak_file.stem}_{target_profile.folder_name}.pak").exists():
                stats["skipped"] += 1
            else:
                stats["failed"] += 1

        _log("\n" + "=" * 50)
        _log("[Summary]")
        _log(f"  ✅ Done: {stats['done']}")
        _log(f"  ⏩ Skipped: {stats['skipped']}")
        _log(f"  ❌ Failed: {stats['failed']}")

    else:
        _log(f"❌ Path is neither a .pak file nor a folder: {target}")
        return

    save_translation_cache(cache_file)
    cache = load_translation_cache(cache_file)
    _log(f"\n💾 Translation cache: {len(cache)} entries saved")

    if work_dir:
        temp_root = work_dir / "_pak_temp"
        if temp_root.exists():
            shutil.rmtree(temp_root, ignore_errors=True)
