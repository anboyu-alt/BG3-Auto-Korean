# BG3 "Not Found" 일괄 수리 도구 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 한글화된 BG3 모드 pak들을 폴더에서 자동 감지해, "Not Found"를 유발하는 깨진/누락 핸들을 오프라인(재escape + English backfill)으로 일괄 수리한다.

**Architecture:** 순수 로직(`bg3core/repair.py`)과 divine 오케스트레이션(`bg3_repair_notfound.py`)을 분리한다. 핵심 수리는 문자열→문자열 순수 함수 `repair_xml_text`로 구현해 전수 단위 테스트한다. divine 추출/패킹과 기존 정규식·escape 함수는 재사용한다.

**Tech Stack:** Python 3, stdlib(`re`, `xml.etree.ElementTree`, `argparse`, `subprocess`, `shutil`, `pathlib`, `dataclasses`), pytest, LSLib Divine.exe.

설계 문서: `docs/superpowers/specs/2026-06-06-bg3-notfound-repair-design.md`

---

## File Structure

- **Create `bg3core/repair.py`** — 순수 수리 로직. `RepairResult`, `parse_content_blocks`, `base_stem`, `has_korean_localization`, `repair_xml_text` + 내부 헬퍼. 의존: `bg3core.constants`(정규식), `bg3core.translate`(escape). pipeline/mcm/divine 비의존.
- **Modify `bg3core/divine.py`** — `list_package()` 얇은 래퍼 추가(전체 추출 없이 엔트리 목록).
- **Create `bg3_repair_notfound.py`** — CLI. 후보 선별 → 내용 감지 → pak별 추출/수리/백업/재패킹 → 리포트. 런타임에만 `bg3core.pipeline` 헬퍼 사용.
- **Create `tests/test_repair.py`** — `repair.py` 순수 함수 단위 테스트.

테스트 실행은 저장소 루트에서 `pytest`(기존 `tests/conftest.py`가 import 경로 설정).

---

## Task 1: repair.py 골격 — 순수 헬퍼 4종

**Files:**
- Create: `bg3core/repair.py`
- Test: `tests/test_repair.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_repair.py`:

```python
from bg3core.repair import (
    RepairResult, parse_content_blocks, base_stem, has_korean_localization,
)


def test_parse_content_blocks_basic():
    text = ('<content contentuid="h1" version="1">A</content>'
            '<content contentuid="h2">B</content>')
    blocks = parse_content_blocks(text)
    assert set(blocks) == {"h1", "h2"}
    assert blocks["h1"] == '<content contentuid="h1" version="1">A</content>'


def test_parse_content_blocks_self_closing():
    text = '<content contentuid="h3" version="1"/>'
    blocks = parse_content_blocks(text)
    assert "h3" in blocks


def test_base_stem_variants():
    assert base_stem("Foo.xml") == "Foo"
    assert base_stem("english.loca.xml") == "english"
    assert base_stem("english.loca") == "english"
    assert base_stem("Bar") == "Bar"


def test_has_korean_localization_true():
    entries = ["Mods/Foo/Localization/English/Foo.xml",
               "Mods/Foo/Localization/Korean/Foo.xml"]
    assert has_korean_localization(entries) is True


def test_has_korean_localization_backslash():
    assert has_korean_localization(["Mods\\Foo\\Localization\\Korean\\Foo.loca"]) is True


def test_has_korean_localization_false():
    entries = ["Mods/Foo/Localization/English/Foo.xml", "Public/Foo/Stats/x.txt"]
    assert has_korean_localization(entries) is False


def test_repair_result_defaults():
    r = RepairResult("x", False, 0, 0)
    assert r.unfixable == []
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_repair.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bg3core.repair'`

- [ ] **Step 3: 최소 구현**

`bg3core/repair.py`:

