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
