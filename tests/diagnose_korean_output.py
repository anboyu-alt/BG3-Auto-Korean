"""산출 PAK에서 추출한 BootstrapClient.lua를 진단.

번역 후 어떤 영문 문자열이 남았고 그게 (a) 의도된 잔존 (검수/옵션/식별자),
(b) 번역 실패, (c) 정규식이 못 잡은 패턴 중 어디에 해당하는지 분류.

사용:
    python tests/diagnose_korean_output.py <path/to/BootstrapClient.lua>
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bg3core.mcm.lua_handler import scan_lua
from bg3core.mcm.whitelist import is_lua_skippable, is_lua_short_key


def main() -> None:
    if len(sys.argv) < 2:
        # 기본: 풀린 산출물 경로 추정
        candidate = Path("F:/BG3ModFile/_verify_korean/Mods/Tooltip Manager/ScriptExtender/Lua/BootstrapClient.lua")
        if not candidate.exists():
            print(f"파일 경로를 인자로 주거나 {candidate}에 산출물을 풀어두세요.")
            sys.exit(1)
        target = candidate
    else:
        target = Path(sys.argv[1])

    if not target.exists():
        print(f"파일 없음: {target}")
        sys.exit(1)

    content = target.read_text(encoding="utf-8", errors="replace")
    auto, review, options = scan_lua(content)

    def looks_korean(s: str) -> bool:
        return any("가" <= c <= "힣" or "ㄱ" <= c <= "ㆎ" for c in s)

    print(f"=== {target} ===")
    print(f"AUTO 후보 {len(auto)}건, REVIEW {len(review)}건, 옵션 배열 {len(options)}개\n")

    untranslated_auto = [e for e in auto if not looks_korean(e["text"]) and e["text"].strip()]
    empty_auto = [e for e in auto if not e["text"].strip()]
    print(f"[AUTO 영문 잔존 — 진짜 버그 가능성] {len(untranslated_auto)}건")
    for e in untranslated_auto:
        print(f"  L{e['line']:>4} [{e['pattern']}] {e['text']!r}")
    print(f"[AUTO 빈 문자열 — 정상 잔존] {len(empty_auto)}건")
    for e in empty_auto:
        print(f"  L{e['line']:>4} [{e['pattern']}] {e['text']!r}")

    print(f"\n[REVIEW 큐 — 의도된 영문 잔존] {len(review)}건")
    for e in review:
        print(f"  L{e['line']:>4} [{e.get('kind','?')}] {e['text']!r}")

    print(f"\n[옵션 배열 — 의도된 영문 잔존] {len(options)}개")
    for o in options:
        print(f"  L{o['line']:>4} {o['variable']}.Options = {o['items']}")


if __name__ == "__main__":
    main()
