import os
import json
import time
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Tuple, Optional


# =============================================================================
# BG3 모드 자동 한글화 스크립트
# 제작: (배포자 이름/닉네임을 여기에 입력하세요)
# =============================================================================
#
# ※ 처음 사용하시는 분은 아래 [1단계], [2단계]를 먼저 읽어주세요.
#
# ----------------------------------------------------------------
# [1단계] Gemini API 키 발급 방법 (무료)
# ----------------------------------------------------------------
#  1. https://aistudio.google.com 접속 (Google 계정 로그인 필요)
#  2. 왼쪽 메뉴에서 "Get API key" 클릭
#  3. "Create API key" 버튼 클릭
#  4. 생성된 키(AIzaSy...로 시작하는 문자열)를 복사
#  5. 아래 [2단계]에 따라 키를 입력
#
# ----------------------------------------------------------------
# [2단계] API 키와 경로 설정 방법 (두 가지 중 하나를 선택)
# ----------------------------------------------------------------
#
#  ★ 방법 A: 코드에 직접 입력 (간단)
#     아래 설정 구간에서
#       API_KEY = ""  →  API_KEY = "여기에 발급받은 키 붙여넣기"
#       TARGET_ROOT_FOLDER = ""  →  해당 경로로 변경
#     저장 후 실행하면 됩니다.
#
#  ★ 방법 B: 실행할 때마다 직접 입력 (코드 수정 없이 사용 가능)
#     API_KEY와 TARGET_ROOT_FOLDER를 빈 문자열("")로 두면
#     스크립트 실행 시 자동으로 입력을 요청합니다.
#
# ----------------------------------------------------------------
# [참고] 경로 입력 예시 (Windows)
# ----------------------------------------------------------------
#  올바른 예시:  r"C:\Users\홍길동\Downloads\bg3-modders-multitool"
#  앞에 r을 붙이고 큰따옴표로 감싸야 역슬래시(\)가 올바르게 인식됩니다.
#
# =============================================================================


# ==========================================
# [설정 구간] ← 여기를 수정하세요
# ==========================================

# Gemini API 키 (발급 방법은 위 [1단계] 참고)
# 비워두면 실행 시 입력 요청
API_KEY = ""

# 번역할 모드 파일의 루트 경로 (bg3-modders-multitool 폴더)
# 비워두면 실행 시 입력 요청
# 예시: r"C:\Users\홍길동\Downloads\bg3-modders-multitool"
TARGET_ROOT_FOLDER = ""

# 번역 실패 로그 파일 경로
# 비워두면 스크립트와 같은 폴더에 translation_errors.txt 로 저장
LOG_FILE = ""

# Korean 폴더가 이미 있으면 한글화 완료로 간주하고 스킵
SKIP_IF_KOREAN_EXISTS = True

# ==========================================


# ==========================================
# [고급 설정] 건드리지 않아도 됩니다
# ==========================================
INPUT_GLOB = "*.xml"
DEFAULT_BLOCKS_PER_CHUNK = 60
DOWNSHIFT_STEPS = [60, 40, 25, 15]

MODELS_TO_TRY = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]

BASE_URL = "https://generativelanguage.googleapis.com"
TIMEOUT_SEC = 120
CONTENT_BLOCK_RE = re.compile(r"(<content\b[^>]*>.*?</content>)", re.DOTALL | re.IGNORECASE)
ESCAPED_TAGS = {"br", "span"}
# ==========================================

