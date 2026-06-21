import re

__version__ = "6.0"

INPUT_GLOB = "*.xml"

MAX_TOKENS_PER_CHUNK = 4000
DOWNSHIFT_TOKEN_STEPS = [4000, 2500, 1500, 800]

MODELS_TO_TRY = [
    "gemini-3.1-flash-lite",   # 1순위: 최신 stable (2027-05-07까지)
    "gemini-2.5-flash-lite",   # 폴백 (2026-10-16까지)
]

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
