import os
import json
import time
import re
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Tuple, Optional


# =============================================================================
# BG3 모드 자동 한글화 스크립트 v2.1
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

# 번역 캐시 파일 경로
# 이미 번역한 텍스트를 저장해두고 재실행 시 재사용합니다.
# 비워두면 스크립트와 같은 폴더에 translation_cache.json 으로 저장
TRANSLATION_CACHE_FILE = ""

# Korean 폴더가 이미 있으면 한글화 완료로 간주하고 스킵
SKIP_IF_KOREAN_EXISTS = True

# ==========================================


# ==========================================
# [고급 설정] 건드리지 않아도 됩니다
# ==========================================
INPUT_GLOB = "*.xml"

# 토큰 기반 청크 설정
MAX_TOKENS_PER_CHUNK = 4000
DOWNSHIFT_TOKEN_STEPS = [4000, 2500, 1500, 800]

MODELS_TO_TRY = [
    "gemini-2.5-flash-lite",   # 1순위: 저비용
    "gemini-2.5-flash",         # 폴백
]

BASE_URL = "https://generativelanguage.googleapis.com"
TIMEOUT_SEC = 120
CONTENT_BLOCK_RE = re.compile(r"(<content\b[^>]*>.*?</content>)", re.DOTALL | re.IGNORECASE)
CONTENT_INNER_RE = re.compile(r"(<content\b[^>]*>)(.*?)(</content>)", re.DOTALL | re.IGNORECASE)
ESCAPED_TAGS = {"br", "span"}
# ==========================================