# ==========================================
# [용어집] 고유 용어 선번역 목록
# 형식: "원문": "번역어"
# - 프롬프트에 포함되어 Gemini에게 우선 번역을 지시
# - 번역 후 코드가 한 번 더 치환하여 확실하게 적용
# ==========================================
GLOSSARY = {
    # 동료 캐릭터
    "Karlach": "카를라크",
    "Astarion": "아스타리온",
    "Gale": "게일",
    "Lae'zel": "레이젤",
    "Shadowheart": "섀도하트",
    "Wyll": "윌",
    "Jaheira": "자헤이라",
    "Minsc": "민스크",
    "Halsin": "할신",
    "Minthara": "민타라",
    "Nightsong": "밤의 노래",
    "Dark Urge": "어두운 충동",
    "Haunted One": "시달리는 자",
    "Viconia": "바이코니아",
    "Ketheric Thorm": "케더릭 토름",
    # 주요 NPC / 세력
    "Raphael": "라파엘",
    "Mizora": "미조라",
    "Orin": "오린",
    "Gortash": "고르타시",
    "The Emperor": "황제",
    "Mind Flayer": "마인드 플레이어",
    "Illithid": "일리시드",
    # 직업 - 바바리안
    "Barbarian": "바바리안",
    "Wildheart": "야생의심장",
    "Berserker": "광전사",
    "Wild Magic": "야생 마법",
    "Giant": "거인",
    # 직업 - 바드
    "Bard": "바드",
    "College of Lore": "전승학파",
    "College of Valour": "용맹학파",
    "College of Swords": "검술학파",
    "College of Glamour": "요술학파",
    # 직업 - 클레릭
    "Cleric": "클레릭",
    "Life Domain": "생명 권역",
    "Light Domain": "빛 권역",
    "Trickery Domain": "기만 권역",
    "Knowledge Domain": "지식 권역",
    "Nature Domain": "자연 권역",
    "Tempest Domain": "폭풍 권역",
    "War Domain": "전쟁 권역",
    "Death Domain": "죽음 권역",
    # 직업 - 드루이드
    "Druid": "드루이드",
    "Circle of the Land": "땅의 회합",
    "Circle of the Moon": "달의 회합",
    "Circle of the Spores": "포자의 회합",
    "Circle of the Stars": "별의 회합",
    # 직업 - 파이터
    "Fighter": "파이터",
    "Battle Master": "전투의 대가",
    "Eldritch Knight": "비술 기사",
    "Champion": "투사",
    "Arcane Archer": "비전 궁수",
    # 직업 - 몽크
    "Monk": "몽크",
    "Way of the Four Elements": "사원소의 길",
    "Way of the Open Hand": "열린 손의 길",
    "Way of Shadow": "그림자의 길",
    "Way of the Drunken Master": "취권 달인의 길",
    # 직업 - 팔라딘
    "Paladin": "팔라딘",
    "Oath of Devotion": "헌신의 맹세",
    "Oath of the Ancients": "선조의 맹세",
    "Oath of Vengeance": "복수의 맹세",
    "Oath of the Crown": "왕관의 맹세",
    # 직업 - 레인저
    "Ranger": "레인저",
    "Hunter": "사냥꾼",
    "Beast Master": "야수 조련사",
    "Gloom Stalker": "어둠 추척자",
    "Swarmkeeper": "무리지기",
    # 직업 - 로그
    "Rogue": "로그",
    "Thief": "도둑",
    "Arcane Trickster": "비전 괴도",
    "Assassin": "암살자",
    "Swashbuckler": "칼잡이",
    # 직업 - 소서러
    "Sorcerer": "소서러",
    "Draconic Bloodline": "용의 혈통",
    "Storm Sorcery": "폭풍 술사",
    "Shadow Magic": "그림자 마법",
    # 직업 - 워락
    "Warlock": "워락",
    "The Fiend": "마족",
    "The Great Old One": "고대의 지배자",
    "The Archfey": "대요정",
    "The Hexblade": "주술 칼날",
    "Hexblade": "주술 칼날",
    "Pact of the Chain": "사슬의 계약",
    "Pact of the Blade": "검의 계약",
    "Pact of the Tome": "장서의 계약",
    # 직업 - 위저드
    "Wizard": "위저드",
    "Bladesinging": "칼날 노래",
    "Bladesinger": "칼날 노래",
    # 주문 학파 (긴 표현 먼저 - 부분 매칭 방지)
    "School of Abjuration": "방호술",
    "Abjuration School": "방호술",
    "Abjuration": "방호술",
    "School of Evocation": "방출술",
    "Evocation School": "방출술",
    "Evocation": "방출술",
    "School of Necromancy": "사령술",
    "Necromancy School": "사령술",
    "Necromancy": "사령술",
    "School of Conjuration": "창조술",
    "Conjuration School": "창조술",
    "Conjuration": "창조술",
    "School of Enchantment": "환혹술",
    "Enchantment School": "환혹술",
    "Enchantment": "환혹술",
    "School of Divination": "예지술",
    "Divination School": "예지술",
    "Divination": "예지술",
    "School of Illusion": "환영술",
    "Illusion School": "환영술",
    "Illusion": "환영술",
    "School of Transmutation": "변환술",
    "Transmutation School": "변환술",
    "Transmutation": "변환술",
    # 주문명 (자주 등장하는 것들)
    "Fireball": "화염구",
    "Lightning Bolt": "번개 줄기",
    "Haste": "가속",
    "Slow": "둔화",
    "Invisibility": "투명화",
    "Misty Step": "안개 걸음",
    "Thunderwave": "천둥파",
    "Animate Dead": "망자 조종",
    "Speak with Dead": "망자와 대화",
    "Polymorph": "변신",
    "Counterspell": "주문 방해",
    "Bless": "축복",
    "Bane": "액운",
    "Hex": "주술",
    "Healing Word": "치유의 단어",
    "Revivify": "생환",
    # 전투 용어
    "Attack Rolls": "공격 굴림",
    "Attack Roll": "공격 굴림",
    "attack rolls": "공격 굴림",
    "attack roll": "공격 굴림",
    "Saving Throws": "내성 굴림",
    "Saving Throw": "내성 굴림",
    "saving throws": "내성 굴림",
    "saving throw": "내성 굴림",
}
# ==========================================