```python
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .constants import CONTENT_BLOCK_RE, CONTENT_INNER_RE, CONTENTUID_RE
from .translate import escape_unescaped_angle_brackets


@dataclass
class RepairResult:
    new_text: str
    changed: bool
    reescaped: int
    backfilled: int
    unfixable: List[Tuple[str, str]] = field(default_factory=list)


def parse_content_blocks(text: str) -> Dict[str, str]:
    """{contentuid: 전체 <content> 블록} 매핑. contentuid 없는 블록은 무시."""
    blocks: Dict[str, str] = {}
    for block in CONTENT_BLOCK_RE.findall(text):
        m = CONTENTUID_RE.search(block)
        if m:
            blocks[m.group(1)] = block
    return blocks


def base_stem(name: str) -> str:
    """파일명에서 .xml / .loca.xml / .loca 확장자를 제거한 베이스 스템."""
    low = name.lower()
    if low.endswith(".loca.xml"):
        return name[: -len(".loca.xml")]
    if low.endswith(".xml"):
        return name[: -len(".xml")]
    if low.endswith(".loca"):
        return name[: -len(".loca")]
    return name


def has_korean_localization(entries: List[str]) -> bool:
    """list-package 엔트리 목록에 Localization/.../Korean 경로가 있으면 True."""
    for e in entries:
        el = e.lower().replace("\\", "/")
        if "localization/" in el and "/korean/" in el:
            return True
    return False
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_repair.py -v`
Expected: PASS (7개)

- [ ] **Step 5: 커밋**

```bash
git add bg3core/repair.py tests/test_repair.py
git commit -m "feat(repair): add content-block parsing and detection helpers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: repair_xml_text — 재escape + XML 검증 (English 없는 경로)

**Files:**
- Modify: `bg3core/repair.py`
- Test: `tests/test_repair.py`

- [ ] **Step 1: 실패 테스트 작성** (`tests/test_repair.py`에 추가)

```python
import xml.etree.ElementTree as ET
from bg3core.repair import repair_xml_text

VALID = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
         '<content contentuid="h1" version="1">안녕</content>\n</contentList>\n')


def _assert_valid_xml(text):
    ET.fromstring(text.encode("utf-8"))  # raises if invalid


def test_clean_korean_unchanged():
    r = repair_xml_text(VALID, None)
    assert r.changed is False
    assert r.reescaped == 0


def test_raw_angle_brackets_fixed():
    broken = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
              '<content contentuid="h1" version="1">2d6 <화염> 피해</content>\n'
              '</contentList>\n')
    r = repair_xml_text(broken, None)
    assert r.changed is True
    assert r.reescaped == 1
    assert "&lt;화염&gt;" in r.new_text
    _assert_valid_xml(r.new_text)


def test_raw_ampersand_fixed():
    broken = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
              '<content contentuid="h1" version="1">[3] & [4]</content>\n'
              '</contentList>\n')
    r = repair_xml_text(broken, None)
    assert "&amp;" in r.new_text
    assert r.changed is True
    _assert_valid_xml(r.new_text)


def test_valid_entities_and_lstag_preserved():
    text = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
            '<content contentuid="h1" version="1">'
            '&lt;LSTag Tooltip="x"&gt;효과&lt;/LSTag&gt; &amp; 끝</content>\n'
            '</contentList>\n')
    r = repair_xml_text(text, None)
    assert r.changed is False
    assert "&lt;LSTag" in r.new_text and "&amp;" in r.new_text


def test_idempotent():
    broken = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
              '<content contentuid="h1" version="1">a <b> c</content>\n'
              '</contentList>\n')
    r1 = repair_xml_text(broken, None)
    r2 = repair_xml_text(r1.new_text, None)
    assert r1.changed is True
    assert r2.changed is False


