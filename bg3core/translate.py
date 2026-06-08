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
from .language import (
    LanguageProfile, DEFAULT_PROFILE, prompt_language_name, script_ratio,
)


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

_SYSTEM_INSTRUCTIONS: dict = {}

# 사용자가 선택한 모델 우선순위. 번역 시작 전 set_active_models()로 한 번 설정하면
# call_gemini가 이 순서대로 시도한다(미설정 시 MODELS_TO_TRY 기본값).
_ACTIVE_MODELS: Optional[List[str]] = None


def set_active_models(models: Optional[List[str]]) -> None:
    """call_gemini가 사용할 모델 우선순위를 지정한다.

    사용자가 고른 모델을 앞에 두고, 기본 MODELS_TO_TRY를 폴백으로 뒤에 덧붙여
    중복 없이 합친다. models가 비어 있으면 기본값(MODELS_TO_TRY)으로 되돌린다.
    """
    global _ACTIVE_MODELS
    if not models:
        _ACTIVE_MODELS = None
        return
    effective: List[str] = []
    for m in list(models) + list(MODELS_TO_TRY):
        m = (m or "").strip()
        if m and m not in effective:
            effective.append(m)
    _ACTIVE_MODELS = effective or None


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


def _cache_key(original: str, profile: LanguageProfile) -> str:
    # 한국어는 기존 캐시 파일과의 호환을 위해 bare key를 유지한다. 다른 대상 언어는
    # 같은 원문이라도 결과가 다르므로 폴더명으로 네임스페이스를 분리한다.
    if profile.folder_name == "Korean":
        return original
    return f"\x00{profile.folder_name}\x00{original}"


def cache_get(original: str, profile: LanguageProfile = DEFAULT_PROFILE) -> Optional[str]:
    if _translation_cache is None:
        return None
    return _translation_cache.get(_cache_key(original, profile))


def cache_put(original: str, translated: str, profile: LanguageProfile = DEFAULT_PROFILE) -> None:
    global _cache_dirty
    if _translation_cache is not None:
        _translation_cache[_cache_key(original, profile)] = translated
        _cache_dirty = True


def should_skip_translation(text: str, profile: LanguageProfile = DEFAULT_PROFILE) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    # 이미 대상 언어 스크립트로 절반 이상 채워져 있으면 번역 생략. Latin 등 감지
    # 불가 스크립트는 script_ratio가 0.0이라 이 조건에 걸리지 않는다.
    if script_ratio(stripped, profile) >= 0.5:
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


_XML_ENTITY_RE = re.compile(r"&(?:lt|gt|amp|quot|apos|#\d+|#x[0-9a-fA-F]+);")


def escape_unescaped_angle_brackets(text: str) -> str:
    """번역 결과 텍스트의 raw `<`/`>`/`&`를 XML entity로 변환.

    Gemini가 D&D 텍스트를 한글로 옮길 때:
    - `<내성 굴림>` 같은 자작 placeholder를 raw `<>`로 넣거나
    - `[3] & [4]` 같이 단독 `&`를 escape 없이 넣는 경우

    결과 XML이 깨지고 게임이 그 모드의 핸들 등록 자체를 실패한다. valid entity
    (`&lt;`, `&gt;`, `&amp;`, `&quot;`, `&apos;`, `&#nn;` 등)는 보존하고 그 외
    모든 raw XML 특수문자만 안전하게 entity로 변환한다.
    """
    if not any(c in text for c in "<>&"):
        return text

    # 1. 모든 valid entity를 임시 placeholder로 보호
    placeholders: dict = {}

    def _stash(m: re.Match) -> str:
        key = f"\x00ENT{len(placeholders)}\x00"
        placeholders[key] = m.group(0)
        return key

    text = _XML_ENTITY_RE.sub(_stash, text)

    # 2. 남은 raw `&`, `<`, `>`를 entity로 변환 (& 먼저 — 우리가 만든 &lt; 등을
    #    다시 escape하지 않기 위해. valid entity는 이미 placeholder로 보호됨)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # 3. placeholder 복원
    for key, val in placeholders.items():
        text = text.replace(key, val)
    return text


