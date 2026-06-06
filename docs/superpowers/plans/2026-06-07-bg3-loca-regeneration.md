# BG3 `.loca` 재생성 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 한글화 pak에 누락된 바이너리 `.loca`를 (멱등하게) 재생성해 게임 내 "Not Found"를 해소하고, 본 번역 파이프라인이 앞으로 `.loca`를 포함해 산출하도록 v3.7 회귀를 되돌린다.

**Architecture:** 순수 함수 `plan_loca_generation`(생성 대상 산출, 멱등)과 divine 래퍼 `ensure_loca`(실제 변환)를 `bg3core/divine.py`에 추가한다. 수리 도구(`bg3_repair_notfound.py`)와 본 파이프라인(`bg3core/pipeline.py`)에서 `strip_loca_artifacts` 호출을 `ensure_loca`로 교체한다.

**Tech Stack:** Python 3 (stdlib: `pathlib`, `subprocess`, `typing`), pytest, LSLib Divine.exe (`convert-loca`).

설계 문서: `docs/superpowers/specs/2026-06-07-bg3-loca-regeneration-design.md`

---

## File Structure

- **Modify `bg3core/divine.py`** — `plan_loca_generation(unpacked_path) -> List[Tuple[Path,Path]]`(순수) + `ensure_loca(divine_path, unpacked_path) -> int`(divine 래퍼) 추가. 기존 `strip_loca_artifacts`/`convert_xml_to_loca`는 그대로 둠(다른 테스트가 참조).
- **Create `tests/test_loca.py`** — `plan_loca_generation` 순수 단위 테스트.
- **Modify `bg3_repair_notfound.py`** — `process_pak`에서 strip 제거 + `.loca` 통합, 리포트/요약에 loca 카운트.
- **Modify `bg3core/pipeline.py`** — `process_pak_file`에서 `strip_loca_artifacts` → `ensure_loca` 교체.
- **Modify `README.md`** — v3.8 항목.

테스트는 저장소 루트에서 `pytest`(기존 `tests/conftest.py`가 import 경로 설정).

---

## Task 1: `plan_loca_generation` 순수 함수 + 테스트

**Files:**
- Modify: `bg3core/divine.py`
- Test: `tests/test_loca.py`

- [ ] **Step 1: 실패 테스트 작성** — create `tests/test_loca.py`:

```python
from pathlib import Path
from bg3core.divine import plan_loca_generation


def _mk(p: Path, content: str = "x") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_plain_xml_missing_loca(tmp_path):
    x = tmp_path / "Localization" / "Korean" / "Foo.xml"
    _mk(x)
    plan = plan_loca_generation(tmp_path)
    assert len(plan) == 1
    src, out = plan[0]
    assert src == x
    assert out == tmp_path / "Localization" / "Korean" / "Foo.loca"


def test_existing_loca_skipped(tmp_path):
    _mk(tmp_path / "Localization" / "Korean" / "Foo.xml")
    _mk(tmp_path / "Localization" / "Korean" / "Foo.loca")
    assert plan_loca_generation(tmp_path) == []


def test_dual_xml_dedup_prefers_plain(tmp_path):
    x = tmp_path / "Localization" / "Korean" / "Artificer.xml"
    lx = tmp_path / "Localization" / "Korean" / "Artificer.loca.xml"
    _mk(x)
    _mk(lx)
    plan = plan_loca_generation(tmp_path)
    assert len(plan) == 1
    src, out = plan[0]
    assert out == tmp_path / "Localization" / "Korean" / "Artificer.loca"
    assert src == x  # plain .xml preferred as source


def test_loca_xml_only(tmp_path):
    lx = tmp_path / "Localization" / "English" / "english.loca.xml"
    _mk(lx)
    plan = plan_loca_generation(tmp_path)
    assert len(plan) == 1
    src, out = plan[0]
    assert src == lx
    assert out == tmp_path / "Localization" / "English" / "english.loca"


def test_xml_outside_localization_ignored(tmp_path):
    _mk(tmp_path / "Public" / "Foo" / "meta.xml")
    _mk(tmp_path / "Mods" / "Foo" / "something.xml")
    assert plan_loca_generation(tmp_path) == []


def test_multiple_language_folders(tmp_path):
    _mk(tmp_path / "Localization" / "English" / "M.xml")
    _mk(tmp_path / "Localization" / "Korean" / "M.xml")
    plan = plan_loca_generation(tmp_path)
    outs = sorted(str(o) for _, o in plan)
    assert len(plan) == 2
    assert any("English" in o and o.endswith("M.loca") for o in outs)
    assert any("Korean" in o and o.endswith("M.loca") for o in outs)


def test_mt_gen_loca_naming(tmp_path):
    x = tmp_path / "Localization" / "Korean" / "__MT_GEN_LOCA_abc.xml"
    _mk(x)
    plan = plan_loca_generation(tmp_path)
    assert plan[0][1].name == "__MT_GEN_LOCA_abc.loca"
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `pytest tests/test_loca.py -v`
Expected: FAIL — `ImportError: cannot import name 'plan_loca_generation' from 'bg3core.divine'`

- [ ] **Step 3: 구현 추가** — `bg3core/divine.py` 상단 import에 typing 추가하고, 파일 끝에 함수 추가.

먼저 파일 맨 위 import 부분을 확인하고 `from typing import List, Tuple`가 없으면 추가:
```python
from typing import List, Tuple
```
(이미 `import os`, `import subprocess`, `from pathlib import Path`가 있음.)

그리고 파일 끝에 추가:
```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest tests/test_loca.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: 커밋**