def test_unparseable_reported_not_written():
    broken = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
              '<content contentuid="h1" version="1">ok</content>\n'
              '<content >dangling')  # 닫힘 태그/루트 닫힘 없음
    r = repair_xml_text(broken, None)
    assert r.changed is False
    assert r.new_text == broken
    assert any("parse" in reason for _, reason in r.unfixable)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_repair.py -k "clean_korean or angle or ampersand or entities or idempotent or unparseable" -v`
Expected: FAIL — `ImportError: cannot import name 'repair_xml_text'`

- [ ] **Step 3: 구현 추가** (`bg3core/repair.py` 끝에 추가)

```python
def _reescape_inner(text: str) -> Tuple[str, int]:
    """각 <content>의 inner에만 escape_unescaped_angle_brackets 적용. (open/close/uid 보존)"""
    count = 0

    def repl(m: "re.Match") -> str:
        nonlocal count
        open_tag, inner, close = m.group(1), m.group(2), m.group(3)
        fixed = escape_unescaped_angle_brackets(inner)
        if fixed != inner:
            count += 1
        return open_tag + fixed + close

    return CONTENT_INNER_RE.sub(repl, text), count


# 안전한 XML 파서: 가능하면 defusedxml(외부 엔티티·billion-laughs 차단), 없으면 stdlib 폴백.
try:
    from defusedxml.ElementTree import fromstring as _xml_fromstring
except ImportError:  # defusedxml 미설치 시 stdlib 폴백
    from xml.etree.ElementTree import fromstring as _xml_fromstring


def _is_valid_xml(text: str) -> bool:
    # 검증 전용 프로브: 파싱 실패·위험 엔티티 등 어떤 예외든 '무효'로 보고 원본을 보존,
    # 상위에서 unfixable로 기록한다(에러 은폐가 아니라 의도된 분기).
    try:
        _xml_fromstring(text.encode("utf-8"))  # bytes → XML 선언 인코딩 문제 회피
        return True
    except Exception:
        return False


def repair_xml_text(korean_text: str, english_text: Optional[str]) -> RepairResult:
    """깨진 Korean loca XML을 오프라인 수리한다.

    1) 각 <content> inner 재escape (원인 1 복구)
    2) XML 파싱 검증 — 실패하면 원본 유지 + unfixable
    3) (english_text 있으면) 누락 핸들을 English 블록으로 backfill — Task 3
    """
    reescaped_text, reescaped = _reescape_inner(korean_text)

    if not _is_valid_xml(reescaped_text):
        return RepairResult(korean_text, False, 0, 0,
                            [("<file>", "xml_parse_failed_after_reescape")])

    new_text = reescaped_text
    changed = new_text != korean_text
    return RepairResult(new_text, changed, reescaped, 0, [])
```

**의존성 추가 (보안 강화):** `requirements-gui.txt`에 `defusedxml` 한 줄을 추가하고 `pip install defusedxml` 실행. 미설치 시에도 stdlib로 폴백 동작하지만, 서드파티 mod XML을 파싱하므로 설치를 권장한다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_repair.py -v`
Expected: PASS (전체)

- [ ] **Step 5: 커밋**

```bash
git add bg3core/repair.py tests/test_repair.py
git commit -m "feat(repair): reescape content inners and validate XML

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: repair_xml_text — English backfill

**Files:**
- Modify: `bg3core/repair.py`
- Test: `tests/test_repair.py`

- [ ] **Step 1: 실패 테스트 작성** (`tests/test_repair.py`에 추가)

```python
def test_backfill_missing_handle_preserves_version():
    english = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
               '<content contentuid="h1" version="3">Sword</content>\n'
               '<content contentuid="h2" version="2">Shield</content>\n'
               '</contentList>\n')
    korean = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
              '<content contentuid="h1" version="3">검</content>\n'
              '</contentList>\n')
    r = repair_xml_text(korean, english)
    assert r.backfilled == 1
    assert r.changed is True
    assert 'contentuid="h2" version="2"' in r.new_text
    assert "Shield" in r.new_text
    _assert_valid_xml(r.new_text)