# ==========================================
# [용어집] 고유 용어 선번역 목록
# 형식: "원문": "번역어"
# - 프롬프트에 포함되어 Gemini에게 우선 번역을 지시
# - 번역 후 코드가 한 번 더 치환하여 확실하게 적용
# ==========================================
GLOSSARY = {
    # ──────────────────────────────────────
    # 동료 캐릭터
    # ──────────────────────────────────────
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
    # ──────────────────────────────────────
    # 주요 NPC / 세력 / 신
    # ──────────────────────────────────────
    "Raphael": "라파엘",
    "Mizora": "미조라",
    "Orin": "오린",
    "Gortash": "고타쉬",
    "The Emperor": "황제",
    "Mind Flayer": "마인드 플레이어",
    "Illithid": "일리시드",
    "Absolute": "절대자",
    "The Absolute": "절대자",
    "Chosen": "선택받은 자",
    "Withers": "위더스",
    "Vlaakith": "블라키스",
    "Cazador": "카자도르",
    "Isobel": "이소벨",
    "Dame Aylin": "에일린 경",
    "Elminster": "엘민스터",
    # 신
    "Myrkul": "미어쿨",
    "Bhaal": "바알",
    "Bane": "베인",
    "Mystra": "미스트라",
    "Shar": "샤",
    "Selune": "셀루네",
    "Lathander": "라샌더",
    "Lolth": "롤쓰",
    "Tyr": "티르",
    "Silvanus": "실바누스",
    "Tempus": "템퍼스",
    # 세력
    "Flaming Fist": "불주먹 용병대",
    "Zhentarim": "젠타림",
    "Harpers": "하퍼",
    "Emerald Grove": "에메랄드 숲",
    "Goblin": "고블린",
    "Githyanki": "기스양키",
    "Cambion": "캠비온",
    "Nautiloid": "노틸로이드",
    "Underdark": "언더다크",
    "Sword Coast": "소드 코스트",
    "Faerun": "페이룬",
    "Astral Plane": "아스트랄계",
    "Nine Hells": "나인 헬",
    # ──────────────────────────────────────
    # 종족
    # ──────────────────────────────────────
    "Human": "인간",
    "Elf": "엘프",
    "High Elf": "하이 엘프",
    "Wood Elf": "우드 엘프",
    "Drow": "드로우",
    "Lolth-Sworn Drow": "롤쓰 스원 드로우",
    "Seldarine Drow": "셀다린 드로우",
    "Tiefling": "티플링",
    "Asmodeus Tiefling": "아스모데우스 티플링",
    "Mephistopheles Tiefling": "메피스토펠레스 티플링",
    "Zariel Tiefling": "자리엘 티플링",
    "Dwarf": "드워프",
    "Gold Dwarf": "골드 드워프",
    "Shield Dwarf": "실드 드워프",
    "Duergar": "드웨가",
    "Halfling": "하플링",
    "Lightfoot Halfling": "라이트풋 하플링",
    "Strongheart Halfling": "스트롱하트 하플링",
    "Gnome": "노움",
    "Rock Gnome": "바위 노움",
    "Forest Gnome": "숲 노움",
    "Deep Gnome": "딥 노움",
    "Half-Elf": "하프엘프",
    "High Half-Elf": "하이 하프 엘프",
    "Wood Half-Elf": "우드 하프 엘프",
    "Drow Half-Elf": "드로우 하프 엘프",
    "Dragonborn": "드래곤본",
    "Half-Orc": "하프오크",
    # ──────────────────────────────────────
    # 능력치 (6대 스탯)
    # ──────────────────────────────────────
    "Strength": "근력",
    "Dexterity": "민첩",
    "Constitution": "건강",
    "Intelligence": "지능",
    "Wisdom": "지혜",
    "Charisma": "매력",
    # ──────────────────────────────────────
    # 직업
    # ──────────────────────────────────────
    # 바바리안
    "Barbarian": "바바리안",
    "Wildheart": "야생의심장",
    "Berserker": "광전사",
    "Wild Magic": "야생 마법",
    "Giant": "거인",
    # 바드
    "Bard": "바드",
    "College of Lore": "전승학파",
    "College of Valour": "용맹학파",
    "College of Swords": "검술학파",
    "College of Glamour": "요술학파",
    # 클레릭
    "Cleric": "클레릭",
    "Life Domain": "생명 권역",
    "Light Domain": "빛 권역",
    "Trickery Domain": "기만 권역",
    "Knowledge Domain": "지식 권역",
    "Nature Domain": "자연 권역",
    "Tempest Domain": "폭풍 권역",
    "War Domain": "전쟁 권역",
    "Death Domain": "죽음 권역",
    # 드루이드
    "Druid": "드루이드",
    "Circle of the Land": "땅의 회합",
    "Circle of the Moon": "달의 회합",
    "Circle of the Spores": "포자의 회합",
    "Circle of the Stars": "별의 회합",
    # 파이터
    "Fighter": "파이터",
    "Battle Master": "전투의 대가",
    "Eldritch Knight": "비술 기사",
    "Champion": "투사",
    "Arcane Archer": "비전 궁수",
    # 몽크
    "Monk": "몽크",
    "Way of the Four Elements": "사원소의 길",
    "Way of the Open Hand": "열린 손의 길",
    "Way of Shadow": "그림자의 길",
    "Way of the Drunken Master": "취권 달인의 길",
    # 팔라딘
    "Paladin": "팔라딘",
    "Oath of Devotion": "헌신의 맹세",
    "Oath of the Ancients": "선조의 맹세",
    "Oath of Vengeance": "복수의 맹세",
    "Oath of the Crown": "왕관의 맹세",
    "Oathbreaker": "맹세파기자",
    # 레인저
    "Ranger": "레인저",
    "Hunter": "사냥꾼",
    "Beast Master": "야수 조련사",
    "Gloom Stalker": "어둠 추척자",
    "Swarmkeeper": "무리지기",
    # 로그
    "Rogue": "로그",
    "Thief": "도둑",
    "Arcane Trickster": "비전 괴도",
    "Assassin": "암살자",
    "Swashbuckler": "칼잡이",
    # 소서러
    "Sorcerer": "소서러",
    "Draconic Bloodline": "용의 혈통",
    "Storm Sorcery": "폭풍 술사",
    "Shadow Magic": "그림자 마법",
    # 워락
    "Warlock": "워락",
    "The Fiend": "마족",
    "The Great Old One": "고대의 지배자",
    "The Archfey": "대요정",
    "The Hexblade": "주술 칼날",
    "Hexblade": "주술 칼날",
    "Pact of the Chain": "사슬의 계약",
    "Pact of the Blade": "검의 계약",
    "Pact of the Tome": "장서의 계약",
    # 위저드
    "Wizard": "위저드",
    "Bladesinging": "칼날 노래",
    "Bladesinger": "칼날 노래",
    # ──────────────────────────────────────
    # 주문 학파 (긴 표현 먼저 - 부분 매칭 방지)
    # ──────────────────────────────────────
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
    # ──────────────────────────────────────
    # 주문명 (자주 등장하는 것들)
    # ──────────────────────────────────────
    "Fireball": "화염구",
    "Lightning Bolt": "번개 줄기",
    "Haste": "가속",
    "Slow": "둔화",
    "Invisibility": "투명화",
    "Greater Invisibility": "상위 투명화",
    "Misty Step": "안개 걸음",
    "Thunderwave": "천둥파",
    "Animate Dead": "망자 조종",
    "Speak with Dead": "망자와 대화",
    "Polymorph": "변신",
    "Counterspell": "주문 방해",
    "Bless": "축복",
    "Hex": "주술",
    "Healing Word": "치유의 단어",
    "Cure Wounds": "상처 치유",
    "Revivify": "생환",
    "Shield of Faith": "신념의 보호막",
    "Spirit Guardians": "영혼의 수호자",
    "Eldritch Blast": "섬뜩한 작렬",
    "Magic Missile": "마법의 화살",
    "Mage Hand": "마법사의 손",
    "Sacred Flame": "신성한 불꽃",
    "Guidance": "인도",
    "Darkness": "어둠",
    "Daylight": "일광",
    "Dispel Magic": "마법 해제",
    "Hold Person": "인물 속박",
    "Hold Monster": "괴물 속박",
    "Dimension Door": "차원문",
    "Fly": "비행",
    "Feather Fall": "깃털 낙하",
    "Knock": "개방",
    "Pass Without Trace": "흔적 없는 이동",
    "Silence": "침묵",
    "Smite": "강타",
    "Divine Smite": "신성 강타",
    "Sneak Attack": "급소 공격",
    "Wild Shape": "야생 변신",
    "Rage": "격노",
    "Action Surge": "행동 쇄도",
    "Second Wind": "재기",
    "Lay on Hands": "레이온핸즈",
    "Bardic Inspiration": "바드의 영감",
    "Channel Divinity": "신성한 도관",
    "Ki": "기",
    "Sorcery Points": "소서리 점수",
    "Metamagic": "초마법",
    # ──────────────────────────────────────
    # 전투 / 시스템 용어
    # ──────────────────────────────────────
    "Attack Rolls": "공격 굴림",
    "Attack Roll": "공격 굴림",
    "attack rolls": "공격 굴림",
    "attack roll": "공격 굴림",
    "Saving Throws": "내성 굴림",
    "Saving Throw": "내성 굴림",
    "saving throws": "내성 굴림",
    "saving throw": "내성 굴림",
    "Damage Roll": "피해 굴림",
    "Damage Rolls": "피해 굴림",
    "Ability Check": "능력 판정",
    "Ability Checks": "능력 판정",
    "Armor Class": "방어도",
    "Armour Class": "방어도",
    "Hit Points": "체력",
    "Hit Dice": "생명력 주사위",
    "Proficiency": "숙련",
    "Proficiency Bonus": "숙련 보너스",
    "Expertise": "통달",
    "Advantage": "유리",
    "Disadvantage": "불리",
    "Concentration": "집중",
    "Bonus Action": "추가 행동",
    "Bonus Actions": "추가 행동",
    "Reaction": "반응",
    "Reactions": "반응",
    "Critical Hit": "치명타",
    "Critical Hits": "치명타",
    "Inspiration": "영감",
    "Initiative": "선제권",
    "Spell Slot": "주문 슬롯",
    "Spell Slots": "주문 슬롯",
    "Spell Save DC": "주문 내성 난이도",
    "Difficulty Class": "난이도",
    "Cantrip": "소마법",
    "Cantrips": "소마법",
    "Ritual": "의식",
    "Short Rest": "짧은 휴식",
    "Long Rest": "긴 휴식",
    "Camp": "야영지",
    "Multiclassing": "멀티 클래싱",
    "Finesse": "기교",
    "Versatile": "다용도",
    "Two-Handed": "양손",
    "Light Armor": "경갑",
    "Medium Armor": "평갑",
    "Heavy Armor": "중갑",
    "Shield": "방패",
    "Feat": "재주",
    "Feats": "재주",
    "Background": "배경",
    # ──────────────────────────────────────
    # 상태이상 / 상태 효과
    # ──────────────────────────────────────
    "Prone": "쓰러짐",
    "Stunned": "기절",
    "Frightened": "공포",
    "Charmed": "매혹",
    "Poisoned": "중독",
    "Blinded": "실명",
    "Deafened": "귀먹음",
    "Restrained": "속박",
    "Paralyzed": "마비",
    "Petrified": "석화",
    "Incapacitated": "행동불능",
    "Invisible": "투명",
    "Exhaustion": "피로",
    "Burning": "불타는",
    "Bleeding": "출혈",
    "Blessed": "축복받은",
    "Cursed": "저주받은",
    "Sleeping": "수면",
    "Entangled": "얽힘",
    # ──────────────────────────────────────
    # 피해 유형
    # ──────────────────────────────────────
    "Fire Damage": "화염 피해",
    "Cold Damage": "냉기 피해",
    "Lightning Damage": "번개 피해",
    "Thunder Damage": "천둥 피해",
    "Radiant Damage": "광휘 피해",
    "Necrotic Damage": "괴저 피해",
    "Psychic Damage": "정신 피해",
    "Poison Damage": "독 피해",
    "Acid Damage": "산 피해",
    "Force Damage": "역장 피해",
    "Bludgeoning Damage": "타격 피해",
    "Piercing Damage": "관통 피해",
    "Slashing Damage": "참격 피해",
    "Healing": "치유",
    "Temporary Hit Points": "임시 체력",
    # 피해 유형 단독 (짧은 형태)
    "Radiant": "광휘",
    "Necrotic": "괴저",
    "Psychic": "정신",
    "Bludgeoning": "타격",
    "Piercing": "관통",
    "Slashing": "참격",
    # ──────────────────────────────────────
    # 기술 (Skills)
    # ──────────────────────────────────────
    "Acrobatics": "곡예",
    "Animal Handling": "동물 조련",
    "Arcana": "비전학",
    "Athletics": "운동",
    "Deception": "기만",
    "History": "역사",
    "Insight": "통찰",
    "Intimidation": "위협",
    "Investigation": "수사",
    "Medicine": "의학",
    "Nature": "자연",
    "Perception": "인지",
    "Performance": "연행",
    "Persuasion": "설득",
    "Religion": "종교",
    "Sleight of Hand": "손재주",
    "Stealth": "은신",
    "Survival": "생존",
    # ──────────────────────────────────────
    # 기타 게임 용어
    # ──────────────────────────────────────
    "Darkvision": "암시야",
    "Superior Darkvision": "상위 암시야",
    "Resistance": "저항",
    "Immunity": "면역",
    "Vulnerability": "취약",
    "Familiar": "패밀리어",
    "Companion": "동료",
    "Tadpole": "올챙이",
    "Ceremorphosis": "세레모포시스",
    "Elder Brain": "엘더 브레인",
    "Psionic": "사이오닉",
}
# ==========================================