```bash
git add bg3core/divine.py tests/test_loca.py
git commit -m "feat(divine): add idempotent plan_loca_generation (pure)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `ensure_loca` divine 래퍼

**Files:**
- Modify: `bg3core/divine.py`

- [ ] **Step 1: 구현 추가** — `bg3core/divine.py` 끝(plan_loca_generation 아래)에 추가:

```python
def ensure_loca(divine_path: str, unpacked_path: Path) -> int:
    """Localization xml 중 .loca가 없는 것을 convert-loca로 생성. 생성 개수 반환.

    plan_loca_generation으로 대상을 고른 뒤 각각 변환한다(이미 .loca 있으면 스킵 → 멱등).
    BG3는 표준 구조 모드의 로컬라이제이션을 .loca 바이너리에서 읽으므로 필수.
    """
    generated = 0
    for src_xml, out_loca in plan_loca_generation(unpacked_path):
        cmd = [
            divine_path,
            "-g", "bg3",
            "-a", "convert-loca",
            "-s", str(src_xml),
            "-d", str(out_loca),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0 and out_loca.exists():
                generated += 1
            else:
                err = (result.stderr or result.stdout or "").strip()
                if err:
                    print(f"    ⚠️ .loca 생성 실패: {src_xml.name} — {err.splitlines()[0][:200]}")
        except Exception as e:
            print(f"    ⚠️ .loca 생성 예외: {src_xml.name} — {e}")
    return generated
```

- [ ] **Step 2: import 무결성 + 기존 테스트 확인**

Run: `python -c "from bg3core.divine import ensure_loca, plan_loca_generation; print('ok')"`
Expected: `ok`

Run: `pytest tests/test_loca.py tests/test_strip_loca.py -q`
Expected: all pass (plan_loca_generation 7 + 기존 strip 테스트).

- [ ] **Step 3: 커밋**

```bash
git add bg3core/divine.py
git commit -m "feat(divine): add ensure_loca wrapper (generate missing .loca)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

> 참고: `ensure_loca`는 divine 의존이라 단위 테스트 대신 Task 6의 실제 dry-run/스윕에서 검증한다.

---

## Task 3: 수리 도구에 `.loca` 통합 (strip 제거)

**Files:**
- Modify: `bg3_repair_notfound.py`

- [ ] **Step 1: import 교체** — 상단 divine import에서 `strip_loca_artifacts`를 빼고 `ensure_loca`, `plan_loca_generation`을 추가.

현재:
```python
from bg3core.divine import (
    check_divine_exe, divine_extract, convert_loca_to_xml,
    strip_loca_artifacts, divine_repack, list_package,
)
```
교체:
```python
from bg3core.divine import (
    check_divine_exe, divine_extract, convert_loca_to_xml,
    divine_repack, list_package, ensure_loca, plan_loca_generation,
)
```

- [ ] **Step 2: `process_pak` 함수 전체 교체** — 현재 `process_pak` 정의를 아래로 통째 교체:

```python
def process_pak(pak: Path, divine_path: str, work_root: Path,
                backup_dir: Path, dry_run: bool) -> dict:
    from bg3core.pipeline import find_localization_folders, list_source_language_dirs

    temp_dir = work_root / pak.stem
    if temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)

    result = {"name": pak.name, "status": "clean", "reescaped": 0,
              "backfilled": 0, "loca_missing": 0, "loca_generated": 0,
              "unfixable": [], "note": ""}
    try:
        if not divine_extract(divine_path, pak, temp_dir):
            result["status"] = "failed"
            result["note"] = "extract_failed"
            return result

        # 원본 상태 기준 누락 .loca 개수(멱등성·dry-run 보고용) — convert 전에 측정
        loca_missing = len(plan_loca_generation(temp_dir))
        result["loca_missing"] = loca_missing

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

        needs = changed_any or loca_missing > 0
        if not needs:
            result["status"] = "clean"
        elif dry_run:
            result["status"] = "would-repair"
        else:
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / pak.name
            if not backup_path.exists():
                shutil.copy2(pak, backup_path)
            result["loca_generated"] = ensure_loca(divine_path, temp_dir)
            temp_out = pak.parent / (pak.name + ".repairing")
            try:
                if divine_repack(divine_path, temp_dir, temp_out):
                    os.replace(str(temp_out), str(pak))
                    result["status"] = "repaired"
                else:
                    result["status"] = "failed"
                    result["note"] = "repack_failed"
            finally:
                if temp_out.exists():
                    temp_out.unlink()
    except Exception as e:  # pak 단위 격리
        result["status"] = "failed"
        result["note"] = f"exception: {e}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    return result
```

(핵심 변경: `strip_loca_artifacts` 호출 제거, convert 전에 `loca_missing` 측정, `needs`에 loca 누락 반영, 재패킹 직전 `ensure_loca`로 `.loca` 생성.)

- [ ] **Step 3: `write_report` per-pak 라인에 loca 표기** — `write_report` 안의 md append 줄을 교체.

현재:
```python
        if r["status"] in ("repaired", "would-repair", "failed") or r["unfixable"]:
            md.append(f"- **{r['name']}** — {r['status']} "
                      f"(reescaped={r['reescaped']}, backfilled={r['backfilled']}, "
                      f"unfixable={len(r['unfixable'])}) {r['note']}")
```
교체:
```python
        if r["status"] in ("repaired", "would-repair", "failed") or r["unfixable"]:
            loca = r.get("loca_generated") or r.get("loca_missing") or 0
            md.append(f"- **{r['name']}** — {r['status']} "
                      f"(reescaped={r['reescaped']}, backfilled={r['backfilled']}, "
                      f"loca={loca}, unfixable={len(r['unfixable'])}) {r['note']}")
```

- [ ] **Step 4: `main`의 summary와 진행 출력에 loca 반영** — summary dict와 진행 print를 교체.

진행 print 현재:
```python
        print(f"    → {r['status']} (reescaped={r['reescaped']}, "
              f"backfilled={r['backfilled']}, unfixable={len(r['unfixable'])})")
```
교체:
```python
        print(f"    → {r['status']} (reescaped={r['reescaped']}, "
              f"backfilled={r['backfilled']}, "
              f"loca={r.get('loca_generated') or r.get('loca_missing') or 0}, "
              f"unfixable={len(r['unfixable'])})")
```

summary dict 현재:
```python
    summary = {
        "generated": today, "dry_run": args.dry_run,
        "candidates": len(candidates), "translated": translated,
        "repaired": sum(1 for r in results if r["status"] in ("repaired", "would-repair")),
        "clean": sum(1 for r in results if r["status"] == "clean"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "unfixable_paks": sum(1 for r in results if r["unfixable"]),
    }
```
교체:
```python
    summary = {
        "generated": today, "dry_run": args.dry_run,
        "candidates": len(candidates), "translated": translated,
        "repaired": sum(1 for r in results if r["status"] in ("repaired", "would-repair")),
        "clean": sum(1 for r in results if r["status"] == "clean"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "unfixable_paks": sum(1 for r in results if r["unfixable"]),
        "loca_generated": sum(r.get("loca_generated", 0) for r in results),
        "loca_missing": sum(r.get("loca_missing", 0) for r in results),
    }
```

- [ ] **Step 5: 무결성 확인**

Run: `python bg3_repair_notfound.py --help`
Expected: usage 출력, import 에러 없음.

Run: `pytest tests/test_repair.py tests/test_loca.py -q`
Expected: all pass (기존 repair 20 + loca 7).

- [ ] **Step 6: 커밋**

```bash
git add bg3_repair_notfound.py
git commit -m "feat(repair-cli): regenerate missing .loca instead of stripping

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: 본 파이프라인 strip → ensure_loca 교체

**Files:**
- Modify: `bg3core/pipeline.py`

- [ ] **Step 1: import 교체** — `bg3core/pipeline.py` 상단 divine import에서 `strip_loca_artifacts`를 빼고 `ensure_loca` 추가.

현재:
```python
from .divine import check_divine_exe, divine_extract, convert_loca_to_xml, strip_loca_artifacts, divine_repack
```
교체:
```python
from .divine import check_divine_exe, divine_extract, convert_loca_to_xml, ensure_loca, divine_repack
```

- [ ] **Step 2: 패킹 직전 호출 교체** — `process_pak_file` 안의 strip 블록을 교체.

현재:
```python
    # .loca 바이너리와 .loca.xml 보조 파일 제거 — BG3 모드는 .xml만으로 작동.
    # 영문 .loca/.loca.xml이 남아 있으면 한국어 폴더의 한글 .xml을 가릴 위험이 있다.
    stripped = strip_loca_artifacts(temp_dir)
    if stripped > 0:
        _log(f"  🧹 .loca/.loca.xml 정리: {stripped}개 (.xml만 남김)")
```
교체:
```python
    # BG3는 표준 구조 모드의 로컬라이제이션을 .loca 바이너리에서 읽는다.
    # 번역된 xml에서 각 언어 .loca를 생성해 포함시킨다(없는 것만 — 멱등).
    generated = ensure_loca(divine_path, temp_dir)
    if generated > 0:
        _log(f"  🧩 .loca 생성: {generated}개")
```

- [ ] **Step 3: 무결성 확인**

Run: `python -c "import bg3core.pipeline; print('ok')"`
Expected: `ok`

Run: `pytest -q tests/test_loca.py tests/test_repair.py tests/test_strip_loca.py`
Expected: all pass (strip 함수는 divine.py에 남아 있어 test_strip_loca 정상).

- [ ] **Step 4: 커밋**

```bash
git add bg3core/pipeline.py
git commit -m "fix(pipeline): generate .loca on pack instead of stripping (v3.7 regression)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: README v3.8 + 전체 테스트

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 버전 이력에 v3.8 추가** — `README.md`의 `## 업데이트 이력` 바로 아래(맨 위 항목으로) 삽입:

```markdown
### v3.8
- **`.loca` 재생성 복원 (v3.7 회귀 수정)**: BG3는 표준 구조(`Localization/<언어>/`) 모드의 로컬라이제이션을 **`.loca` 바이너리에서 읽는다.** v3.7이 `.loca` 생성을 없애고 `.xml`만 남기면서, 게임이 읽을 로컬라이제이션이 없어 다수 모드의 아이템·클래스 이름이 "Not Found"로 표시되는 회귀가 있었다. 이제 패킹 직전에 번역된 각 언어 xml에서 `.loca`를 생성(없는 것만, 멱등)해 포함한다. v3.7이 우려한 "영문이 한글을 가림"은 언어별 `.loca`를 생성하면 발생하지 않음을 게임 실측으로 확인.
- **기존 모드 일괄 복구**: `bg3_repair_notfound.py`가 `.loca` 없는 번역본을 감지해 재생성·재패킹(재번역·재다운로드 불필요). `--dry-run`으로 먼저 점검 가능.
```

- [ ] **Step 2: 한글화 원리 섹션의 v3.7 설명 정정** — `README.md`에서 v3.7이 `.loca`를 불필요하다고 한 설명 문단(`.loca` 바이너리 역생성 / `.xml`만 패킹 관련)이 있으면, 그 옆/아래에 한 줄 주석 추가:

```markdown
> ⚠️ 정정(v3.8): 위 v3.7의 "`.xml`만으로 작동" 판단은 표준 구조 모드에서 틀렸다. 게임은 `.loca`를 읽으므로 v3.8에서 `.loca` 생성을 복원했다.
```
(해당 문단을 찾지 못하면 이 단계는 생략하고 Step 1만으로 충분하다.)

- [ ] **Step 3: 전체 테스트 통과 확인**

Run: `pytest tests/test_loca.py tests/test_repair.py tests/test_strip_loca.py tests/test_xml_escape.py tests/test_self_closing_content.py -q`
Expected: all pass.

- [ ] **Step 4: 커밋**

```bash
git add README.md
git commit -m "docs: README v3.8 — .loca regeneration restored

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: 운영 — dry-run 점검 → 전체 스윕 → 게임 확인

**Files:** (코드 변경 없음 — 운영 검증)

- [ ] **Step 1: dry-run으로 누락 규모 확인**

Run:
```
python bg3_repair_notfound.py ^
  --mods "C:\Users\anboy\AppData\Local\Larian Studios\Baldur's Gate 3\Mods" ^
  --divine "F:\BG3ModFile\ExportTool-v1.20.4\Packed\Tools\Divine.exe" ^
  --dry-run
```
Expected: 요약에 `loca_missing` 합계와 `would-repair` 개수 출력. 거의 모든 번역본이 `would-repair`(loca>0)로 잡혀야 함. 어떤 pak도 변경되지 않음.

- [ ] **Step 2: 전체 일괄 스윕 실행 (백업 후 제자리)**

Run (`--dry-run` 제거):
```
python bg3_repair_notfound.py ^
  --mods "C:\Users\anboy\AppData\Local\Larian Studios\Baldur's Gate 3\Mods" ^
  --divine "F:\BG3ModFile\ExportTool-v1.20.4\Packed\Tools\Divine.exe"
```
Expected: 원본이 `Mods_backup_<날짜>`에 백업되고, 각 pak에 `.loca`가 생성되어 재패킹. 요약에 `loca_generated`/`repaired` 출력. (대용량 포함 ~수십분~시간.)

- [ ] **Step 3: 게임 확인**

게임을 한국어로 실행해 이전 Not Found(InvisibleItems, CombatBodysuit, Artificer 등) 이름이 정상 출력되는지 확인. 남는 항목은 리포트의 `unfixable`과 대조.

- [ ] **Step 4: 멱등성 확인(선택)**

Run: 스윕을 한 번 더 dry-run.
Expected: 이제 대부분 `clean`(이미 `.loca` 보유) — `loca_missing`이 0에 수렴. 재실행이 불필요한 재패킹을 만들지 않음을 확인.

---

## Self-Review

**1. Spec coverage**
- `plan_loca_generation`(순수·멱등·dedup) → Task 1. ✅
- `ensure_loca`(divine 래퍼) → Task 2. ✅
- 수리 도구 strip 제거 + .loca 통합 + 리포트 → Task 3. ✅
- 본 파이프라인 strip→ensure_loca → Task 4. ✅
- README v3.8 → Task 5. ✅
- 전체 스윕/모든 언어 → `plan_loca_generation`이 Localization 하위 전 언어 xml 대상(Task 1) + 운영 스윕(Task 6). ✅
- 멱등성(이미 .loca면 스킵) → Task 1 `out.exists()` 필터 + Task 3 `loca_missing` convert 전 측정 → Task 6 Step 4 확인. ✅
- masking 회귀 방지(언어별 .loca) → 설계 근거, Task 6 게임 확인. ✅

**2. Placeholder scan:** 모든 step에 실제 코드/명령/기대출력. "TBD/TODO" 없음. (Task 5 Step 2만 "문단 못 찾으면 생략" 조건부 — 이는 기존 README 텍스트 가변성 때문이며 Step 1이 핵심이라 허용.) ✅

**3. Type consistency:** `plan_loca_generation(unpacked_path) -> List[Tuple[Path,Path]]`, `ensure_loca(divine_path, unpacked_path) -> int` 시그니처가 Task 1/2 정의 → Task 3/4 사용에서 일치. result dict의 `loca_missing`/`loca_generated` 키가 process_pak·write_report·summary·print에서 일관. import 교체(strip 제거, ensure_loca/plan 추가)가 Task 3/4에서 일관. ✅