def test_backfill_idempotent():
    english = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
               '<content contentuid="h1" version="1">Sword</content>\n'
               '<content contentuid="h2" version="1">Shield</content>\n'
               '</contentList>\n')
    korean = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
              '<content contentuid="h1" version="1">검</content>\n'
              '</contentList>\n')
    r1 = repair_xml_text(korean, english)
    r2 = repair_xml_text(r1.new_text, english)
    assert r1.backfilled == 1
    assert r2.changed is False


def test_backfill_skips_korean_mirror_source():
    english = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
               '<content contentuid="h2" version="1">'
               '이미 한국어로 덮인 긴 텍스트입니다</content>\n</contentList>\n')
    korean = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
              '<content contentuid="h1" version="1">검</content>\n</contentList>\n')
    r = repair_xml_text(korean, english)
    assert r.backfilled == 0
    assert any(uid == "h2" for uid, _ in r.unfixable)


def test_no_backfill_when_complete():
    english = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
               '<content contentuid="h1" version="1">Sword</content>\n</contentList>\n')
    korean = ('<?xml version="1.0" encoding="utf-8"?>\n<contentList>\n'
              '<content contentuid="h1" version="1">검</content>\n</contentList>\n')
    r = repair_xml_text(korean, english)
    assert r.changed is False
    assert r.backfilled == 0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_repair.py -k backfill -v`
Expected: FAIL — `assert r.backfilled == 1` 등 (현재 backfill 미구현 → 0)

- [ ] **Step 3: 구현 — backfill 로직 추가**

`bg3core/repair.py`에 헬퍼 추가:

```python
_INNER_RE = re.compile(r">([^<]*)</content>", re.IGNORECASE)
_CONTENTLIST_CLOSE_RE = re.compile(r"</contentList>", re.IGNORECASE)


def _looks_korean(block: str) -> bool:
    """블록 inner가 한국어로 채워졌는지(=영어 원천이 미러로 덮였는지) 휴리스틱."""
    m = _INNER_RE.search(block)
    inner = m.group(1) if m else ""
    clean = re.sub(r"&[a-zA-Z]+;", "", inner)
    clean = re.sub(r"\s+", "", clean)
    if len(clean) < 6:
        return False
    korean = sum(1 for c in clean if "가" <= c <= "힣")
    return korean / len(clean) >= 0.3
```

그리고 `repair_xml_text`의 `new_text = reescaped_text` 이후, `changed = ...` 이전을 아래로 교체:

```python
    new_text = reescaped_text
    backfilled = 0
    unfixable: List[Tuple[str, str]] = []

    if english_text:
        kor_blocks = parse_content_blocks(reescaped_text)
        eng_blocks = parse_content_blocks(english_text)
        to_insert: List[str] = []
        for uid, block in eng_blocks.items():
            if uid in kor_blocks:
                continue
            if _looks_korean(block):
                unfixable.append((uid, "english_source_is_korean_mirror"))
                continue
            to_insert.append(block)
        if to_insert:
            m = _CONTENTLIST_CLOSE_RE.search(new_text)
            if m:
                insertion = "\n" + "\n".join(to_insert) + "\n"
                candidate = new_text[: m.start()] + insertion + new_text[m.start():]
                if _is_valid_xml(candidate):
                    new_text = candidate
                    backfilled = len(to_insert)
                else:
                    unfixable.append(("<file>", "backfill_broke_xml"))
            else:
                for block in to_insert:
                    cm = CONTENTUID_RE.search(block)
                    unfixable.append((cm.group(1) if cm else "?", "no_contentlist_close_tag"))

    changed = new_text != korean_text
    return RepairResult(new_text, changed, reescaped, backfilled, unfixable)
```

(기존 `return RepairResult(new_text, changed, reescaped, 0, [])` 줄은 삭제한다.)

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_repair.py -v`
Expected: PASS (전체)

- [ ] **Step 5: 커밋**