# ==========================================
# [번역 캐시]
# ==========================================
_translation_cache: Optional[dict] = None
_cache_dirty: bool = False


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


# ==========================================
# [로컬 번역] API 없이 처리
# ==========================================
_SKIP_PATTERNS = re.compile(
    r"^("
    r"\d+[\d.,/%+\-*x ]*"
    r"|[+\-]\d+.*"
    r"|\d+[dD]\d+.*"
    r"|[A-Z_]{2,}"
    r"|<[^>]+>"
    r")$"
)


def should_skip_translation(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    korean_chars = sum(1 for c in stripped if '\uAC00' <= c <= '\uD7A3')
    total_chars = sum(1 for c in stripped if not c.isspace())
    if total_chars > 0 and korean_chars / total_chars >= 0.5:
        return True
    if _SKIP_PATTERNS.match(stripped):
        return True
    return False


def try_glossary_only(text: str) -> Optional[str]:
    stripped = text.strip()
    if stripped in GLOSSARY:
        return GLOSSARY[stripped]
    for src, dst in GLOSSARY.items():
        if stripped.lower() == src.lower():
            return dst
    return None


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


# ==========================================
# [태그 보호]
# ==========================================
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


# ==========================================
# [용어집 유틸]
# ==========================================
def build_glossary_prompt_section() -> str:
    if not GLOSSARY:
        return ""
    lines = ["[고유 용어 번역 규칙]",
             "아래 용어는 원문에 등장할 경우 반드시 지정된 한국어로 번역한다."]
    for src, dst in GLOSSARY.items():
        lines.append(f"  {src} -> {dst}")
    lines.append("")
    return "\n".join(lines) + "\n"


def apply_glossary(text: str) -> str:
    if not GLOSSARY:
        return text
    for src, dst in sorted(GLOSSARY.items(), key=lambda x: len(x[0]), reverse=True):
        text = re.sub(r'\b' + re.escape(src) + r'\b', dst, text)
    return text


# ==========================================
# [Gemini API - 경량 포맷 + systemInstruction + thinking off]
# ==========================================
_SYSTEM_INSTRUCTION: Optional[str] = None


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
                api_key: str) -> Tuple[Optional[str], str]:
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
                    time.sleep(wait)
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


