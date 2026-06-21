"""UI i18n 번역 생성기 — en.py STRINGS를 Gemini로 13개 언어로 번역해 i18n 파일 생성.

영어(en, 원본)와 한국어(ko, 수기 번역)는 건드리지 않는다. 나머지 13개 언어를 생성한다.
플레이스홀더({...})와 기술용어(PAK, Divine.exe, MCM, LSTag, API, Gemini, .pak, .loca,
.xml, Lua, JSON, BG3, Ctrl+S 등)는 그대로 두도록 지시하고, 생성 후 검증한다.
키가 빠지거나 플레이스홀더가 어긋나면 해당 항목은 영어로 폴백한다.

사용: python tools/gen_ui_translations.py [code ...]   (코드 생략 시 13개 전부)
API 키: config.json(api_key) 또는 환경변수 GEMINI_API_KEY.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bg3gui.i18n.en import STRINGS as EN  # noqa: E402
from bg3core.config import load_config  # noqa: E402

I18N_DIR = ROOT / "bg3gui" / "i18n"

# 생성 대상: 코드 → 사람이 읽는 언어명(프롬프트용). en/ko 제외.
TARGETS = {
    "fr": "French", "de": "German", "es": "Spanish (Spain)", "pl": "Polish",
    "ru": "Russian", "zh": "Simplified Chinese", "tr": "Turkish",
    "pt_br": "Brazilian Portuguese", "it": "Italian",
    "es_la": "Latin American Spanish", "zh_tw": "Traditional Chinese",
    "uk": "Ukrainian", "ja": "Japanese",
}

MODEL = "gemini-2.5-flash"
BASE = "https://generativelanguage.googleapis.com"

DO_NOT_TRANSLATE = (
    "PAK, .pak, .loca, .xml, Divine.exe, LSLib, ExportTool, MCM, LSTag, API, "
    "Gemini, Lua, JSON, BG3, Baldur's Gate 3, Ctrl+S, contentuid, UUID, .NET"
)


def _placeholders(s: str) -> set:
    return set(re.findall(r"\{[^}]*\}", s))


def _call_gemini(api_key: str, lang_name: str, payload_json: str) -> dict:
    system = (
        "You are a professional software UI localizer. Translate the VALUES of the "
        f"given JSON object into {lang_name}. Rules:\n"
        "1) Return ONLY a JSON object with the SAME keys; translate values only.\n"
        "2) Keep every placeholder like {current}, {total}, {err} EXACTLY as-is.\n"
        "3) Do NOT translate these technical/brand terms (keep verbatim): "
        f"{DO_NOT_TRANSLATE}.\n"
        "4) Keep emojis/symbols. Keep it concise (UI labels). No comments, no code fences."
    )
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": payload_json}]}],
        "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json"},
    }
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    url = f"{BASE}/v1beta/models/{MODEL}:generateContent"
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        rj = json.loads(resp.read().decode("utf-8"))
    text = rj["candidates"][0]["content"]["parts"][0]["text"]
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def _write_module(code: str, lang_name: str, strings: dict) -> None:
    header = (
        f"# bg3gui/i18n/{code}.py — {lang_name}\n"
        "# AUTO-GENERATED (machine translation). Corrections welcome via GitHub PR.\n"
        "# Regenerate: python tools/gen_ui_translations.py " + code + "\n"
    )
    out = header + "STRINGS = " + json.dumps(strings, ensure_ascii=False, indent=4) + "\n"
    (I18N_DIR / f"{code}.py").write_text(out, encoding="utf-8")


def main() -> None:
    codes = sys.argv[1:] or list(TARGETS)
    api_key = os.environ.get("GEMINI_API_KEY") or load_config().api_key
    if not api_key:
        print("ERROR: no API key (set GEMINI_API_KEY or save it in the app).")
        sys.exit(1)

    src_json = json.dumps(EN, ensure_ascii=False)
    for code in codes:
        lang = TARGETS.get(code)
        if not lang:
            print("skip unknown code:", code)
            continue
        try:
            translated = _call_gemini(api_key, lang, src_json)
        except Exception as e:
            print(f"[{code}] FAILED: {e}")
            continue
        # 검증 + 영어 폴백
        result, kept_en, ph_fix = {}, 0, 0
        for k, en_val in EN.items():
            tv = translated.get(k)
            if not isinstance(tv, str) or not tv.strip():
                result[k] = en_val; kept_en += 1; continue
            if _placeholders(tv) != _placeholders(en_val):
                result[k] = en_val; ph_fix += 1; continue
            result[k] = tv
        _write_module(code, lang, result)
        print(f"[{code}] {lang}: wrote {len(result)} keys "
              f"(en-fallback {kept_en}, placeholder-fallback {ph_fix})")


if __name__ == "__main__":
    main()
