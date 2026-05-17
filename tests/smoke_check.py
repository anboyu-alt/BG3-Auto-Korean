"""통합 smoke 테스트 — 단위 테스트 통과 후 임포트·시그니처·회귀 안전성 검증.

사용:
    python tests/smoke_check.py
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bg3core.config as c
import bg3core.pipeline as p
from bg3core.mcm import process_mcm_for_mod, has_mcm_artifacts


def check(label: str, ok: bool, detail: str = "") -> None:
    mark = "OK " if ok else "FAIL"
    print(f"[{mark}] {label}" + (f" — {detail}" if detail else ""))
    if not ok:
        sys.exit(1)


def main() -> None:
    cfg = c.UserConfig()
    check("UserConfig.mcm_enabled 기본값 True", cfg.mcm_enabled is True, f"got {cfg.mcm_enabled}")

    cfg2 = c.UserConfig()
    for k, v in {**cfg.__dict__, "mcm_enabled": False}.items():
        if hasattr(cfg2, k):
            setattr(cfg2, k, v)
    check("dict roundtrip으로 mcm_enabled=False 복원", cfg2.mcm_enabled is False)

    check(
        "process_pak_file 시그니처에 mcm_enabled 포함",
        "mcm_enabled" in p.process_pak_file.__code__.co_varnames,
    )
    check(
        "run_batch 시그니처에 mcm_enabled 포함",
        "mcm_enabled" in p.run_batch.__code__.co_varnames,
    )

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "Localization").mkdir()
        check("MCM 자산 없는 모드 감지", has_mcm_artifacts(root) is False)
        result = process_mcm_for_mod(root, api_key="", log_file="x.log")
        check("MCM 자산 없는 모드 처리 결과 None", result is None)

        lua_dir = root / "Mods" / "Foo" / "ScriptExtender" / "Lua"
        lua_dir.mkdir(parents=True)
        (lua_dir / "init.lua").write_text(':AddText("Hello")\n', encoding="utf-8")
        check("Lua만 있어도 MCM 자산으로 인식", has_mcm_artifacts(root) is True)

    print("\nSMOKE OK")


if __name__ == "__main__":
    main()