# ==========================================
# [설정]
# ==========================================
def setup_config() -> Tuple[str, str, str, str]:
    """
    API 키, 경로, 로그 파일 경로, 캐시 파일 경로를 확정한다.
    코드에 직접 입력된 값이 없으면 실행 시 사용자에게 입력받는다.
    """
    # --- API 키 확정 ---
    api_key = API_KEY.strip()

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
        script_dir = Path(__file__).parent
        log_file = str(script_dir / "translation_errors.txt")

    # --- 캐시 파일 경로 확정 ---
    cache_file = TRANSLATION_CACHE_FILE.strip()
    if not cache_file:
        script_dir = Path(__file__).parent
        cache_file = str(script_dir / "translation_cache.json")

    return api_key, root_folder, log_file, cache_file


# ==========================================
# [번역 파이프라인]
# ==========================================
def process_xml_file(original_content: str, filename: str,
                     api_key: str, log_file: str) -> str:
    matches = list(CONTENT_BLOCK_RE.finditer(original_content))
    total_blocks = len(matches)
    if total_blocks == 0:
        return original_content

    all_blocks = []
    for m in matches:
        full = m.group(1)
        open_tag, inner, close_tag = extract_block_parts(full)
        all_blocks.append((full, open_tag, inner, close_tag))

    # 중복 제거
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
    print(f"    -> 총 블록: {total_blocks} (고유: {unique_count}, 중복 제거: {dedup_saved})")

    if unique_count == 0:
        return original_content

    # ── 1단계: 로컬 처리 ──
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
    print(f"    -> 로컬: 캐시 {stats_cache} + 스킵 {stats_skip} + 글로서리 {stats_glossary} = {local_total}개")
    print(f"    -> API 필요: {len(need_api)}개")

    # ── 2단계: API 호출 ──
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
            print(f"    -> 청크 수: {len(chunks)} (토큰한도 {max_tokens}, 미번역 {len(remaining)}개)")

            failed_hard = False
            for cidx, chunk in enumerate(chunks, start=1):
                ctokens = sum(estimate_tokens(t) for _, t, _, _ in chunk)
                print(f"      ▶ 청크 ({cidx}/{len(chunks)}) - {len(chunk)}개 (~{ctokens}토큰)")

                lines = []
                for idx, protected, _, _ in chunk:
                    lines.append(f"{idx}|{protected.replace(chr(10), chr(92) + 'n')}")

                raw, status = call_gemini("\n".join(lines), filename, cidx, len(chunks), api_key)

                if raw is None:
                    print(f"        ❌ 실패: {status}")
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(f"{filename} | 청크 {cidx}/{len(chunks)} | {status}\n")
                    failed_hard = True
                    continue

                parsed = parse_response(raw, len(chunk))
                if parsed is None:
                    print(f"        ⚠️ 파싱 실패. 원본 유지")
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
                print(f"        -> 성공: {ok}/{len(chunk)}개 ({status})")
                time.sleep(1.5)

            if not failed_hard:
                break
            print(f"    -> 다운시프트 진행")

    # ── 3단계: 최종 조립 ──
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
    print(f"    -> 최종: {done}/{total_blocks} 블록 번역 완료")

    return header + "\n".join(final_blocks) + footer