def get_system_instruction(profile: LanguageProfile = DEFAULT_PROFILE) -> str:
    cached = _SYSTEM_INSTRUCTIONS.get(profile.folder_name)
    if cached is not None:
        return cached

    target_name = prompt_language_name(profile)
    is_korean = profile.folder_name == "Korean"

    # 용어집(영→한)과 "Bane→액운" 규칙은 한국어 대상일 때만 의미가 있다.
    glossary_section = build_glossary_prompt_section() if is_korean else ""
    korean_extra = (
        '\n[한국어 추가 규칙]\n'
        '- 주문 이름 "Bane"은 신 이름이 아니라 주문으로 쓰인 경우 "액운"으로 번역한다.\n'
        if is_korean else ""
    )

    instruction = f"""너는 발더스 게이트 3 모드 번역 전문가다. 입력의 모든 텍스트를 {target_name}(으)로 번역한다.

[입력 형식]
번호|원문텍스트
(한 줄에 하나씩, 번호와 텍스트가 |로 구분)

[출력 형식]
번호|번역된텍스트
(입력과 동일한 번호를 유지하고, 텍스트만 {target_name}(으)로 번역)

[절대 규칙]
1) 번호를 절대 바꾸지 않는다. 입력의 번호를 그대로 출력한다.
2) 줄 수를 유지한다. 입력이 N줄이면 출력도 정확히 N줄이어야 한다.
3) 원문에 &lt;br&gt;, &lt;span&gt; 같은 이스케이프 태그는 그대로 유지한다.
4) &lt;LSTag ...&gt; ... &lt;/LSTag&gt; 이스케이프 태그도 그대로 유지하고 사이 텍스트만 번역한다.
5) 빈 텍스트는 빈 채로 유지한다. (예: 3| -> 3|)
6) 설명, 주석, 마크다운 없이 번역된 줄만 출력한다.
7) 원문은 어떤 언어든(영어, 포르투갈어 등) 될 수 있다. 무조건 {target_name}(으)로 번역한다. 원문이 이미 {target_name}이면 그대로 둔다.
8) 번역 결과 안에 `<...>` 형태의 새로운 태그나 placeholder를 절대 만들지 않는다. 원문에 있는 `&lt;...&gt;` 이스케이프 entity만 그대로 유지하고, 그 외 `<`나 `>` 기호 자체를 결과에 절대 사용하지 않는다. 게임 용어를 강조할 때도 "(내성 굴림)"이나 "[내성 굴림]" 같은 일반 괄호만 쓰고 `<...>`는 금지한다.
{korean_extra}
{glossary_section}"""

    _SYSTEM_INSTRUCTIONS[profile.folder_name] = instruction
    return instruction


def extract_block_parts(block: str) -> Tuple[str, str, str]:
    m = CONTENT_INNER_RE.search(block)
    if m:
        return m.group(1), m.group(2), m.group(3)
    return block, "", ""


def call_gemini(lines_text: str, filename: str,
                chunk_index: int, total_chunks: int,
                api_key: str,
                cancel_event: Optional[threading.Event] = None,
                target_profile: LanguageProfile = DEFAULT_PROFILE) -> Tuple[Optional[str], str]:
    payload = {
        "system_instruction": {"parts": [{"text": get_system_instruction(target_profile)}]},
        "contents": [{"parts": [{"text": f"[파일: {filename} ({chunk_index}/{total_chunks})]\n{lines_text}"}]}],
        "generationConfig": {
            "temperature": 0.1,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    last_status = "unknown"

    for model_name in (_ACTIVE_MODELS or MODELS_TO_TRY):
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
    target_profile: LanguageProfile = DEFAULT_PROFILE,
) -> str:
    use_glossary = target_profile.folder_name == "Korean"

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
        if should_skip_translation(text, target_profile):
            translated_map[idx] = text
            stats_skip += 1
        elif (cached := cache_get(text, target_profile)) is not None:
            translated_map[idx] = escape_unescaped_angle_brackets(cached)
            stats_cache += 1
        elif use_glossary and (hit := try_glossary_only(text)) is not None:
            translated_map[idx] = escape_unescaped_angle_brackets(hit)
            cache_put(text, hit, target_profile)
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
                    target_profile=target_profile,
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
                        t = escape_unescaped_angle_brackets(t)
                        if use_glossary:
                            t = apply_glossary(t)
                        translated_map[idx] = t
                        cache_put(orig, t, target_profile)
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
            final_blocks.append(f"{open_tag}{escape_unescaped_angle_brackets(translated_map[uid])}{close_tag}")
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
    target_profile: LanguageProfile = DEFAULT_PROFILE,
) -> Dict[str, str]:
    """임의 텍스트 리스트를 원문→대상언어 dict로 번역해 반환.

    중복 입력은 자동으로 dedup된다. should_skip_translation에 걸리거나 빈 문자열은
    결과 dict에 포함시키지 않는다(호출자가 원본 그대로 사용). API 실패 시에도
    해당 항목은 dict에서 빠진다.

    응답 파싱이 `idx|텍스트` 형식을 쓰므로, 텍스트 안의 `|`는 placeholder로
    보호해 호출하고 결과에서 복원한다.
    """
    use_glossary = target_profile.folder_name == "Korean"

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
        if should_skip_translation(text, target_profile):
            stats_skip += 1
            continue
        if (cached := cache_get(text, target_profile)) is not None:
            translated_map[idx] = escape_unescaped_angle_brackets(cached)
            stats_cache += 1
            continue
        if use_glossary and (hit := try_glossary_only(text)) is not None:
            translated_map[idx] = escape_unescaped_angle_brackets(hit)
            cache_put(text, hit, target_profile)
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
                    target_profile=target_profile,
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
                        t = escape_unescaped_angle_brackets(t)
                        if use_glossary:
                            t = apply_glossary(t)
                        translated_map[idx] = t
                        cache_put(orig, t, target_profile)
                time.sleep(1.5)

            if not failed_hard:
                break

    result: Dict[str, str] = {}
    for text, idx in unique_texts.items():
        if idx in translated_map:
            result[text] = translated_map[idx]
    return result