def setup_config() -> Tuple[str, str, str]:
    """
    API 키, 경로, 로그 파일 경로를 확정한다.
    코드에 직접 입력된 값이 없으면 실행 시 사용자에게 입력받는다.
    """
    # --- API 키 확정 ---
    # 환경변수 → 코드 직접 입력 → 실행 시 입력 순으로 확인
    api_key = os.environ.get("GEMINI_API_KEY", "").strip() or API_KEY.strip()

    if not api_key:
        print("=" * 60)
        print("  Gemini API 키가 설정되어 있지 않습니다.")
        print()
        print("  API 키 발급 방법:")
        print("  1. https://aistudio.google.com 접속")
        print("  2. 'Get API key' → 'Create API key' 클릭")
        print("  3. 생성된 키(AIzaSy...로 시작)를 아래에 붙여넣기")
        print("=" * 60)
        api_key = input("  API 키 입력: ").strip()
        print()

    if not api_key:
        print("❌ API 키가 입력되지 않았습니다. 프로그램을 종료합니다.")
        raise SystemExit(1)

    # --- 루트 경로 확정 ---
    root_folder = TARGET_ROOT_FOLDER.strip()

    if not root_folder:
        print("=" * 60)
        print("  번역할 모드 파일의 루트 경로를 입력해주세요.")
        print()
        print("  예시: C:\\Users\\홍길동\\Downloads\\bg3-modders-multitool")
        print("  (폴더를 탐색기에서 찾아 주소창의 경로를 복사해서 붙여넣기)")
        print("=" * 60)
        root_folder = input("  경로 입력: ").strip().strip('"').strip("'")
        print()

    if not root_folder:
        print("❌ 경로가 입력되지 않았습니다. 프로그램을 종료합니다.")
        raise SystemExit(1)

    # --- 로그 파일 경로 확정 ---
    log_file = LOG_FILE.strip()
    if not log_file:
        # 스크립트와 같은 폴더에 저장
        script_dir = Path(__file__).parent
        log_file = str(script_dir / "translation_errors.txt")

    return api_key, root_folder, log_file


def protect_escaped_lstags(text: str) -> Tuple[str, List[Tuple[str, str]]]:
    mapping: List[Tuple[str, str]] = []
    open_pat = re.compile(r"&lt;\s*LSTag\b.*?&gt;", re.IGNORECASE)
    opens = list(open_pat.finditer(text))
    for i, m in enumerate(reversed(opens), start=1):
        original = m.group(0)
        ph = f"__ESCAPED_LSTAG_OPEN_{i}__"
        text = text[:m.start()] + ph + text[m.end():]
        mapping.append((ph, original))

    close_pat = re.compile(r"&lt;\s*/\s*LSTag\s*&gt;", re.IGNORECASE)
    closes = list(close_pat.finditer(text))
    for i, m in enumerate(reversed(closes), start=1):
        original = m.group(0)
        ph = f"__ESCAPED_LSTAG_CLOSE_{i}__"
        text = text[:m.start()] + ph + text[m.end():]
        mapping.append((ph, original))

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
        inside = m.group(0)[1:-1]
        return f"&lt;{inside}&gt;"

    text = re.sub(r"<\s*LSTag\b[^>]*?>", _repl_open, text, flags=re.IGNORECASE)
    text = re.sub(r"<\s*/\s*LSTag\s*>", "&lt;/LSTag&gt;", text, flags=re.IGNORECASE)

    def _repl_self(m: re.Match) -> str:
        inside = m.group(0)[1:-1]
        return f"&lt;{inside}&gt;"

    text = re.sub(r"<\s*LSTag\b[^>]*?/\s*>", _repl_self, text, flags=re.IGNORECASE)

    return text