# ==========================================
# [폴더 탐색]
# ==========================================
def find_localization_folders(root_path: Path) -> List[Path]:
    return list(root_path.rglob("Localization"))


def has_korean_folder(loc_path: Path) -> bool:
    return (loc_path / "Korean").exists()


def list_source_language_dirs(loc_path: Path) -> List[Path]:
    if not loc_path.exists():
        return []
    src_dirs = [p for p in loc_path.iterdir() if p.is_dir() and p.name.lower() != "korean"]
    src_dirs.sort(key=lambda x: (0 if x.name.lower() == "english" else 1, x.name.lower()))
    return src_dirs


def is_already_korean(text: str) -> bool:
    blocks = CONTENT_BLOCK_RE.findall(text)
    if not blocks:
        return False
    inner_text = ""
    for block in blocks:
        m = re.search(r">([^<]*)</content>", block, re.IGNORECASE)
        if m:
            inner_text += m.group(1)
    clean = re.sub(r"&[a-zA-Z]+;", "", inner_text)
    clean = re.sub(r"\s+", "", clean)
    if len(clean) < 10:
        return False
    korean_chars = sum(1 for c in clean if '\uAC00' <= c <= '\uD7A3' or '\u3131' <= c <= '\u318E')
    return korean_chars / len(clean) >= 0.3


