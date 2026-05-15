import re

INPUT_GLOB = "*.xml"

MAX_TOKENS_PER_CHUNK = 4000
DOWNSHIFT_TOKEN_STEPS = [4000, 2500, 1500, 800]

MODELS_TO_TRY = [
    "gemini-3.1-flash-lite",   # 1순위: 최신 stable (2027-05-07까지)
    "gemini-2.5-flash-lite",   # 폴백 (2026-10-16까지)
]

BASE_URL = "https://generativelanguage.googleapis.com"
TIMEOUT_SEC = 120
CONTENT_BLOCK_RE = re.compile(r"(<content\b[^>]*>.*?</content>)", re.DOTALL | re.IGNORECASE)
CONTENT_INNER_RE = re.compile(r"(<content\b[^>]*>)(.*?)(</content>)", re.DOTALL | re.IGNORECASE)
ESCAPED_TAGS = {"br", "span"}

CONTENTUID_RE = re.compile(r'contentuid="([^"]*)"', re.IGNORECASE)