def split_xml_into_blocks(text: str, blocks_per_chunk: int) -> Tuple[str, str, List[str], int]:
    matches = list(CONTENT_BLOCK_RE.finditer(text))
    if not matches:
        return text, "", [text], 0

    header = text[:matches[0].start()]
    footer = text[matches[-1].end():]
    blocks = [m.group(1) for m in matches]

    chunks: List[str] = []
    for i in range(0, len(blocks), blocks_per_chunk):
        chunks.append("\n".join(blocks[i:i + blocks_per_chunk]))

    return header, footer, chunks, len(blocks)


def build_glossary_prompt_section() -> str:
    """
    GLOSSARY 딕셔너리를 프롬프트용 텍스트로 변환한다.
    용어가 없으면 빈 문자열 반환.
    """
    if not GLOSSARY:
        return ""
    lines = ["[고유 용어 번역 규칙]",
             "아래 용어는 원문에 등장할 경우 반드시 지정된 한국어로 번역한다."]
    for src, dst in GLOSSARY.items():
        lines.append(f"  {src} → {dst}")
    lines.append("")
    return "\n".join(lines) + "\n"


def apply_glossary(text: str) -> str:
    """
    번역 결과에 GLOSSARY를 직접 치환하여 2차 보정한다.
    - 긴 표현을 먼저 처리(부분 매칭 방지)
    - 영어 단어 경계(\b) 기준으로 치환
    """
    if not GLOSSARY:
        return text
    sorted_items = sorted(GLOSSARY.items(), key=lambda x: len(x[0]), reverse=True)
    for src, dst in sorted_items:
        pattern = r'\b' + re.escape(src) + r'\b'
        text = re.sub(pattern, dst, text)
    return text


def build_prompt(content_chunk: str, filename: str, chunk_index: int, total_chunks: int) -> str:
    glossary_section = build_glossary_prompt_section()
    return f"""너는 발더스 게이트 3 모드 한글화 전문가다.
아래 XML <content> 블록들의 텍스트를 한국어로 번역한다.
원문은 영어가 아닐 수도 있다(포르투갈어 등). 어떤 언어든 반드시 한국어로 번역한다.

[파일 정보]
파일명: {filename} (진행률: {chunk_index}/{total_chunks})

[절대 규칙]
1) contentuid와 version 속성은 절대 수정하지 않는다.
2) <content> 태그 구조를 깨뜨리지 않는다. 블록 개수와 순서도 유지한다.
3) 원문에 &lt;br&gt;, &lt;span&gt; 같은 이스케이프 문자열 태그는 절대 <br>, <span>로 풀지 말고 그대로 유지한다.
4) 원문에 &lt;LSTag ...&gt; ... &lt;/LSTag&gt; 처럼 이스케이프된 LSTag도 절대 실제 태그 <LSTag ...>로 풀지 말고 그대로 유지한다.
   (즉, &lt;LSTag ...&gt;와 &lt;/LSTag&gt;는 그대로 두고, 그 사이 텍스트만 한국어로 번역한다.)
5) 설명, 주석, 마크다운 없이 번역된 <content> 블록들만 출력한다.

{glossary_section}[번역할 내용]
{content_chunk}
"""


