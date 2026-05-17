import os
import json
import time
import re
import threading
import urllib.request
import urllib.error
from typing import Dict, List, Tuple, Optional, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .logger import CallbackLogger

from .constants import (
    CONTENT_BLOCK_RE, CONTENT_INNER_RE, ESCAPED_TAGS,
    MODELS_TO_TRY, BASE_URL, TIMEOUT_SEC, DOWNSHIFT_TOKEN_STEPS,
)
from .glossary import GLOSSARY, try_glossary_only, build_glossary_prompt_section, apply_glossary


_translation_cache: Optional[dict] = None
_cache_dirty: bool = False

_SKIP_PATTERNS = re.compile(
    r"^("
    r"\d+[\d.,/%+\-*x ]*"
    r"|[+\-]\d+.*"
    r"|\d+[dD]\d+.*"
    r"|[A-Z_]{2,}"
    r"|<[^>]+>"
    r")$"
)

_SYSTEM_INSTRUCTION: Optional[str] = None


def load_translation_cache(cache_file: str) -> dict:
    global _translation_cache
    if _translation_cache is not None:
        return _translation_cache
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                _translation_cache = json.load(f)
                print(f"  [캐시] {len(_translation_cache)}개 항목 로드됨")
                return _translation_cache
        except (json.JSONDecodeError, IOError):
            pass
    _translation_cache = {}
    return _translation_cache