```bash
git add bg3core/repair.py tests/test_repair.py
git commit -m "feat(repair): backfill missing handles from English source

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: divine.list_package 래퍼

**Files:**
- Modify: `bg3core/divine.py`

- [ ] **Step 1: 구현 추가** (`bg3core/divine.py` 끝에 추가)

```python
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
```

- [ ] **Step 2: import 무결성 확인**

Run: `python -c "from bg3core.divine import list_package; print('ok')"`
Expected: `ok`

- [ ] **Step 3: 커밋**

```bash
git add bg3core/divine.py
git commit -m "feat(divine): add list_package wrapper for content detection

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

> 참고: `list_package`는 divine 의존이라 단위 테스트 대신 Task 6의 실제 `--dry-run`에서 검증한다. 출력 각 줄에 경로가 포함되며 `has_korean_localization`이 부분 문자열로 판정하므로 접두 컬럼(크기 등)이 있어도 동작한다.

---

## Task 5: CLI 오케스트레이션 — bg3_repair_notfound.py

**Files:**
- Create: `bg3_repair_notfound.py`

- [ ] **Step 1: CLI 전체 구현**

`bg3_repair_notfound.py`:

```python
#!/usr/bin/env python3
"""BG3 한글화 모드 'Not Found' 일괄 수리 CLI.

Mods 폴더에서 한글화된 pak을 자동 감지해, 깨진/누락 핸들을 오프라인으로 수리한다.
사용 예:
  python bg3_repair_notfound.py --mods "C:\\...\\Mods" --divine "C:\\...\\Divine.exe" --dry-run
"""
import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from bg3core.divine import (
    check_divine_exe, divine_extract, convert_loca_to_xml,
    strip_loca_artifacts, divine_repack, list_package,
)
from bg3core.repair import repair_xml_text, has_korean_localization, base_stem


def iter_candidates(mods_dir: Path, since: datetime, include_all: bool):
    for pak in sorted(mods_dir.glob("*.pak")):
        if include_all or datetime.fromtimestamp(pak.stat().st_mtime) >= since:
            yield pak


def build_english_map(src_dir):
    out = {}
    if src_dir and src_dir.exists():
        for f in src_dir.iterdir():
            if f.is_file() and f.name.lower().endswith(".xml"):
                out[base_stem(f.name)] = f
    return out


def process_pak(pak: Path, divine_path: str, work_root: Path,
                backup_dir: Path, dry_run: bool) -> dict:
    from bg3core.pipeline import find_localization_folders, list_source_language_dirs

    temp_dir = work_root / pak.stem
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

    result = {"name": pak.name, "status": "clean", "reescaped": 0,
              "backfilled": 0, "unfixable": [], "note": ""}
    try:
        if not divine_extract(divine_path, pak, temp_dir):
            result["status"] = "failed"
            result["note"] = "extract_failed"
            return result
        convert_loca_to_xml(divine_path, temp_dir)

        changed_any = False
        for loc in find_localization_folders(temp_dir):
            korean_dir = loc / "Korean"
            if not korean_dir.exists():
                continue
            src_dirs = list_source_language_dirs(loc)
            eng_map = build_english_map(src_dirs[0]) if src_dirs else {}
            for kfile in korean_dir.glob("*.xml"):
                eng_file = eng_map.get(base_stem(kfile.name))
                eng_text = eng_file.read_text(encoding="utf-8", errors="replace") if eng_file else None
                ktext = kfile.read_text(encoding="utf-8", errors="replace")
                rr = repair_xml_text(ktext, eng_text)
                result["reescaped"] += rr.reescaped
                result["backfilled"] += rr.backfilled
                for uid, reason in rr.unfixable:
                    result["unfixable"].append(
                        {"file": kfile.name, "contentuid": uid, "reason": reason})
                if rr.changed:
                    changed_any = True
                    if not dry_run:
                        kfile.write_text(rr.new_text, encoding="utf-8")

        if not changed_any:
            result["status"] = "clean"
        elif dry_run:
            result["status"] = "would-repair"
        else:
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / pak.name
            if not backup_path.exists():
                shutil.copy2(pak, backup_path)
            strip_loca_artifacts(temp_dir)
            temp_out = work_root / (pak.stem + "_repaired.pak")
            if divine_repack(divine_path, temp_dir, temp_out):
                shutil.move(str(temp_out), str(pak))
                result["status"] = "repaired"
            else:
                result["status"] = "failed"
                result["note"] = "repack_failed"
    except Exception as e:  # pak 단위 격리
        result["status"] = "failed"
        result["note"] = f"exception: {e}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return result


def write_report(report_path: Path, summary: dict, results: list):
    report = {"summary": summary, "paks": results}
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md = [f"# 수리 리포트 {summary['generated']}", "",
          f"- dry_run: {summary['dry_run']}",
          (f"- 후보 {summary['candidates']} / 번역본 {summary['translated']} / "
           f"수리 {summary['repaired']} / clean {summary['clean']} / 실패 {summary['failed']}"),
          "", "## 수리·문제 pak"]
    for r in results:
        if r["status"] in ("repaired", "would-repair", "failed") or r["unfixable"]:
            md.append(f"- **{r['name']}** — {r['status']} "
                      f"(reescaped={r['reescaped']}, backfilled={r['backfilled']}, "
                      f"unfixable={len(r['unfixable'])}) {r['note']}")
    report_path.with_suffix(".md").write_text("\n".join(md), encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description="BG3 한글화 모드 Not Found 일괄 수리")
    p.add_argument("--mods", required=True, help="Mods 폴더 경로")
    p.add_argument("--divine", required=True, help="Divine.exe 경로")
    p.add_argument("--since", default="2026-03-01", help="mtime 후보 필터 (YYYY-MM-DD)")
    p.add_argument("--all", action="store_true", help="날짜 필터 무시(전체 후보)")
    p.add_argument("--dry-run", action="store_true", help="쓰기 없이 리포트만")
    p.add_argument("--backup-dir", default=None)
    p.add_argument("--report", default=None)
    p.add_argument("--work-dir", default=None)
    args = p.parse_args()

    if not check_divine_exe(args.divine):
        sys.exit(1)
    mods = Path(args.mods)
    if not mods.is_dir():
        print(f"❌ Mods 폴더 없음: {mods}")
        sys.exit(1)

    since = datetime.strptime(args.since, "%Y-%m-%d")
    today = datetime.now().strftime("%Y%m%d")
    backup_dir = Path(args.backup_dir) if args.backup_dir else mods.parent / f"Mods_backup_{today}"
    report_path = Path(args.report) if args.report else Path.cwd() / f"repair_report_{today}.json"
    work_root = Path(args.work_dir) if args.work_dir else Path(tempfile.gettempdir()) / "bg3_repair"
    work_root.mkdir(parents=True, exist_ok=True)

    candidates = list(iter_candidates(mods, since, args.all))
    print(f"후보 pak: {len(candidates)}개 (필터: {'전체' if args.all else '>= ' + args.since})")

    results, translated = [], 0
    for i, pak in enumerate(candidates, 1):
        if not has_korean_localization(list_package(args.divine, pak)):
            continue
        translated += 1
        print(f"[{i}/{len(candidates)}] 🔧 {pak.name}")
        r = process_pak(pak, args.divine, work_root, backup_dir, args.dry_run)
        print(f"    → {r['status']} (reescaped={r['reescaped']}, "
              f"backfilled={r['backfilled']}, unfixable={len(r['unfixable'])})")
        results.append(r)

    summary = {
        "generated": today, "dry_run": args.dry_run,
        "candidates": len(candidates), "translated": translated,
        "repaired": sum(1 for r in results if r["status"] in ("repaired", "would-repair")),
        "clean": sum(1 for r in results if r["status"] == "clean"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "unfixable_paks": sum(1 for r in results if r["unfixable"]),
    }
    write_report(report_path, summary, results)
    print(f"\n✅ 완료. 리포트: {report_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: import·인자 파싱 무결성 확인**

Run: `python bg3_repair_notfound.py --help`
Expected: usage 출력(에러 없이). 인자 목록에 `--mods --divine --since --all --dry-run --backup-dir --report --work-dir` 표시.

- [ ] **Step 3: 커밋**

```bash
git add bg3_repair_notfound.py
git commit -m "feat: add bg3_repair_notfound CLI orchestration

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: 실제 폴더 dry-run 검증 → 실수리

