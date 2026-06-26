"""pak/loca 입출력 — 순수 Python(Divine.exe 불필요).

v7.0에서 Divine.exe(LSLib) 의존을 완전히 제거했다. pak(LSPK V18) 추출·패킹과
.loca↔xml 변환을 `bg3core.lspk`/`bg3core.loca`로 직접 수행한다.

구현은 Divine을 정답지로 실증 검증했다(공식 English.pak 232,876 엔트리 변환 일치
0 오차, Divine이 우리 pak을 바이트 동일하게 재추출). tests/test_native_oracle.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

from . import loca as _loca
from . import lspk as _lspk

if TYPE_CHECKING:
    from .logger import CallbackLogger


# ── extract pak → 폴더 ─────────────────────────────────────
def extract_pak(pak_path: Path, dest_folder: Path) -> bool:
    try:
        _lspk.read_package(pak_path, dest_folder)
        return True
    except Exception as e:
        print(f"    ❌ unpack failed: {pak_path} — {e}")
        return False


# ── loca → xml ─────────────────────────────────────────────
def convert_loca_to_xml(
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
        try:
            xml_out.write_text(_loca.loca_file_to_xml(loca_file), encoding="utf-8")
            loca_file.unlink()
            converted += 1
        except Exception as e:
            _warn(f"    ⚠️ .loca → XML conversion failed: {loca_file.name} — {e}")
    return converted


# ── 폴더 → pak ─────────────────────────────────────────────
def repack_pak(source_folder: Path, output_pak: Path) -> bool:
    try:
        _lspk.write_package(source_folder, output_pak)
        return True
    except Exception as e:
        print(f"    ❌ repack failed: {output_pak} — {e}")
        return False


# ── pak 엔트리 목록 ────────────────────────────────────────
def list_package(pak_path: Path) -> list:
    """전체 추출 없이 pak 내부 엔트리 경로 목록만 반환. 실패 시 빈 리스트."""
    try:
        return _lspk.list_package(pak_path)
    except Exception:
        return []


# ── loca 생성 계획 (순수 함수) ─────────────────────────────
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
    순수 함수 — 단위 테스트 대상.
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


# ── xml → loca ─────────────────────────────────────────────
def ensure_loca(
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
        try:
            out_loca.write_bytes(_loca.xml_to_loca_bytes(src_xml))
            generated += 1
        except Exception as e:
            _warn(f"    ⚠️ .loca generation failed: {src_xml.name} — {e}")
    return generated