def call_gemini_chunk(
    content_chunk: str,
    filename: str,
    chunk_index: int,
    total_chunks: int,
    api_key: str,
) -> Tuple[Optional[str], str]:
    prompt_text = build_prompt(content_chunk, filename, chunk_index, total_chunks)
    payload = {
        "contents": [{"parts": [{"text": prompt_text}]}],
        "generationConfig": {"temperature": 0.1},
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key,
    }

    last_status = "unknown"

    for model_name in MODELS_TO_TRY:
        url = f"{BASE_URL}/v1beta/models/{model_name}:generateContent"

        for attempt in range(1, 4):
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as resp:
                    result_json = json.loads(resp.read().decode("utf-8"))

                candidates = result_json.get("candidates", [])
                if not candidates:
                    last_status = f"no_candidates ({model_name})"
                    continue

                parts = candidates[0].get("content", {}).get("parts", [])
                if not parts:
                    last_status = f"no_parts ({model_name})"
                    continue

                translated = parts[0].get("text", "")
                translated = translated.replace("```xml", "").replace("```", "").strip()

                if translated.strip() == content_chunk.strip():
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
                    last_status = f"429 wait {wait}s ({model_name})"
                    print(f"        [!] 429 제한. {wait}초 대기 후 재시도 ({model_name})")
                    time.sleep(wait)
                    continue
                elif e.code == 404:
                    last_status = f"404 model not found ({model_name})"
                    break
                elif e.code >= 500:
                    wait = 5 * attempt
                    last_status = f"{e.code} server error wait {wait}s ({model_name})"
                    time.sleep(wait)
                    continue
                else:
                    last_status = f"HTTP {e.code} {e.reason} ({model_name}) {body[:200]}"
                    break

            except Exception as e:
                last_status = f"connection error: {e} ({model_name})"
                break

    return None, last_status


def process_xml_file(original_content: str, filename: str, api_key: str, log_file: str) -> str:
    matches = list(CONTENT_BLOCK_RE.finditer(original_content))
    total_blocks = len(matches)
    if total_blocks == 0:
        return original_content

    print(f"    -> 총 content 블록: {total_blocks}")

    # 다운시프트 전 단계가 전부 실패해도 부분 번역 결과를 보존하기 위한 변수
    last_header = ""
    last_footer = ""
    last_final_blocks: List[str] = []

    for blocks_per_chunk in DOWNSHIFT_STEPS:
        header, footer, chunks, _ = split_xml_into_blocks(original_content, blocks_per_chunk=blocks_per_chunk)
        if not chunks:
            return original_content

        print(f"    -> 청크 수: {len(chunks)} (요청블록 {blocks_per_chunk})")

        final_blocks: List[str] = []
        failed_hard = False

        for idx, chunk in enumerate(chunks, start=1):
            in_blocks = CONTENT_BLOCK_RE.findall(chunk)
            print(f"      ▶ 청크 번역 ({idx}/{len(chunks)}) - 입력 블록 {len(in_blocks)}개")

            protected_chunk, mapping = protect_escaped_tags(chunk)
            translated_chunk, status = call_gemini_chunk(protected_chunk, filename, idx, len(chunks), api_key)

            if translated_chunk is None:
                print(f"        ❌ 번역 실패. 원본 유지. 마지막 상태: {status}")
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"{filename} | 청크 {idx}/{len(chunks)} | 상태: {status}\n")
                final_blocks.extend(in_blocks)
                failed_hard = True
                continue

            translated_chunk = restore_escaped_tags(translated_chunk, mapping)
            translated_chunk = reescape_if_model_unescaped(translated_chunk)
            translated_chunk = apply_glossary(translated_chunk)  # 용어집 2차 보정

            out_blocks = CONTENT_BLOCK_RE.findall(translated_chunk)

            if not out_blocks:
                print("        ⚠️ 출력에서 content 블록을 찾지 못함. 원본 유지")
                final_blocks.extend(in_blocks)
                failed_hard = True
                continue

            if len(out_blocks) != len(in_blocks):
                print(f"        ⚠️ 블록 수 불일치: 입력 {len(in_blocks)} / 출력 {len(out_blocks)}. 원본 유지")
                final_blocks.extend(in_blocks)
                failed_hard = True
                continue

            print(f"        -> 성공: 출력 블록 {len(out_blocks)}개 ({status})")
            final_blocks.extend(out_blocks)

            time.sleep(1.5)

        # 이번 시도 결과를 보존 (다음 단계도 실패할 경우를 대비)
        last_header = header
        last_footer = footer
        last_final_blocks = list(final_blocks)

        if not failed_hard:
            body_text = "\n".join(final_blocks)
            return f"{header}{body_text}{footer}"

        print(f"    -> 다운시프트: 요청 블록 수를 {blocks_per_chunk}로 줄여도 완주 실패. 다음 단계로 진행")

    # 모든 다운시프트 단계가 실패해도 부분 번역 결과를 저장
    if last_final_blocks:
        print(f"    ⚠️ 최종 실패. 부분 번역 결과라도 저장합니다.")
        body_text = "\n".join(last_final_blocks)
        return f"{last_header}{body_text}{last_footer}"

    return original_content


