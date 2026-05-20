import os
import subprocess
from pathlib import Path


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