def save_translation_cache(cache_file: str) -> None:
    global _cache_dirty
    if not _cache_dirty or _translation_cache is None:
        return
    os.makedirs(os.path.dirname(os.path.abspath(cache_file)), exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(_translation_cache, f, ensure_ascii=False)
    _cache_dirty = False


def cache_get(original: str) -> Optional[str]:
    if _translation_cache is None:
        return None
    return _translation_cache.get(original)


def cache_put(original: str, translated: str) -> None:
    global _cache_dirty
    if _translation_cache is not None:
        _translation_cache[original] = translated
        _cache_dirty = True


def should_skip_translation(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    korean_chars = sum(1 for c in stripped if '가' <= c <= '힣')
    total_chars = sum(1 for c in stripped if not c.isspace())
    if total_chars > 0 and korean_chars / total_chars >= 0.5:
        return True
    if _SKIP_PATTERNS.match(stripped):
        return True
    return False


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 3) + 5


def chunk_by_tokens(items: list, max_tokens: int) -> List[list]:
    chunks = []
    current_chunk = []
    current_tokens = 0
    for item in items:
        item_tokens = estimate_tokens(item[1])
        if item_tokens > max_tokens:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0
            chunks.append([item])
            continue
        if current_tokens + item_tokens > max_tokens and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_tokens = 0
        current_chunk.append(item)
        current_tokens += item_tokens
    if current_chunk:
        chunks.append(current_chunk)
    return chunks


def protect_escaped_lstags(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    mapping: List[Tuple[str, str]] = []
    open_pat = re.compile(r"&lt;\s*LSTag\b.*?&gt;", re.IGNORECASE)
    for i, m in enumerate(reversed(list(open_pat.finditer(text))), start=1):
        ph = f"__ESCAPED_LSTAG_OPEN_{i}__"
        text = text[:m.start()] + ph + text[m.end():]
        mapping.append((ph, m.group(0)))
    close_pat = re.compile(r"&lt;\s*/\s*LSTag\s*&gt;", re.IGNORECASE)
    for i, m in enumerate(reversed(list(close_pat.finditer(text))), start=1):
        ph = f"__ESCAPED_LSTAG_CLOSE_{i}__"
        text = text[:m.start()] + ph + text[m.end():]
        mapping.append((ph, m.group(0)))
    return text, mapping


def protect_escaped_tags(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    mapping: List[Tuple[str, str]] = []
    text, m_lst = protect_escaped_lstags(text)
    mapping.extend(m_lst)
    for tag in ESCAPED_TAGS:
        ph_self = f"__ESCAPED_{tag.upper()}_SELF__"
        ph_open = f"__ESCAPED_{tag.upper()}_OPEN__"
        ph_close = f"__ESCAPED_{tag.upper()}_CLOSE__"
        text = re.sub(fr"&lt;\s*{tag}\s*/\s*&gt;", ph_self, text, flags=re.IGNORECASE)
        text = re.sub(fr"&lt;\s*{tag}\s*&gt;", ph_open, text, flags=re.IGNORECASE)
        text = re.sub(fr"&lt;\s*/\s*{tag}\s*&gt;", ph_close, text, flags=re.IGNORECASE)
        mapping.append((ph_self, f"&lt;{tag} /&gt;"))
        mapping.append((ph_open, f"&lt;{tag}&gt;"))
        mapping.append((ph_close, f"&lt;/{tag}&gt;"))
    return text, mapping


def restore_escaped_tags(text: str, mapping: List[Tuple[str, str]]) -> str:
    for ph, original in mapping:
        text = text.replace(ph, original)
    return text


def reescape_if_model_unescaped(text: str) -> str:
    for tag in ESCAPED_TAGS:
        text = re.sub(fr"<\s*{tag}\s*/\s*>", f"&lt;{tag} /&gt;", text, flags=re.IGNORECASE)
        text = re.sub(fr"<\s*{tag}\s*>", f"&lt;{tag}&gt;", text, flags=re.IGNORECASE)
        text = re.sub(fr"<\s*/\s*{tag}\s*>", f"&lt;/{tag}&gt;", text, flags=re.IGNORECASE)

    def _repl_open(m: re.Match) -> str:
        return f"&lt;{m.group(0)[1:-1]}&gt;"

    text = re.sub(r"<\s*LSTag\b[^>]*?>", _repl_open, text, flags=re.IGNORECASE)
    text = re.sub(r"<\s*/\s*LSTag\s*>", "&lt;/LSTag&gt;", text, flags=re.IGNORECASE)

    def _repl_self(m: re.Match) -> str:
        return f"&lt;{m.group(0)[1:-1]}&gt;"

    text = re.sub(r"<\s*LSTag\b[^>]*?/\s*>", _repl_self, text, flags=re.IGNORECASE)
    return text


def get_system_instruction() -> str:
    global _SYSTEM_INSTRUCTION
    if _SYSTEM_INSTRUCTION is None:
        glossary_section = build_glossary_prompt_section()
        _SYSTEM_INSTRUCTION = f"""너는 발더스 게이트 3 모드 한글화 전문가다.

[입력 형식]
번호|원문텍스트
(한 줄에 하나씩, 번호와 텍스트가 |로 구분)

[출력 형식]
번호|번역된텍스트
(입력과 동일한 번호를 유지하고, 텍스트만 한국어로 번역)

[절대 규칙]
1) 번호를 절대 바꾸지 않는다. 입력의 번호를 그대로 출력한다.
2) 줄 수를 유지한다. 입력이 N줄이면 출력도 정확히 N줄이어야 한다.
3) 원문에 &lt;br&gt;, &lt;span&gt; 같은 이스케이프 태그는 그대로 유지한다.
4) &lt;LSTag ...&gt; ... &lt;/LSTag&gt; 이스케이프 태그도 그대로 유지하고 사이 텍스트만 번역한다.
5) 빈 텍스트는 빈 채로 유지한다. (예: 3| -> 3|)
6) 설명, 주석, 마크다운 없이 번역된 줄만 출력한다.
7) 원문은 영어가 아닐 수도 있다(포르투갈어 등). 어떤 언어든 한국어로 번역한다.
8) 주문 이름 "Bane"은 신 이름이 아니라 주문으로 쓰인 경우 "액운"으로 번역한다.

{glossary_section}"""
    return _SYSTEM_INSTRUCTION


def extract_block_parts(block: str) -> Tuple[str, str, str]:
    m = CONTENT_INNER_RE.search(block)
    if m:
        return m.group(1), m.group(2), m.group(3)
    return block, "", ""


def call_gemini(lines_text: str, filename: str,
                chunk_index: int, total_chunks: int,
                api_key: str,
                cancel_event: Optional[threading.Event] = None) -> Tuple[Optional[str], str]:
    payload = {
        "system_instruction": {"parts": [{"text": get_system_instruction()}]},
        "contents": [{"parts": [{"text": f"[파일: {filename} ({chunk_index}/{total_chunks})]\n{lines_text}"}]}],
        "generationConfig": {
            "temperature": 0.1,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    last_status = "unknown"

    for model_name in MODELS_TO_TRY:
        url = f"{BASE_URL}/v1beta/models/{model_name}:generateContent"
        for attempt in range(1, 4):
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                    rj = json.loads(resp.read().decode("utf-8"))

                candidates = rj.get("candidates", [])
                if not candidates:
                    last_status = f"no_candidates ({model_name})"
                    continue

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    last_status = f"no_parts ({model_name})"
                    continue

                translated = parts[0].get("text", "").replace("```", "").strip()
                if translated.strip() == lines_text.strip():
                    last_status = f"unchanged_output ({model_name})"
                    continue

                return translated, f"ok ({model_name})"

            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", errors="replace")
                except Exception:
                    pass

                if e.code == 429:
                    wait = 10 + attempt * 15
                    print(f"        [!] 429 제한. {wait}초 대기 ({model_name})")
                    for _ in range(wait):
                        if cancel_event and cancel_event.is_set():
                            return None, "user_cancelled"
                        time.sleep(1)
                    continue
                elif e.code == 404:
                    last_status = f"404 ({model_name})"
                    break
                elif e.code >= 500:
                    time.sleep(5 * attempt)
                    continue
                else:
                    last_status = f"HTTP {e.code} ({model_name}) {body[:200]}"
                    break

            except Exception as e:
                last_status = f"error: {e} ({model_name})"
                break

    return None, last_status


def parse_response(response: str, expected_count: int) -> Optional[dict]:
    result = {}
    for line in response.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        sep = line.find("|")
        if sep == -1:
            continue
        try:
            result[int(line[:sep].strip())] = line[sep + 1:]
        except ValueError:
            continue
    return result if len(result) >= expected_count * 0.8 else None


def process_xml_file(
    original_content: str,
    filename: str,
    api_key: str,
    log_file: str,
    cancel_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    logger: Optional["CallbackLogger"] = None,
) -> str:
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)
    matches = list(CONTENT_BLOCK_RE.finditer(original_content))
    total_blocks = len(matches)
    if total_blocks == 0:
        return original_content

    all_blocks = []
    for m in matches:
        full = m.group(1)
        open_tag, inner, close_tag = extract_block_parts(full)
        all_blocks.append((full, open_tag, inner, close_tag))

    unique_texts: dict = {}
    block_to_unique: List[Optional[int]] = []
    for _, _, inner, _ in all_blocks:
        stripped = inner.strip()
        if not stripped:
            block_to_unique.append(None)
            continue
        if stripped not in unique_texts:
            unique_texts[stripped] = len(unique_texts) + 1
        block_to_unique.append(unique_texts[stripped])

    unique_count = len(unique_texts)
    empty_count = sum(1 for x in block_to_unique if x is None)
    dedup_saved = total_blocks - unique_count - empty_count
    _log(f"    -> 총 블록: {total_blocks} (고유: {unique_count}, 중복 제거: {dedup_saved})")

    if unique_count == 0:
        return original_content

    translated_map: dict = {}
    unique_list = sorted(unique_texts.items(), key=lambda x: x[1])
    stats_cache = stats_skip = stats_glossary = 0
    need_api: List[Tuple[str, int]] = []

    for text, idx in unique_list:
        if should_skip_translation(text):
            translated_map[idx] = text
            stats_skip += 1
        elif (cached := cache_get(text)) is not None:
            translated_map[idx] = cached
            stats_cache += 1
        elif (hit := try_glossary_only(text)) is not None:
            translated_map[idx] = hit
            cache_put(text, hit)
            stats_glossary += 1
        else:
            need_api.append((text, idx))

    local_total = stats_cache + stats_skip + stats_glossary
    _log(f"    -> 로컬: 캐시 {stats_cache} + 스킵 {stats_skip} + 글로서리 {stats_glossary} = {local_total}개")
    _log(f"    -> API 필요: {len(need_api)}개")

    if need_api:
        protected_texts = []
        for text, idx in need_api:
            protected, mapping = protect_escaped_tags(text)
            protected_texts.append((idx, protected, mapping, text))

        for max_tokens in DOWNSHIFT_TOKEN_STEPS:
            remaining = [x for x in protected_texts if x[0] not in translated_map]
            if not remaining:
                break

            chunks = chunk_by_tokens(remaining, max_tokens)
            _log(f"    -> 청크 수: {len(chunks)} (토큰한도 {max_tokens}, 미번역 {len(remaining)}개)")

            failed_hard = False
            for cidx, chunk in enumerate(chunks, start=1):
                if cancel_event and cancel_event.is_set():
                    raise InterruptedError("user_cancelled")
                while pause_event and pause_event.is_set():
                    time.sleep(0.2)
                    if cancel_event and cancel_event.is_set():
                        raise InterruptedError("user_cancelled")

                ctokens = sum(estimate_tokens(t) for _, t, _, _ in chunk)
                _log(f"      ▶ 청크 ({cidx}/{len(chunks)}) - {len(chunk)}개 (~{ctokens}토큰)")

                lines = []
                for idx, protected, _, _ in chunk:
                    lines.append(f"{idx}|{protected.replace(chr(10), chr(92) + 'n')}")

                raw, status = call_gemini(
                    "\n".join(lines), filename, cidx, len(chunks), api_key,
                    cancel_event=cancel_event,
                )

                if raw is None:
                    if status == "user_cancelled":
                        raise InterruptedError("user_cancelled")
                    _log(f"        ❌ 실패: {status}")
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(f"{filename} | 청크 {cidx}/{len(chunks)} | {status}\n")
                    failed_hard = True
                    continue

                parsed = parse_response(raw, len(chunk))
                if parsed is None:
                    _log("        ⚠️ 파싱 실패. 원본 유지")
                    failed_hard = True
                    continue

                ok = 0
                for idx, _, mapping, orig in chunk:
                    if idx in parsed:
                        t = parsed[idx].replace("\\n", "\n")
                        t = restore_escaped_tags(t, mapping)
                        t = reescape_if_model_unescaped(t)
                        t = apply_glossary(t)
                        translated_map[idx] = t
                        cache_put(orig, t)
                        ok += 1
                _log(f"        -> 성공: {ok}/{len(chunk)}개 ({status})")
                time.sleep(1.5)

            if not failed_hard:
                break
            _log("    -> 다운시프트 진행")

    final_blocks = []
    for i, (full_block, open_tag, inner, close_tag) in enumerate(all_blocks):
        uid = block_to_unique[i]
        if uid is not None and uid in translated_map:
            final_blocks.append(f"{open_tag}{translated_map[uid]}{close_tag}")
        else:
            final_blocks.append(full_block)

    header = original_content[:matches[0].start()]
    footer = original_content[matches[-1].end():]
    done = sum(1 for uid in block_to_unique if uid is not None and uid in translated_map)
    _log(f"    -> 최종: {done}/{total_blocks} 블록 번역 완료")

    return header + "\n".join(final_blocks) + footer


_PIPE_PLACEHOLDER = "__BG3MCM_PIPE_FB29A8__"


def _protect_pipes(text: str) -> str:
    return text.replace("|", _PIPE_PLACEHOLDER)


def _restore_pipes(text: str) -> str:
    return text.replace(_PIPE_PLACEHOLDER, "|")


def translate_text_list(
    texts: List[str],
    label: str,
    api_key: str,
    log_file: str,
    cancel_event: Optional[threading.Event] = None,
    pause_event: Optional[threading.Event] = None,
    logger: Optional["CallbackLogger"] = None,
) -> Dict[str, str]:
    """임의 텍스트 리스트를 영문→한글 dict로 번역해 반환.

    중복 입력은 자동으로 dedup된다. should_skip_translation에 걸리거나 빈 문자열은
    결과 dict에 포함시키지 않는다(호출자가 원본 그대로 사용). API 실패 시에도
    해당 항목은 dict에서 빠진다.

    응답 파싱이 `idx|텍스트` 형식을 쓰므로, 텍스트 안의 `|`는 placeholder로
    보호해 호출하고 결과에서 복원한다.
    """
    def _log(text: str) -> None:
        if logger:
            logger.info(text)
        else:
            print(text)

    unique_texts: Dict[str, int] = {}
    for raw in texts:
        stripped = (raw or "").strip()
        if not stripped:
            continue
        if stripped in unique_texts:
            continue
        unique_texts[stripped] = len(unique_texts) + 1

    if not unique_texts:
        return {}

    translated_map: Dict[int, str] = {}
    need_api: List[Tuple[str, int]] = []
    stats_cache = stats_skip = stats_glossary = 0

    for text, idx in sorted(unique_texts.items(), key=lambda x: x[1]):
        if should_skip_translation(text):
            stats_skip += 1
            continue
        if (cached := cache_get(text)) is not None:
            translated_map[idx] = cached
            stats_cache += 1
            continue
        if (hit := try_glossary_only(text)) is not None:
            translated_map[idx] = hit
            cache_put(text, hit)
            stats_glossary += 1
            continue
        need_api.append((text, idx))

    _log(f"    -> [{label}] 고유 {len(unique_texts)} | 캐시 {stats_cache} 글로서리 {stats_glossary} 스킵 {stats_skip} | API {len(need_api)}")

    if need_api:
        protected_texts = []
        for text, idx in need_api:
            protected, mapping = protect_escaped_tags(text)
            protected = _protect_pipes(protected)
            protected_texts.append((idx, protected, mapping, text))

        for max_tokens in DOWNSHIFT_TOKEN_STEPS:
            remaining = [x for x in protected_texts if x[0] not in translated_map]
            if not remaining:
                break

            chunks = chunk_by_tokens(remaining, max_tokens)
            failed_hard = False
            for cidx, chunk in enumerate(chunks, start=1):
                if cancel_event and cancel_event.is_set():
                    raise InterruptedError("user_cancelled")
                while pause_event and pause_event.is_set():
                    time.sleep(0.2)
                    if cancel_event and cancel_event.is_set():
                        raise InterruptedError("user_cancelled")

                lines = []
                for idx, protected, _, _ in chunk:
                    lines.append(f"{idx}|{protected.replace(chr(10), chr(92) + 'n')}")

                raw, status = call_gemini(
                    "\n".join(lines), label, cidx, len(chunks), api_key,
                    cancel_event=cancel_event,
                )

                if raw is None:
                    if status == "user_cancelled":
                        raise InterruptedError("user_cancelled")
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(f"{label} | 청크 {cidx}/{len(chunks)} | {status}\n")
                    failed_hard = True
                    continue

                parsed = parse_response(raw, len(chunk))
                if parsed is None:
                    failed_hard = True
                    continue

                for idx, _, mapping, orig in chunk:
                    if idx in parsed:
                        t = parsed[idx].replace("\\n", "\n")
                        t = restore_escaped_tags(t, mapping)
                        t = _restore_pipes(t)
                        t = reescape_if_model_unescaped(t)
                        t = apply_glossary(t)
                        translated_map[idx] = t
                        cache_put(orig, t)
                time.sleep(1.5)

            if not failed_hard:
                break

    result: Dict[str, str] = {}
    for text, idx in unique_texts.items():
        if idx in translated_map:
            result[text] = translated_map[idx]
    return result