def find_localization_folders(root_path: Path) -> List[Path]:
    return list(root_path.rglob("Localization"))


def has_korean_folder(loc_path: Path) -> bool:
    return (loc_path / "Korean").exists()


def list_source_language_dirs(loc_path: Path) -> List[Path]:
    if not loc_path.exists():
        return []

    src_dirs: List[Path] = []
    for p in loc_path.iterdir():
        if not p.is_dir():
            continue
        if p.name.lower() == "korean":
            continue
        src_dirs.append(p)

    src_dirs.sort(key=lambda x: x.name.lower())
    return src_dirs


def run(api_key: str, root_folder: str, log_file: str) -> None:
    root_path = Path(root_folder)
    print(f"[시작] 루트 경로: {root_path}")

    if not root_path.exists():
        print("❌ 경로를 찾을 수 없습니다. 경로를 다시 확인해주세요.")
        return

    loc_folders = find_localization_folders(root_path)
    print(f"총 {len(loc_folders)}개의 Localization 폴더를 발견했습니다.\n")

    if not loc_folders:
        print("⚠️ 처리할 Localization 폴더를 찾지 못했습니다.")
        print("   경로가 올바른지, bg3-modders-multitool로 모드를 언팩했는지 확인해주세요.")
        return

    for loc_path in loc_folders:
        print(f"📂 Localization 처리 중: {loc_path}")

        if SKIP_IF_KOREAN_EXISTS and has_korean_folder(loc_path):
            print("    - Korean 폴더가 이미 존재함. (한글화 완료로 간주) 스킵")
            print("-" * 50)
            continue

        src_dirs = list_source_language_dirs(loc_path)
        if not src_dirs:
            print("    - 하위 언어 폴더를 찾지 못함. 스킵")
            print("-" * 50)
            continue

        korean_path = loc_path / "Korean"
        korean_path.mkdir(parents=True, exist_ok=True)

        for src_dir in src_dirs:
            xml_files = list(src_dir.glob(INPUT_GLOB))
            if not xml_files:
                continue

            print(f"    - 원본 폴더: {src_dir.name} (XML {len(xml_files)}개)")

            for xml_file in xml_files:
                print(f"    ▶ 파일 처리: {xml_file.name}")

                try:
                    original = xml_file.read_text(encoding="utf-8", errors="strict")
                except UnicodeDecodeError:
                    original = xml_file.read_text(encoding="utf-8", errors="replace")

                if not original.strip():
                    print("      - 빈 파일. 스킵")
                    continue

                translated = process_xml_file(original, xml_file.name, api_key, log_file)

                out_file = korean_path / xml_file.name
                out_file.write_text(translated, encoding="utf-8")
                print(f"      ✅ 저장 완료: {out_file}")

        print("-" * 50)


if __name__ == "__main__":
    print("=" * 60)
    print("   BG3 모드 자동 한글화 스크립트")
    print("=" * 60)
    print()

    api_key, root_folder, log_file = setup_config()

    print(f"  API 키  : {api_key[:8]}...{api_key[-4:]} (확인용 앞뒤 일부만 표시)")
    print(f"  대상 경로: {root_folder}")
    print(f"  로그 파일: {log_file}")
    print()
    print("  위 설정으로 한글화를 시작합니다.")
    print("  (취소하려면 지금 창을 닫으세요)")
    print()
    input("  엔터를 누르면 시작합니다... ")
    print()

    run(api_key, root_folder, log_file)

    print("\n--- 작업 종료 ---")
    input("엔터 키를 누르면 종료합니다.")