# ==========================================
# [실행]
# ==========================================
def run(api_key: str, root_folder: str, log_file: str, cache_file: str) -> None:
    load_translation_cache(cache_file)

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

        # English 우선, 첫 번째 언어 폴더만 사용 (중복 번역 방지)
        src_dir = src_dirs[0]
        if len(src_dirs) > 1:
            print(f"    - 언어 폴더 {len(src_dirs)}개. '{src_dir.name}'을 소스로 사용")

        xml_files = list(src_dir.glob(INPUT_GLOB))
        if not xml_files:
            print("-" * 50)
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

            if is_already_korean(original):
                print("      - 이미 한글화된 파일. 스킵")
                continue

            translated = process_xml_file(original, xml_file.name, api_key, log_file)

            out_file = korean_path / xml_file.name
            out_file.write_text(translated, encoding="utf-8")
            print(f"      ✅ 저장 완료: {out_file}")

        print("-" * 50)

    save_translation_cache(cache_file)
    cache = load_translation_cache(cache_file)
    print(f"\n💾 번역 캐시: {len(cache)}개 항목 저장됨")


if __name__ == "__main__":
    print("=" * 60)
    print("   BG3 모드 자동 한글화 스크립트 v2.1")
    print("=" * 60)
    print()

    api_key, root_folder, log_file, cache_file = setup_config()

    print(f"  API 키  : {api_key[:8]}...{api_key[-4:]} (확인용 앞뒤 일부만 표시)")
    print(f"  대상 경로: {root_folder}")
    print(f"  로그 파일: {log_file}")
    print(f"  캐시 파일: {cache_file}")
    print()
    print("  위 설정으로 한글화를 시작합니다.")
    print("  (취소하려면 지금 창을 닫으세요)")
    print()
    input("  엔터를 누르면 시작합니다... ")
    print()

    run(api_key, root_folder, log_file, cache_file)

    print("\n--- 작업 종료 ---")
    input("엔터 키를 누르면 종료합니다.")
