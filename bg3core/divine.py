import os
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from .logger import CallbackLogger

# divine CLI 상수 — 모든 subprocess 호출이 이 값을 참조한다.
# v5.0 다국어 대응 시 파라미터화 지점.
_GAME = "bg3"
_COMPRESS = "lz4"
_LANG_ALL = "all"
_TIMEOUT_SHORT = 60    # 단일 .loca 변환
_TIMEOUT_MED = 120     # list-package
_TIMEOUT_LONG = 300    # extract / repack


def check_divine_exe(divine_path: str) -> bool:
    if not os.path.isfile(divine_path):
        print(f"❌ Divine.exe not found: {divine_path}")
        print("   Check the Divine.exe path (from LSLib ExportTool).")
        print("   Download: https://github.com/Norbyte/lslib/releases")
        return False
    return True


def divine_extract(divine_path: str, pak_path: Path, dest_folder: Path) -> bool:
    dest_folder.mkdir(parents=True, exist_ok=True)
    cmd = [
        divine_path,
        "-g", _GAME,
        "-a", "extract-package",
        "-s", str(pak_path),
        "-d", str(dest_folder),
        "-l", _LANG_ALL,
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

    loca_files = list(unpacked_path.rglob("*.loca"))
    converted = 0
    for loca_file in loca_files:
        if "localization" not in str(loca_file).lower():
            continue
        xml_out = loca_file.with_suffix(".loca.xml")
        cmd = [
            divine_path,
            "-g", _GAME,
            "-a", "convert-loca",
            "-s", str(loca_file),
            "-d", str(xml_out),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT_SHORT)
            if result.returncode == 0 and xml_out.exists():
                loca_file.unlink()
                converted += 1
            else:
                err = (result.stderr or result.stdout or "").strip()
                if err:
                    _warn(f"    ⚠️ .loca → XML conversion failed: {loca_file.name} — {err.splitlines()[0][:200]}")
        except Exception as e:
            _warn(f"    ⚠️ .loca → XML conversion error: {loca_file.name} — {e}")
    return converted


def divine_repack(divine_path: str, source_folder: Path, output_pak: Path) -> bool:
    output_pak.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        divine_path,
        "-g", _GAME,
        "-a", "create-package",
        "-s", str(source_folder),
        "-d", str(output_pak),
        "-c", _COMPRESS,
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


def list_package(divine_path: str, pak_path: Path) -> list:
    """전체 추출 없이 pak 내부 엔트리 경로 목록만 반환. 실패 시 빈 리스트."""
    cmd = [
        divine_path,
        "-g", _GAME,
        "-a", "list-package",
        "-s", str(pak_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT_MED)
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


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
        cmd = [
            divine_path,
            "-g", _GAME,
            "-a", "convert-loca",
            "-s", str(src_xml),
            "-d", str(out_loca),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=_TIMEOUT_SHORT)
            if result.returncode == 0 and out_loca.exists():
                generated += 1
            else:
                err = (result.stderr or result.stdout or "").strip()
                if err:
                    _warn(f"    ⚠️ .loca generation failed: {src_xml.name} — {err.splitlines()[0][:200]}")
        except Exception as e:
            _warn(f"    ⚠️ .loca generation error: {src_xml.name} — {e}")
    return generated
