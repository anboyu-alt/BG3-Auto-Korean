"""MCM 처리기에서 사용하는 화이트리스트·블랙리스트 상수."""

from __future__ import annotations

import re

BLUEPRINT_TRANSLATABLE_KEYS = frozenset({
    "ModName",
    "TabName",
    "TabDescription",
    "SectionName",
    "SectionDescription",
    "Name",
    "Description",
    "Tooltip",
    "Label",
    "Title",
    "Message",
    "ConfirmText",
    "CancelText",
})

BLUEPRINT_NEVER_TOUCH_KEYS = frozenset({
    "Id",
    "TabId",
    "SectionId",
    "SettingId",
    "Type",
    "Default",
    "Operator",
    "ExpectedValue",
    "Min",
    "Max",
    "Step",
    "SchemaVersion",
    "Optional",
    "VisibleIf",
    "Handles",
    "NameHandle",
    "DescriptionHandle",
    "TooltipHandle",
    "LabelHandle",
})

# 각 *Handle 키가 보호하는 평문 필드들. NameHandle은 노드 타입에 따라
# Name/TabName/SectionName/ModName 등 다양한 이름을 보호한다.
BLUEPRINT_HANDLE_PROTECTIONS = {
    "NameHandle": frozenset({"Name", "TabName", "SectionName", "ModName"}),
    "DescriptionHandle": frozenset({"Description", "TabDescription", "SectionDescription"}),
    "TooltipHandle": frozenset({"Tooltip"}),
    "LabelHandle": frozenset({"Label"}),
}

LUA_WIDGET_PATTERNS = (
    ("AddText", re.compile(r':AddText\(\s*"((?:[^"\\]|\\.)*)"\s*\)')),
    ("AddButton", re.compile(r':AddButton\(\s*"((?:[^"\\]|\\.)*)"\s*\)')),
    ("AddCollapsingHeader", re.compile(r':AddCollapsingHeader\(\s*"((?:[^"\\]|\\.)*)"\s*\)')),
    ("AddInputTextLabel", re.compile(r':AddInputText\(\s*"((?:[^"\\]|\\.)*)"\s*,')),
    ("AddInputTextInit", re.compile(r':AddInputText\(\s*"[^"]*"\s*,\s*"((?:[^"\\]|\\.)*)"\s*\)')),
    ("Hint", re.compile(r'\.Hint\s*=\s*"((?:[^"\\]|\\.)*)"')),
    ("Text", re.compile(r'\.Text\s*=\s*"((?:[^"\\]|\\.)*)"')),
    # string.format("...") 첫 인자 — 동적 텍스트의 포맷 문자열
    ("StringFormat", re.compile(r'string\.format\(\s*"((?:[^"\\]|\\.)*)"')),
)

# string.format 포맷 specifier — Gemini 번역 후 보존됐는지 검증용
LUA_FORMAT_SPECIFIER_RE = re.compile(r'%[#0\-+ ]?\d*\.?\d*[diouxXeEfgGsqc%]')

LUA_OPTIONS_RE = re.compile(r'(\w+)\.Options\s*=\s*\{([^}]*)\}')
LUA_OPTION_ITEM_RE = re.compile(r'"((?:[^"\\]|\\.)*)"')

# 자동 처리 시 제외할 패턴 — 이 문자열은 코드 식별자이므로 번역하면 안 됨
LUA_SKIP_PATTERNS = (
    re.compile(r'^##'),                          # IMGUI 내부 ID
    re.compile(r'[A-Z][a-zA-Z]+_[A-Z]'),         # 네트워크 채널 이름 (Foo_Bar)
    re.compile(r'^(Text|Button|FrameBg|TableRowBg|TableRowBgAlt|Header|Border)$'),
    re.compile(r'^\.[a-z]+$'),                   # 파일 확장자
)

# 비교 키로 자주 쓰이는 짧은 단어 — 자동 치환 제외, 라벨 맵으로 분리
LUA_SHORT_KEY_WORDS = frozenset({
    "All", "Default", "Root", "Local", "Vanilla",
    "Hidden", "On Hover", "Alt-Highlight",
    "Edited", "Status", "Icon", "Visibility",
    "Display Name", "Internal Name",
    "Lootable", "Not Lootable",
    "Containers Only", "Non-Containers",
    "Vanilla Only", "Modded Only",
    "Edited Only", "Unedited Only",
    "Hidden (0)", "On Hover (1)", "Alt-Highlight (2)",
})


def is_lua_skippable(text: str) -> bool:
    """자동 치환에서 제외해야 하는 식별자성 문자열인지."""
    for pat in LUA_SKIP_PATTERNS:
        if pat.search(text):
            return True
    return False


def is_lua_short_key(text: str) -> bool:
    """라벨 맵 후보(비교 키 가능성 높은 짧은 단어)인지."""
    return text in LUA_SHORT_KEY_WORDS