**Files:** (코드 변경 없음 — 운영 검증)

- [ ] **Step 1: 전체 테스트 재확인**

Run: `pytest tests/test_repair.py -v`
Expected: PASS (전체)

- [ ] **Step 2: 실제 Mods 폴더 dry-run**

Run (경로는 사용자 환경에 맞게):
```
python bg3_repair_notfound.py ^
  --mods "C:\Users\anboy\AppData\Local\Larian Studios\Baldur's Gate 3\Mods" ^
  --divine "<Divine.exe 경로>" ^
  --dry-run
```
Expected: `repair_report_<날짜>.json/.md` 생성. 콘솔에 후보 수(≈237)·번역본 수·`would-repair`/`clean`/`unfixable` 요약 출력. **어떤 pak도 변경되지 않음**(dry-run).

- [ ] **Step 3: 리포트 검토**

`repair_report_<날짜>.md`에서 `would-repair` 목록과 `unfixable` 항목 확인. unfixable이 많은 pak은 재다운로드 후보로 분류. 이상 없으면 다음 단계.

- [ ] **Step 4: 실수리 실행 (백업 후 제자리 교체)**

Run (`--dry-run` 제거):
```
python bg3_repair_notfound.py ^
  --mods "C:\Users\anboy\AppData\Local\Larian Studios\Baldur's Gate 3\Mods" ^
  --divine "<Divine.exe 경로>"
```
Expected: 원본이 `Mods_backup_<날짜>`에 복사되고, 변경된 pak만 수리본으로 교체. 요약에 `repaired` 개수 출력.

