# ==========================================
# BG3 모드 번역 검수 도구 v2.2
# ==========================================
# AI가 번역한 결과물을 영어 원문과 나란히 비교하면서
# 오역을 찾아 수정할 수 있는 도구입니다.
#
# 사용법:
#   1. 아래 [설정 구간]에서 DIVINE_EXE와 TARGET_PAK 경로를 지정
#   2. 더블클릭 또는 python BG3_AutoKorean_Reviewer_v2.2.py 실행
#   3. 영어/한국어를 비교하면서 수정이 필요한 항목만 고치기
#   4. 's'를 눌러 저장하면 수정된 pak 파일이 생성됩니다
#
# 조작법:
#   스페이스/엔터 = 다음 항목
#   b            = 이전 항목
#   e            = 현재 항목 수정
#   s            = 저장 후 종료 (수정된 pak 생성)
#   q            = 저장 없이 종료
#   g            = 번호로 이동
#   /            = 텍스트 검색
#   m            = 수정된 항목만 보기 토글
#
# 필요한 것:
#   - Python 3.7+
#   - divine.exe (LSLib ExportTool)
#   - .NET 8.0 런타임
#
# 함께 사용하는 파일:
#   - BG3_AutoKorean_PAK_v2.2.py (번역 도구 — pak 모드)
#   - BG3_AutoKorean_Folder_v2.2.py (번역 도구 — 폴더 모드)
# ==========================================

import os
import re
import sys
import shutil
import subprocess
import msvcrt
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional


# ==========================================
# [설정 구간] DIVINE_EXE만 설정하면 됩니다
# ==========================================
# DIVINE_EXE: divine.exe 경로 (LSLib ExportTool에 포함)
#   → 이것만 미리 넣어두면 편합니다. 매번 같으니까요.
#   → 경로 앞에 r을 붙이고 큰따옴표로 감싸세요.
#   → 예: DIVINE_EXE = r"F:\ExportTool\Packed\Tools\Divine.exe"
#
# TARGET_PAK: 비워두세요! (매번 다른 파일을 검수하니까)
#   → 실행하면 pak 파일 경로나 폴더 경로를 입력할 수 있습니다.
#   → 폴더를 입력하면 안의 pak 목록에서 골라서 선택합니다.
#   → 또는 .pak 파일을 이 스크립트 위에 드래그 앤 드롭해도 됩니다!
# ==========================================
DIVINE_EXE = ""
TARGET_PAK = ""


# ==========================================
# [XML 파싱] content 블록 추출용 정규식
# ==========================================
CONTENT_BLOCK_RE = re.compile(
    r"(<content\b[^>]*>.*?</content>)", re.DOTALL | re.IGNORECASE
)
CONTENT_INNER_RE = re.compile(
    r"(<content\b[^>]*>)(.*?)(</content>)", re.DOTALL | re.IGNORECASE
)
CONTENTUID_RE = re.compile(
    r'contentuid="([^"]*)"', re.IGNORECASE
)


# ==========================================
# [데이터 구조]
# ==========================================
@dataclass
class Entry:
    """영어-한국어 번역 쌍 하나를 표현"""
    contentuid: str
    english: str
    korean: str
    modified: bool = False
    new_korean: str = ""

    @property
    def display_korean(self) -> str:
        return self.new_korean if self.modified else self.korean


@dataclass
class ReviewFile:
    """하나의 XML 파일에 대한 검수 데이터"""
    filename: str
    entries: List[Entry]
    korean_xml_path: Path
    korean_xml_original: str  # 원본 Korean XML 전체 텍스트


