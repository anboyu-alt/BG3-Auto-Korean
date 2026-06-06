#!/usr/bin/env python3
"""BG3 한글화 모드 'Not Found' 일괄 수리 CLI.

Mods 폴더에서 한글화된 pak을 자동 감지해, 깨진/누락 핸들을 오프라인으로 수리한다.
사용 예:
  python bg3_repair_notfound.py --mods "C:\\...\\Mods" --divine "C:\\...\\Divine.exe" --dry-run
"""
import argparse
import json
import os
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
            # 같은 볼륨(pak 폴더)에 산출한 뒤 os.replace로 원자적 교체.
            # 도중 중단돼도 원본 pak은 손상되지 않고, .repairing 임시본만 남는다(*.pak 글롭에 안 걸림).
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


def write_report(report_path: Path, summary: dict, results: list):
    report_path.parent.mkdir(parents=True, exist_ok=True)
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