- [ ] **Step 5: 게임 내 확인**

게임을 한국어로 실행해 이전 "Not Found"가 사라졌는지 확인(최악의 경우 영어 표시). 남는 항목은 리포트의 `unfixable`과 대조.

---

## Self-Review

**1. Spec coverage**
- 내용 기반 감지 → Task 4(`list_package`) + Task 1(`has_korean_localization`) + Task 5(필터링). ✅
- 백업 후 제자리 교체 → Task 5 `process_pak`(백업 복사 → temp 재패킹 → move). ✅
- 오프라인 복구(재escape + backfill) → Task 2·3. ✅
- CLI 폼팩터 + `--dry-run` + 리포트 → Task 5. ✅
- 엣지: 파싱 실패(T2), 미러(T3), 멱등성(T2·T3), self-closing(T1), 플랫 Localization(english 없음 → reescape만, T5에서 eng_text=None 경로), `_Korean` 미포함 이름(내용 감지). ✅
- 안전: 백업/재패킹 성공 전 원본 미삭제(`shutil.move`는 재패킹 성공 후), pak 단위 try/except, temp 정리(finally). ✅

**2. Placeholder scan:** 모든 step에 실제 코드/명령/기대출력 포함. "TBD/TODO" 없음. ✅

**3. Type consistency:** `RepairResult(new_text, changed, reescaped, backfilled, unfixable)` 시그니처가 T1 정의 → T2·T3·T5 사용에서 일치. `repair_xml_text(korean_text, english_text)`·`base_stem`·`has_korean_localization`·`list_package` 이름이 정의-사용 간 동일. ✅

> 비고: `unfixable` 항목은 `repair_xml_text`에서 `(uid|"<file>", reason)` 튜플, CLI에서 `{"file","contentuid","reason"}` dict로 정규화 — 변환은 Task 5 `process_pak` 루프에서 명시적으로 수행하므로 모순 없음.