# ==========================================
# [divine.exe 연동] pak 언팩/리팩
# ==========================================
def check_divine_exe(divine_path: str) -> bool:
    if not os.path.isfile(divine_path):
        print(f"  ❌ Divine.exe를 찾을 수 없습니다: {divine_path}")
        print("     LSLib ExportTool에 포함된 Divine.exe 경로를 확인하세요.")
        print("     다운로드: https://github.com/Norbyte/lslib/releases")
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
            print(f"  ❌ divine 언팩 실패 (exit code {result.returncode})")
            if result.stderr:
                print(f"     {result.stderr[:300]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("  ❌ divine 언팩 타임아웃 (5분 초과)")
        return False
    except Exception as e:
        print(f"  ❌ divine 실행 오류: {e}")
        return False


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
            print(f"  ❌ divine 리팩 실패 (exit code {result.returncode})")
            if result.stderr:
                print(f"     {result.stderr[:300]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print("  ❌ divine 리팩 타임아웃 (5분 초과)")
        return False
    except Exception as e:
        print(f"  ❌ divine 실행 오류: {e}")
        return False


# ==========================================
# [XML 로드] English/Korean XML에서 항목 추출 & 매칭
# ==========================================
def extract_entries_from_xml(xml_text: str) -> Dict[str, str]:
    """XML 텍스트에서 {contentuid: inner_text} 딕셔너리를 만든다."""
    entries = {}
    for m in CONTENT_INNER_RE.finditer(xml_text):
        open_tag = m.group(1)
        inner = m.group(2)
        uid_match = CONTENTUID_RE.search(open_tag)
        if uid_match:
            uid = uid_match.group(1)
            entries[uid] = inner.strip()
    return entries


def load_review_files(unpacked_path: Path) -> List[ReviewFile]:
    """언팩된 폴더에서 English/Korean XML을 매칭하여 ReviewFile 리스트를 만든다."""
    review_files = []

    for loc_dir in unpacked_path.rglob("Localization"):
        if not loc_dir.is_dir():
            continue

        # English와 Korean 폴더 찾기
        english_dir = None
        korean_dir = None
        for sub in loc_dir.iterdir():
            if sub.is_dir():
                if sub.name.lower() == "english":
                    english_dir = sub
                elif sub.name.lower() == "korean":
                    korean_dir = sub

        if not english_dir or not korean_dir:
            continue

        # 각 Korean XML 파일에 대해 매칭되는 English XML 찾기
        for kr_xml in sorted(korean_dir.glob("*.xml")):
            en_xml = english_dir / kr_xml.name
            if not en_xml.exists():
                # 이름이 다를 수 있으므로, English 폴더에 XML이 하나뿐이면 그것 사용
                en_xmls = list(english_dir.glob("*.xml"))
                if len(en_xmls) == 1:
                    en_xml = en_xmls[0]
                else:
                    continue

            try:
                en_text = en_xml.read_text(encoding="utf-8", errors="replace")
                kr_text = kr_xml.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue

            en_entries = extract_entries_from_xml(en_text)
            kr_entries = extract_entries_from_xml(kr_text)

            if not en_entries or not kr_entries:
                continue

            entries = []
            for uid, en_inner in en_entries.items():
                kr_inner = kr_entries.get(uid, "")
                if not kr_inner:
                    continue
                # 영어와 한국어가 완전히 같으면 (번역 안 된 항목) 표시는 하되 구분
                entries.append(Entry(
                    contentuid=uid,
                    english=en_inner,
                    korean=kr_inner,
                ))

            if entries:
                review_files.append(ReviewFile(
                    filename=kr_xml.name,
                    entries=entries,
                    korean_xml_path=kr_xml,
                    korean_xml_original=kr_text,
                ))

    return review_files


# ==========================================
# [저장] 수정된 항목을 Korean XML에 반영
# ==========================================
def save_modified_xml(review_file: ReviewFile) -> None:
    """수정된 항목이 있는 ReviewFile의 Korean XML을 업데이트한다."""
    modified_entries = {e.contentuid: e.new_korean for e in review_file.entries if e.modified}
    if not modified_entries:
        return

    xml_text = review_file.korean_xml_original

    def replace_content(match):
        open_tag = match.group(1)
        inner = match.group(2)
        close_tag = match.group(3)
        uid_match = CONTENTUID_RE.search(open_tag)
        if uid_match and uid_match.group(1) in modified_entries:
            return f"{open_tag}{modified_entries[uid_match.group(1)]}{close_tag}"
        return match.group(0)

    new_xml = CONTENT_INNER_RE.sub(replace_content, xml_text)
    review_file.korean_xml_path.write_text(new_xml, encoding="utf-8")


# ==========================================
# [화면 표시] 터미널 UI
# ==========================================
def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def get_terminal_width() -> int:
    try:
        return os.get_terminal_size().columns
    except OSError:
        return 60


def wrap_text(text: str, width: int) -> str:
    """긴 텍스트를 터미널 폭에 맞게 줄바꿈한다."""
    lines = []
    for line in text.split("\n"):
        while len(line) > width:
            # 공백 위치에서 자르기
            cut = line.rfind(" ", 0, width)
            if cut <= 0:
                cut = width
            lines.append(line[:cut])
            line = line[cut:].lstrip()
        lines.append(line)
    return "\n".join(lines)


def display_entry(entry: Entry, index: int, total: int,
                  filename: str, modified_count: int,
                  show_modified_only: bool) -> None:
    """현재 항목을 화면에 표시한다."""
    clear_screen()
    tw = get_terminal_width()
    w = min(tw - 4, 70)  # 최대 70자 폭
    bar = "=" * (w + 4)
    sep = "-" * (w + 4)

    filter_mark = " [수정된 항목만]" if show_modified_only else ""
    mod_mark = " *수정됨*" if entry.modified else ""

    print(bar)
    print(f"  번역 검수 도구 v2.2  |  {filename}  |  {index + 1} / {total}{filter_mark}")
    print(f"  수정된 항목: {modified_count}개{mod_mark}")
    print(bar)
    print()

    # 영어 원문
    print("  [원문 - English]")
    en_wrapped = wrap_text(entry.english, w)
    for line in en_wrapped.split("\n"):
        print(f"  {line}")
    print()

    # 한국어 번역
    print("  [번역 - Korean]")
    kr_wrapped = wrap_text(entry.display_korean, w)
    for line in kr_wrapped.split("\n"):
        print(f"  {line}")
    print()

    print(sep)
    print("  스페이스/엔터: 다음  |  b: 이전  |  e: 수정")
    print("  s: 저장 후 종료  |  q: 저장 없이 종료")
    print("  g: 번호로 이동  |  /: 검색  |  m: 수정된 항목만 보기")
    print(bar)


def edit_entry(entry: Entry) -> bool:
    """항목 수정 모드. 수정하면 True, 취소하면 False 반환."""
    print()
    print("  [수정] 새 번역을 입력하세요.")
    print("  (여러 줄 입력 가능. 빈 줄을 입력하면 완료)")
    print("  (c를 입력하면 수정 취소)")
    print()

    lines = []
    while True:
        try:
            line = input("  > ")
        except EOFError:
            break
        if line.strip().lower() == "c" and not lines:
            print("  ↩ 수정 취소")
            return False
        if line == "":
            break
        lines.append(line)

    if not lines:
        print("  ↩ 입력 없음 — 수정 취소")
        return False

    new_text = "\n".join(lines)
    entry.new_korean = new_text
    entry.modified = True
    print(f"  ✅ 수정 완료")
    return True


def search_entries(entries: List[Entry], query: str) -> List[int]:
    """검색어가 포함된 항목의 인덱스 리스트를 반환한다."""
    query_lower = query.lower()
    results = []
    for i, e in enumerate(entries):
        if (query_lower in e.english.lower() or
            query_lower in e.display_korean.lower() or
            query_lower in e.contentuid.lower()):
            results.append(i)
    return results


# ==========================================
# [키 입력] msvcrt 기반 단일 키 입력
# ==========================================
def get_key() -> str:
    """키 하나를 입력받아 반환한다."""
    while True:
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            return ch
        # CPU 부하 방지
        import time
        time.sleep(0.01)


# ==========================================
# [메인 루프] 검수 실행
# ==========================================
def run_reviewer(divine_path: str, pak_path: str) -> None:
    pak = Path(pak_path)
    if not pak.exists():
        print(f"  ❌ pak 파일을 찾을 수 없습니다: {pak}")
        return

    if not check_divine_exe(divine_path):
        return

    # 1. 언팩
    temp_dir = pak.parent / f"_reviewer_temp_{pak.stem}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    print(f"  📦 pak 파일 언팩 중... ({pak.name})")
    if not divine_extract(divine_path, pak, temp_dir):
        return

    # 2. XML 로드
    print("  📖 XML 파일 로드 중...")
    review_files = load_review_files(temp_dir)

    if not review_files:
        print("  ⚠️ English/Korean 쌍이 있는 Localization 폴더를 찾지 못했습니다.")
        print("     이 pak 파일에 English와 Korean 폴더가 모두 있는지 확인하세요.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return

    # 모든 파일의 항목을 하나의 리스트로 합치기
    all_entries: List[Entry] = []
    entry_file_map: List[str] = []  # 각 항목이 어느 파일에 속하는지
    for rf in review_files:
        for entry in rf.entries:
            all_entries.append(entry)
            entry_file_map.append(rf.filename)

    total = len(all_entries)
    print(f"  ✅ {len(review_files)}개 파일, 총 {total}개 항목 로드 완료")
    print()
    print("  아무 키나 누르면 검수를 시작합니다...")
    get_key()

    # 3. 검수 루프
    current = 0
    show_modified_only = False
    filtered_indices: Optional[List[int]] = None  # 필터링된 인덱스 리스트

    def get_view_indices() -> List[int]:
        if show_modified_only:
            return [i for i, e in enumerate(all_entries) if e.modified]
        return list(range(total))

    while True:
        view = get_view_indices()
        if not view:
            clear_screen()
            if show_modified_only:
                print("\n  수정된 항목이 없습니다. 'm'을 눌러 전체 보기로 전환하세요.")
            else:
                print("\n  항목이 없습니다.")
            key = get_key()
            if key == "m":
                show_modified_only = not show_modified_only
                current = 0
                continue
            elif key in ("q", "s"):
                pass  # 아래에서 처리
            else:
                continue

        # current가 범위를 벗어나지 않도록
        if current >= len(view):
            current = len(view) - 1
        if current < 0:
            current = 0

        real_idx = view[current]
        entry = all_entries[real_idx]
        filename = entry_file_map[real_idx]
        modified_count = sum(1 for e in all_entries if e.modified)

        display_entry(entry, current, len(view), filename,
                      modified_count, show_modified_only)

        key = get_key()

        if key in (" ", "\r", "\n"):  # 스페이스 또는 엔터: 다음
            if current < len(view) - 1:
                current += 1

        elif key == "b":  # 이전
            if current > 0:
                current -= 1

        elif key == "e":  # 수정
            edit_entry(entry)
            # 수정 후 아무 키나 누르면 복귀
            if entry.modified:
                print("  아무 키나 누르면 계속...")
                get_key()

        elif key == "g":  # 번호로 이동
            print()
            try:
                num = input(f"  이동할 번호 (1-{len(view)}): ")
                n = int(num)
                if 1 <= n <= len(view):
                    current = n - 1
                else:
                    print("  ⚠️ 범위를 벗어났습니다.")
                    get_key()
            except (ValueError, EOFError):
                pass

        elif key == "/":  # 검색
            print()
            try:
                query = input("  검색어: ")
            except EOFError:
                query = ""
            if query.strip():
                results = search_entries(all_entries, query.strip())
                if results:
                    # 필터링된 결과에서 현재 view에 해당하는 것 찾기
                    view_set = set(view)
                    matched_in_view = [i for i in results if i in view_set]
                    if matched_in_view:
                        # view 안에서의 위치로 변환
                        current = view.index(matched_in_view[0])
                        print(f"  🔍 {len(matched_in_view)}개 발견. 첫 번째로 이동합니다.")
                    else:
                        print(f"  🔍 {len(results)}개 발견 (현재 보기 밖). 필터를 해제하세요.")
                else:
                    print("  🔍 검색 결과 없음")
                get_key()

        elif key == "m":  # 수정된 항목만 보기 토글
            show_modified_only = not show_modified_only
            current = 0

        elif key == "s":  # 저장 후 종료
            modified_count = sum(1 for e in all_entries if e.modified)
            if modified_count == 0:
                clear_screen()
                print("\n  수정된 항목이 없습니다. 저장할 내용이 없습니다.")
                print("  아무 키나 누르면 종료합니다...")
                get_key()
                break

            clear_screen()
            print(f"\n  💾 {modified_count}개 항목 저장 중...")

            # Korean XML 파일 업데이트
            for rf in review_files:
                save_modified_xml(rf)

            # 리팩
            print(f"  📦 pak 파일 리팩 중...")
            if divine_repack(divine_path, temp_dir, pak):
                print(f"  ✅ 저장 완료: {pak.name}")
                print(f"     ({modified_count}개 항목 수정됨)")
            else:
                print("  ❌ 리팩 실패. 수정된 XML은 임시 폴더에 남아있습니다:")
                print(f"     {temp_dir}")
                input("\n  엔터를 누르면 종료합니다...")
                return

            # 임시 폴더 정리
            shutil.rmtree(temp_dir, ignore_errors=True)
            print()
            input("  엔터를 누르면 종료합니다...")
            return

        elif key == "q":  # 저장 없이 종료
            modified_count = sum(1 for e in all_entries if e.modified)
            if modified_count > 0:
                clear_screen()
                print(f"\n  ⚠️ 수정된 항목 {modified_count}개가 저장되지 않습니다.")
                print("  정말 종료할까요? (y: 종료 / 다른 키: 돌아가기)")
                confirm = get_key()
                if confirm.lower() != "y":
                    continue
            break

    # 임시 폴더 정리
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==========================================
# [pak 선택] 폴더 안의 pak 목록에서 선택
# ==========================================
def select_pak_from_folder(folder_path: str) -> str:
    """폴더 안의 .pak 파일 목록을 보여주고 번호로 선택받는다."""
    folder = Path(folder_path)
    pak_files = sorted(folder.glob("*.pak"))
    if not pak_files:
        print(f"  ⚠️ 해당 폴더에 .pak 파일이 없습니다: {folder}")
        return ""

    print(f"  📂 {folder.name}/ 안의 pak 파일 ({len(pak_files)}개):")
    print()
    for i, p in enumerate(pak_files, 1):
        # 파일 크기 표시
        size_mb = p.stat().st_size / (1024 * 1024)
        print(f"    {i:3d}. {p.name}  ({size_mb:.1f} MB)")
    print()

    while True:
        try:
            choice = input(f"  번호를 입력하세요 (1-{len(pak_files)}, q=취소): ").strip()
        except EOFError:
            return ""
        if choice.lower() == "q":
            return ""
        try:
            n = int(choice)
            if 1 <= n <= len(pak_files):
                return str(pak_files[n - 1])
        except ValueError:
            pass
        print("  ⚠️ 올바른 번호를 입력하세요.")


# ==========================================
# [설정] 실행 시 설정값 확인/입력
# ==========================================
def setup_config() -> Tuple[str, str]:
    divine = DIVINE_EXE.strip()
    pak = TARGET_PAK.strip()

    # 드래그 앤 드롭: pak 파일을 스크립트 위에 끌어놓으면 sys.argv[1]로 전달됨
    if len(sys.argv) > 1:
        arg = sys.argv[1].strip().strip('"')
        if arg.lower().endswith(".pak") and os.path.isfile(arg):
            pak = arg
            print(f"  📎 드래그 앤 드롭으로 파일을 받았습니다: {Path(arg).name}")
            print()

    if not divine:
        print("  Divine.exe 경로를 입력하세요")
        print("  (예: C:\\ExportTool\\Packed\\Tools\\Divine.exe)")
        divine = input("  > ").strip().strip('"')
        print()

    if not pak:
        print("  검수할 .pak 파일 경로 또는 폴더 경로를 입력하세요")
        print("  (폴더를 입력하면 안의 pak 목록에서 선택할 수 있습니다)")
        print()
        print("  💡 팁: .pak 파일을 이 스크립트 위에 드래그 앤 드롭해도 됩니다!")
        print()
        user_input = input("  > ").strip().strip('"')

        if os.path.isdir(user_input):
            pak = select_pak_from_folder(user_input)
        else:
            pak = user_input
        print()

    return divine, pak


# ==========================================
# [실행] 메인 진입점
# ==========================================
if __name__ == "__main__":
    print("=" * 60)
    print("   BG3 모드 번역 검수 도구 v2.2")
    print("=" * 60)
    print()
    print("  한글화된 모드의 번역을 검수하고 수정하는 도구입니다.")
    print("  English/Korean을 비교하면서 오역을 수정할 수 있습니다.")
    print()

    divine_path, pak_path = setup_config()

    if not pak_path:
        print("  ❌ pak 파일이 선택되지 않았습니다.")
        input("  엔터를 누르면 종료합니다...")
        sys.exit(1)

    print(f"  Divine.exe: {divine_path}")
    print(f"  대상 pak : {pak_path}")
    print()
    input("  엔터를 누르면 시작합니다... ")
    print()

    run_reviewer(divine_path, pak_path)
