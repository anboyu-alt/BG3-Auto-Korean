"""pak/loca 입출력 — 네이티브(Python) 백엔드 우선, Divine.exe는 폴백.

v7.0부터 pak(LSPK V18)·loca 변환을 순수 Python(`bg3core.lspk`, `bg3core.loca`)으로
처리한다. Divine.exe(LSLib) 의존을 제거하기 위한 단계적 전환이며, 네이티브 경로가
예외를 던지면(또는 환경변수 BG3_FORCE_DIVINE=1) 기존 Divine subprocess로 폴백한다.

공개 함수 시그니처는 종전과 동일하다(divine_path 인자 유지) — pipeline·official_glossary·
reviewer_tab 등 호출처를 수정하지 않는다. 네이티브 백엔드는 divine_path 없이도 동작한다.

네이티브 구현은 Divine을 정답지로 실증 검증했다(공식 English.pak 232,876 엔트리 변환
일치 0 오차, Divine이 우리 pak을 바이트 동일하게 재추출). tests/test_native_oracle.py.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from .logger import CallbackLogger

# divine CLI 상수 — subprocess 폴백 호출이 참조한다.
_GAME = "bg3"
_COMPRESS = "lz4"
_LANG_ALL = "all"
_TIMEOUT_SHORT = 60    # 단일 .loca 변환
_TIMEOUT_MED = 120     # list-package
_TIMEOUT_LONG = 300    # extract / repack


def _force_divine() -> bool:
    return os.environ.get("BG3_FORCE_DIVINE", "") not in ("", "0", "false", "False")


def _native_ok() -> bool:
    """네이티브 백엔드(lz4 의존 포함)가 사용 가능하고, 강제 Divine이 아닌지."""
    if _force_divine():
        return False
    try:
        import lz4.block  # noqa: F401
        return True
    except Exception:
        return False


def check_divine_exe(divine_path: str) -> bool:
    """파이프라인 진입 가드. 네이티브 백엔드가 있으면 Divine 없이도 통과한다."""
    if _native_ok():
        return True
    if not os.path.isfile(divine_path):
        print(f"❌ Divine.exe not found: {divine_path}")
        print("   Check the Divine.exe path (from LSLib ExportTool).")
        print("   Download: https://github.com/Norbyte/lslib/releases")
        return False
    return True


def _has_divine(divine_path: str) -> bool:
    return bool(divine_path) and os.path.isfile(divine_path)


# ── extract-package ────────────────────────────────────────
def divine_extract(divine_path: str, pak_path: Path, dest_folder: Path) -> bool:
    if _native_ok():
        try:
            from . import lspk
            lspk.read_package(pak_path, dest_folder)
            return True
        except Exception as e:
            if not _has_divine(divine_path):
                print(f"    ❌ native unpack failed: {e}")
                return False
            print(f"    ⚠️ native unpack failed ({e}); falling back to Divine")
    return _divine_extract_subprocess(divine_path, pak_path, dest_folder)


def _divine_extract_subprocess(divine_path: str, pak_path: Path, dest_folder: Path) -> bool:
    dest_folder.mkdir(parents=True, exist_ok=True)
    cmd = [
        divine_path, "-g", _GAME, "-a", "extract-package",
        "-s", str(pak_path), "-d", str(dest_folder), "-l", _LANG_ALL,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT_LONG)
        if result.returncode != 0:
            print(f"    ❌ divine unpack failed (exit code {result.returncode})")
            if result.stderr:
                print(f"       stderr: {result.stderr[:300]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"    ❌ divine unpack timeout (> {_TIMEOUT_LONG // 60} min)")
        return False
    except Exception as e:
        print(f"    ❌ divine error: {e}")
        return False


# ── convert-loca (loca → xml) ──────────────────────────────
def convert_loca_to_xml(
    divine_path: str,
    unpacked_path: Path,
    logger: Optional["CallbackLogger"] = None,
) -> int:
    """Localization 폴더 안의 *.loca 바이너리를 *.loca.xml로 변환. 변환 개수 반환."""
    def _warn(msg: str) -> None:
        if logger:
            logger.warning(msg)
        else:
            print(msg)

    loca_files = [
        p for p in unpacked_path.rglob("*.loca")
        if "localization" in str(p).lower()
    ]
    converted = 0
    for loca_file in loca_files:
        xml_out = loca_file.with_suffix(".loca.xml")
        if _native_ok():
            try:
                from . import loca as _loca
                xml_out.write_text(_loca.loca_file_to_xml(loca_file), encoding="utf-8")
                loca_file.unlink()
                converted += 1
                continue
            except Exception as e:
                if not _has_divine(divine_path):
                    _warn(f"    ⚠️ .loca → XML conversion failed: {loca_file.name} — {e}")
                    continue
                _warn(f"    ⚠️ native loca→xml failed ({loca_file.name}: {e}); using Divine")
        if _native_convert_one_loca_via_divine(divine_path, loca_file, xml_out, _warn):
            converted += 1
    return converted


def _native_convert_one_loca_via_divine(divine_path, loca_file, xml_out, _warn) -> bool:
    cmd = [
        divine_path, "-g", _GAME, "-a", "convert-loca",
        "-s", str(loca_file), "-d", str(xml_out),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT_SHORT)
        if result.returncode == 0 and xml_out.exists():
            loca_file.unlink()
            return True
        err = (result.stderr or result.stdout or "").strip()
        if err:
            _warn(f"    ⚠️ .loca → XML conversion failed: {loca_file.name} — {err.splitlines()[0][:200]}")
    except Exception as e:
        _warn(f"    ⚠️ .loca → XML conversion error: {loca_file.name} — {e}")
    return False


# ── create-package ─────────────────────────────────────────
def divine_repack(divine_path: str, source_folder: Path, output_pak: Path) -> bool:
    if _native_ok():
        try:
            from . import lspk
            lspk.write_package(source_folder, output_pak)
            return True
        except Exception as e:
            if not _has_divine(divine_path):
                print(f"    ❌ native repack failed: {e}")
                return False
            print(f"    ⚠️ native repack failed ({e}); falling back to Divine")
    return _divine_repack_subprocess(divine_path, source_folder, output_pak)


def _divine_repack_subprocess(divine_path: str, source_folder: Path, output_pak: Path) -> bool:
    output_pak.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        divine_path, "-g", _GAME, "-a", "create-package",
        "-s", str(source_folder), "-d", str(output_pak), "-c", _COMPRESS,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT_LONG)
        if result.returncode != 0:
            print(f"    ❌ divine repack failed (exit code {result.returncode})")
            if result.stderr:
                print(f"       stderr: {result.stderr[:300]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"    ❌ divine repack timeout (> {_TIMEOUT_LONG // 60} min)")
        return False
    except Exception as e:
        print(f"    ❌ divine error: {e}")
        return False


# ── list-package ───────────────────────────────────────────
def list_package(divine_path: str, pak_path: Path) -> list:
    """전체 추출 없이 pak 내부 엔트리 경로 목록만 반환. 실패 시 빈 리스트."""
    if _native_ok():
        try:
            from . import lspk
            return lspk.list_package(pak_path)
        except Exception:
            if not _has_divine(divine_path):
                return []
    cmd = [divine_path, "-g", _GAME, "-a", "list-package", "-s", str(pak_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT_MED)
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


# ── loca 생성 계획 (순수 함수, divine 비호출) ──────────────
def plan_loca_generation(
    unpacked_path: Path,
    force: bool = False,
) -> List[Tuple[Path, Path]]:
    """Localization 하위에서 .loca를 생성해야 할 (src_xml, out_loca) 목록 반환.

    - 출력 규칙: `X.loca.xml` → `X.loca`, `X.xml` → `X.loca`.
    - dedup: 같은 out_loca가 둘 이상이면 한 번만. `X.xml`(정식)과 `X.loca.xml` 공존 시
      `X.xml`을 src로 선택.
    - force=False(기본): out_loca가 이미 존재하면 제외(멱등) — pipeline 용.
    - force=True: 기존 .loca도 재생성 대상에 포함 — 검수 저장 후 강제 반영 시 사용.
    순수 함수(divine 비호출) — 단위 테스트 대상.
    """
    chosen = {}  # out_key(lower) -> (src_xml, out_loca, is_canonical)
    for xml in unpacked_path.rglob("*.xml"):
        if not any(part.lower() == "localization" for part in xml.parts):
            continue
        name = xml.name
        low = name.lower()
        if low.endswith(".loca.xml"):
            out = xml.with_name(name[: -len(".loca.xml")] + ".loca")
            canonical = False
        else:
            out = xml.with_name(name[: -len(".xml")] + ".loca")
            canonical = True
        key = str(out).lower()
        prev = chosen.get(key)
        if prev is None:
            chosen[key] = (xml, out, canonical)
        elif canonical and not prev[2]:
            chosen[key] = (xml, out, canonical)
    result = []
    for src, out, _ in chosen.values():
        if not force and out.exists():
            continue
        result.append((src, out))
    return result


# ── convert-loca (xml → loca) ──────────────────────────────
def ensure_loca(
    divine_path: str,
    unpacked_path: Path,
    force: bool = False,
    logger: Optional["CallbackLogger"] = None,
) -> int:
    """Localization xml에서 .loca 바이너리를 생성. 생성 개수 반환.

    plan_loca_generation으로 대상을 고른 뒤 각각 변환한다.
    force=False(기본): 이미 .loca 있으면 스킵(멱등) — pipeline 용.
    force=True: 기존 .loca도 재생성 — 검수 저장 후 편집 내용 반영 시 사용.
    BG3는 표준 구조 모드의 로컬라이제이션을 .loca 바이너리에서 읽으므로 필수.
    """
    def _warn(msg: str) -> None:
        if logger:
            logger.warning(msg)
        else:
            print(msg)

    generated = 0
    for src_xml, out_loca in plan_loca_generation(unpacked_path, force=force):
        if _native_ok():
            try:
                from . import loca as _loca
                out_loca.write_bytes(_loca.xml_to_loca_bytes(src_xml))
                generated += 1
                continue
            except Exception as e:
                if not _has_divine(divine_path):
                    _warn(f"    ⚠️ .loca generation failed: {src_xml.name} — {e}")
                    continue
                _warn(f"    ⚠️ native xml→loca failed ({src_xml.name}: {e}); using Divine")
        if _ensure_one_loca_via_divine(divine_path, src_xml, out_loca, _warn):
            generated += 1
    return generated


def _ensure_one_loca_via_divine(divine_path, src_xml, out_loca, _warn) -> bool:
    cmd = [
        divine_path, "-g", _GAME, "-a", "convert-loca",
        "-s", str(src_xml), "-d", str(out_loca),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT_SHORT)
        if result.returncode == 0 and out_loca.exists():
            return True
        err = (result.stderr or result.stdout or "").strip()
        if err:
            _warn(f"    ⚠️ .loca generation failed: {src_xml.name} — {err.splitlines()[0][:200]}")
    except Exception as e:
        _warn(f"    ⚠️ .loca generation error: {src_xml.name} — {e}")
    return False
