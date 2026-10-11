import re

__version__ = "7.3"

INPUT_GLOB = "*.xml"

MAX_TOKENS_PER_CHUNK = 4000
DOWNSHIFT_TOKEN_STEPS = [4000, 2500, 1500, 800]

MODELS_TO_TRY = [
    "gemini-3.5-flash-lite",   # 1순위: 최신 경량 stable
    "gemini-3.1-flash-lite",   # 폴백 (2027-05-07 종료 예정)
]

# 번역 탭 드롭다운에 기본 체인 외에 추가로 노출하는 모델.
EXTRA_MODEL_OPTIONS = [
    "gemini-3.8-flash",        # 속도·품질 균형 (GA)
    "gemini-3.1-pro-preview",  # 최고 품질 (preview)
]

# 개발자 API에서 신규 사용자 접근이 막힌 구세대 모델 접두어.
# 저장된 설정에 남아 있으면 불러올 때 걸러낸다.
RETIRED_MODEL_PREFIXES = ("gemini-2.", "gemini-1.")

BASE_URL = "https://generativelanguage.googleapis.com"
TIMEOUT_SEC = 120
# self-closing(<content ... />)과 일반(<content ...>...</content>) 둘 다 매칭.
# self-closing을 별도 매칭으로 분리하지 않으면 그 직후의 다른 블록과 합쳐져
# inner 추출이 어긋나고 번역 결과 XML이 깨진다 (예: DBW의 빈 핸들 다음에 오는
# "1 Star Dragonball Found" 번역이 self-closing 직후로 잘못 끼어듦).
CONTENT_BLOCK_RE = re.compile(
    r"(<content\b[^/>]*(?:/\s*>|>.*?</content>))",
    re.DOTALL | re.IGNORECASE,
)
CONTENT_INNER_RE = re.compile(r"(<content\b[^>]*>)(.*?)(</content>)", re.DOTALL | re.IGNORECASE)
ESCAPED_TAGS = {"br", "span"}

CONTENTUID_RE = re.compile(r'contentuid="([^"]*)"', re.IGNORECASE)
