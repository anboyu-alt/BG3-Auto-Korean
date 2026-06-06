import os
import subprocess
from pathlib import Path
from typing import List, Tuple


def check_divine_exe(divine_path: str) -> bool:
    if not os.path.isfile(divine_path):
        print(f"❌ Divine.exe를 찾을 수 없습니다: {divine_path}")
        print("   LSLib ExportTool에 포함된 Divine.exe 경로를 확인하세요.")
        print("   다운로드: https://github.com/Norbyte/lslib/releases")
        return False
    return True


def divine_extract(divine_path: str, pak_path: Path, dest_folder: Path) -> bool:
    dest_folder.mkdir(parents=True, exist_ok=True)
    cmd = [
        divine_path,
        "-g", "bg3",
        "-a", "extract-package",
        "-s", str(pak_path),
        "-d", str(dest_folder),
        "-l", "all",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"    ❌ divine 언팩 실패 (exit code {result.returncode})")
            if result.stderr:
                print(f"       stderr: {result.stderr[:300]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("    ❌ divine 언팩 타임아웃 (5분 초과)")
        return False
    except Exception as e:
        print(f"    ❌ divine 실행 오류: {e}")
        return False


def convert_loca_to_xml(divine_path: str, unpacked_path: Path) -> int:
    loca_files = list(unpacked_path.rglob("*.loca"))
    converted = 0
    for loca_file in loca_files:
        if "localization" not in str(loca_file).lower():
            continue
        xml_out = loca_file.with_suffix(".loca.xml")
        cmd = [
            divine_path,
            "-g", "bg3",
            "-a", "convert-loca",
            "-s", str(loca_file),
            "-d", str(xml_out),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and xml_out.exists():
                loca_file.unlink()
                converted += 1
        except Exception:
            pass
    return converted


def convert_xml_to_loca(divine_path: str, unpacked_path: Path) -> int:
    """Localization 폴더 안의 모든 *.xml(또는 *.loca.xml)을 *.loca 바이너리로
    역변환. 한글화된 XML의 결과를 게임이 읽는 .loca 바이너리에 반영.
    변환된 파일 개수 반환.

    파일명 패턴이 두 가지로 갈리는데 모두 처리:
    - `english.loca.xml` (CRS 같은 모드) → `english.loca`
    - `english.xml` (DBW/Viltrumite 같은 모드) → `english.loca`

    같은 디렉토리에 .loca와 .xml이 공존하게 둔다(divine_repack이 둘 다 묶음).
    게임은 .loca 바이너리를 우선 읽으므로 한글이 표시된다.
    """
    converted = 0
    seen_outputs: set = set()
    for xml_file in unpacked_path.rglob("*.xml"):
        # Localization 폴더 안의 XML만 처리(다른 lsx/메타 XML 보호)
        if "localization" not in str(xml_file).lower():
            continue
        name_lower = xml_file.name.lower()
        if name_lower.endswith(".loca.xml"):
            loca_out = xml_file.with_suffix("")  # .loca.xml → .loca
        else:
            loca_out = xml_file.with_suffix(".loca")  # english.xml → english.loca
        if loca_out.suffix.lower() != ".loca":
            continue
        # .loca.xml과 .xml이 같은 베이스 이름이면 한 번만 변환
        out_key = str(loca_out).lower()
        if out_key in seen_outputs:
            continue
        seen_outputs.add(out_key)
        cmd = [
            divine_path,
            "-g", "bg3",
            "-a", "convert-loca",
            "-s", str(xml_file),
            "-d", str(loca_out),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and loca_out.exists():
                converted += 1
            else:
                # divine 변환 실패 시 stderr 일부를 출력해 다음 진단에 도움
                err = (result.stderr or result.stdout or "").strip()
                if err:
                    print(f"    ⚠️ .loca 변환 실패: {xml_file.name} — {err.splitlines()[0][:200]}")
        except Exception as e:
            print(f"    ⚠️ .loca 변환 예외: {xml_file.name} — {e}")
    return converted


def strip_loca_artifacts(unpacked_path: Path) -> int:
    """Localization 폴더 안의 .loca 바이너리와 .loca.xml 보조 파일을 정리.

    BG3 공식 모더 가이드(https://mod.io/g/baldursgate3/r/adding-localisation-ko)에
    따르면 모드는 `Localization/<언어>/*.xml`만으로 작동한다. .loca 바이너리는
    기본 게임이 빌드한 결과물이지 모드가 만들 필요가 없다. 오히려 원본 PAK에서
    추출된 영문 `.loca.xml`이 남아 있으면 게임이 한국어 폴더의 한글 `.xml`을
    가릴 위험이 있어, 패킹 직전에 깔끔하게 정리한다.

    동작:
    - 모든 `.loca` 바이너리 삭제
    - `*.loca.xml`: 같은 stem의 `*.xml`이 있으면 삭제, 없으면 `*.xml`로 rename
    """
    removed = 0
    for loca in unpacked_path.rglob("*.loca"):
        if not any(part.lower() == "localization" for part in loca.parts):
            continue
        try:
            loca.unlink()
            removed += 1
        except Exception:
            pass

    for loca_xml in list(unpacked_path.rglob("*.loca.xml")):
        if not any(part.lower() == "localization" for part in loca_xml.parts):
            continue
        base = loca_xml.name[: -len(".loca.xml")]
        sibling_xml = loca_xml.with_name(base + ".xml")
        try:
            if sibling_xml.exists():
                loca_xml.unlink()
                removed += 1
            else:
                loca_xml.rename(sibling_xml)
                removed += 1
        except Exception:
            pass
    return removed


def divine_repack(divine_path: str, source_folder: Path, output_pak: Path) -> bool:
    output_pak.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        divine_path,
        "-g", "bg3",
        "-a", "create-package",
        "-s", str(source_folder),
        "-d", str(output_pak),
        "-c", "lz4",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"    ❌ divine 리팩 실패 (exit code {result.returncode})")
            if result.stderr:
                print(f"       stderr: {result.stderr[:300]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("    ❌ divine 리팩 타임아웃 (5분 초과)")
        return False
    except Exception as e:
        print(f"    ❌ divine 실행 오류: {e}")
        return False


def list_package(divine_path: str, pak_path: Path) -> list:
    """전체 추출 없이 pak 내부 엔트리 경로 목록만 반환. 실패 시 빈 리스트."""
    cmd = [
        divine_path,
        "-g", "bg3",
        "-a", "list-package",
        "-s", str(pak_path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def plan_loca_generation(unpacked_path: Path) -> List[Tuple[Path, Path]]:
    """Localization 하위에서 .loca가 없는 xml에 대해 생성할 (src_xml, out_loca) 목록 반환.

    - 출력 규칙: `X.loca.xml` → `X.loca`, `X.xml` → `X.loca`.
    - dedup: 같은 out_loca가 둘 이상이면 한 번만. `X.xml`(정식)과 `X.loca.xml` 공존 시
      `X.xml`을 src로 선택.
    - 멱등: out_loca가 이미 존재하면 제외.
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
        if out.exists():
            continue
        result.append((src, out))
    return result
