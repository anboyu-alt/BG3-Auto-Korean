# BG3 Mod Translator — GUI 재설계 (PySide6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `bg3gui/`를 customtkinter에서 PySide6로 완전 재작성. BG3 앰버 테마, 커스텀 타이틀바, 사이드바 내비게이션, 앱 UI i18n(ko/en), 앱 이름 BG3 Mod Translator.

**Architecture:** `bg3core/`는 변경 없음. `bg3gui/`를 PySide6 기반으로 교체. FramelessWindow + 골드 그라디언트 커스텀 타이틀바 + 96px 사이드바 + QStackedWidget 탭 전환. i18n 패키지(`bg3gui/i18n/`)로 ko/en UI 문자열 관리. `config.app_language: str = "ko"` 신규 필드.

**Tech Stack:** Python 3.14, PySide6 6.x (LGPL), bg3core (unchanged), pytest

---

## 사전 준비

```bash
pip install PySide6
```

`bg3gui/widgets/log_view.py`와 `bg3gui/widgets/progress_panel.py`는 customtkinter 기반이므로 이번 작업에서 PySide6 버전으로 교체한다.

---

## File Map

**신규:**
- `bg3gui/theme.py`
- `bg3gui/i18n/__init__.py`
- `bg3gui/i18n/ko.py`
- `bg3gui/i18n/en.py`
- `bg3gui/titlebar.py`
- `bg3gui/sidebar.py`
- `bg3_mod_translator.py`
- `tests/test_i18n.py`
- `tests/test_theme.py`

**재작성 (PySide6로 교체):**
- `bg3gui/app.py`
- `bg3gui/workers.py`
- `bg3gui/widgets/path_picker.py`
- `bg3gui/settings_tab.py`
- `bg3gui/translate_tab.py`
- `bg3gui/reviewer_tab.py`
- `bg3gui/glossary_tab.py`
- `bg3gui/widgets/log_view.py`
- `bg3gui/widgets/progress_panel.py`

**수정:**
- `bg3core/config.py` — `app_language: str = "ko"` 추가
- `bg3gui/i18n.py` — 삭제 (기능이 `bg3gui/i18n/` 패키지로 이동)
- `bg3_autokorean_gui.py` — 신규 진입점으로 리디렉션

---

### Task 1: Foundation — theme, i18n, config

**Files:**
- Create: `bg3gui/theme.py`
- Create: `bg3gui/i18n/__init__.py`
- Create: `bg3gui/i18n/ko.py`
- Create: `bg3gui/i18n/en.py`
- Delete: `bg3gui/i18n.py` (기존 customtkinter i18n)
- Modify: `bg3core/config.py`
- Create: `tests/test_i18n.py`
- Create: `tests/test_theme.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_i18n.py
import importlib, sys

def _reload_i18n():
    for mod in list(sys.modules.keys()):
        if "bg3gui.i18n" in mod:
            del sys.modules[mod]

def test_t_returns_korean_by_default():
    _reload_i18n()
    from bg3gui.i18n import load, t
    load("ko")
    assert t("menu.translate") == "번역"

def test_t_returns_english():
    _reload_i18n()
    from bg3gui.i18n import load, t
    load("en")
    assert t("menu.translate") == "Translate"

def test_t_falls_back_to_key():
    _reload_i18n()
    from bg3gui.i18n import load, t
    load("ko")
    assert t("nonexistent.key") == "nonexistent.key"

def test_t_format_kwargs():
    _reload_i18n()
    from bg3gui.i18n import load, t
    load("ko")
    result = t("translate.progress", current=3, total=7, pct=42)
    assert "3" in result and "7" in result and "42" in result


# tests/test_theme.py
def test_app_stylesheet_is_string():
    from bg3gui.theme import app_stylesheet
    css = app_stylesheet()
    assert isinstance(css, str)
    assert len(css) > 100

def test_color_constants_are_hex():
    import bg3gui.theme as theme
    for name in ["BG_APP", "BG_SIDEBAR", "GOLD", "GOLD_LIGHT", "TEXT_PRIMARY"]:
        val = getattr(theme, name)
        assert val.startswith("#"), f"{name} should be hex color, got {val}"
```

- [ ] **Step 2: Run tests — expect ImportError**

```
python -m pytest tests/test_i18n.py tests/test_theme.py -v
```

- [ ] **Step 3: Delete old `bg3gui/i18n.py`**

```bash
rm bg3gui/i18n.py
```

- [ ] **Step 4: Create `bg3gui/theme.py`**

```python
# bg3gui/theme.py
BG_APP = "#1e1e1e"
BG_SIDEBAR = "#151515"
BG_CARD = "#2a2a2a"
BG_LOG = "#111111"
GOLD = "#d4a843"
GOLD_LIGHT = "#e8b840"
GOLD_DARK = "#c49a30"
HEADER_GRAD_START = "#1a1400"
HEADER_GRAD_END = "#2d2100"
DIVIDER = "#2a2a2a"
TEXT_PRIMARY = "#cccccc"
TEXT_SECONDARY = "#888888"
TEXT_MUTED = "#555555"
SUCCESS = "#4a9a4a"
CLOSE_BG = "#5a1a1a"


def app_stylesheet() -> str:
    return f"""
QWidget {{
    background-color: {BG_APP};
    color: {TEXT_PRIMARY};
    font-family: "Malgun Gothic", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QLineEdit, QComboBox {{
    background-color: {BG_CARD};
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    padding: 7px 10px;
    color: {TEXT_PRIMARY};
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {GOLD};
}}
QPlainTextEdit {{
    background-color: {BG_LOG};
    border: 1px solid {DIVIDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 6px;
}}
QPushButton {{
    background-color: {BG_CARD};
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    padding: 8px 14px;
    color: {TEXT_SECONDARY};
}}
QPushButton:hover {{
    border-color: {GOLD};
    color: {TEXT_PRIMARY};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    border-color: #2a2a2a;
}}
QPushButton#btn_start {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {GOLD_DARK}, stop:1 {GOLD_LIGHT});
    color: #1a1000;
    font-weight: bold;
    border: none;
    font-size: 13px;
}}
QPushButton#btn_start:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {GOLD_LIGHT}, stop:1 #f0c060);
}}
QPushButton#btn_start:disabled {{
    background: #3a3a2a;
    color: #666;
}}
QProgressBar {{
    background-color: {BG_CARD};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {GOLD_DARK}, stop:1 {GOLD_LIGHT});
    border-radius: 4px;
}}
QScrollBar:vertical {{
    background: {BG_CARD};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #444;
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid #444;
    border-radius: 3px;
    background: {BG_CARD};
}}
QCheckBox::indicator:checked {{
    background: {GOLD};
    border-color: {GOLD};
    image: none;
}}
QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}
QLabel#label_muted {{
    color: {TEXT_MUTED};
    font-size: 11px;
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {BG_CARD};
    border: 1px solid #3a3a3a;
    selection-background-color: #3a2800;
    color: {TEXT_PRIMARY};
    outline: none;
}}
QTreeWidget {{
    background: {BG_LOG};
    border: 1px solid {DIVIDER};
    border-radius: 4px;
    color: {TEXT_PRIMARY};
    alternate-background-color: #1a1a1a;
}}
QTreeWidget::item:selected {{
    background: #3a2800;
    color: {GOLD};
}}
QTreeWidget QHeaderView::section {{
    background: {BG_CARD};
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 1px solid {DIVIDER};
    padding: 5px 8px;
    font-weight: bold;
}}
QFrame#divider {{
    background: {DIVIDER};
    max-height: 1px;
    min-height: 1px;
}}
"""
```

- [ ] **Step 5: Create `bg3gui/i18n/ko.py`**

```python
# bg3gui/i18n/ko.py
STRINGS = {
    "app.title": "BG3 MOD TRANSLATOR",
    "app.subtitle": "Powered by Gemini AI · v5.0",
    "menu.settings": "설정",
    "menu.translate": "번역",
    "menu.review": "검수",
    "menu.glossary": "용어집",
    "translate.file_label": "PAK 파일 / 폴더",
    "translate.browse": "찾기",
    "translate.target_lang": "번역 대상 언어",
    "translate.model": "AI 모델",
    "translate.start": "▶  번역 시작",
    "translate.pause": "⏸",
    "translate.stop": "⏹",
    "translate.log_header": "TRANSLATION LOG",
    "translate.log_clear": "지우기",
    "translate.progress": "{current} / {total} 파일 · {pct}%",
    "translate.done": "✅ 번역 완료!",
    "translate.cancelled": "⏹ 중단됨",
    "translate.error": "❌ 오류 발생",
    "translate.status.translating": "▶ {file} 처리 중 — {done}/{total}",
    "translate.status.idle": "대기 중",
    "translate.confirm_stop": "번역을 중단하시겠습니까?",
    "settings.title": "설정",
    "settings.api_key": "Gemini API Key",
    "settings.show": "표시",
    "settings.hide": "숨김",
    "settings.divine_path": "Divine.exe 경로",
    "settings.model_1": "AI 모델 1순위",
    "settings.model_2": "AI 모델 2순위",
    "settings.ui_scale": "UI 배율",
    "settings.target_language": "번역 대상 언어",
    "settings.app_language": "앱 UI 언어",
    "settings.cache_path": "번역 캐시 파일",
    "settings.skip_existing": "번역 완료된 PAK 건너뛰기",
    "settings.mcm_enabled": "MCM 자동 처리",
    "settings.save": "저장",
    "settings.test_api": "API 테스트",
    "settings.api_ok": "✅ API 연결 성공",
    "settings.api_fail": "❌ API 오류: {err}",
    "settings.saved": "✅ 저장됨",
    "settings.lang_restart": "앱 UI 언어가 변경됐습니다. 앱을 재시작하면 적용됩니다.",
    "review.pak_label": "검수할 PAK",
    "review.open": "열기",
    "review.files": "파일 목록",
    "review.source_lang": "영어 원문",
    "review.target_lang": "번역",
    "review.prev": "◀ 이전",
    "review.next": "다음 ▶",
    "review.save": "저장 (Ctrl+S)",
    "review.modified_only": "수정 항목만 보기",
    "review.all": "전체 보기",
    "review.nav": "항목 {idx} / {total}",
    "review.none": "항목 없음",
    "review.saved_ok": "검수 PAK 저장 완료:\n{path}",
    "glossary.search_placeholder": "영어 또는 한국어로 검색...",
    "glossary.clear": "지우기",
    "glossary.builtin_tab": "📚 기본 용어집",
    "glossary.custom_tab": "✏️ 내 용어집",
    "glossary.builtin_info": "총 {count}개 항목 — 읽기 전용입니다.",
    "glossary.custom_info": "내 용어집이 기본 용어집보다 우선 적용됩니다.",
    "glossary.col_en": "영어 (English)",
    "glossary.col_ko": "한국어",
    "glossary.add": "+ 추가",
    "glossary.edit": "수정",
    "glossary.delete": "삭제",
    "glossary.save": "💾 저장",
    "glossary.saved": "✅ 저장 완료 ({count}개)",
    "glossary.ask_en": "영어 단어를 입력하세요:",
    "glossary.ask_ko": '"{en}"의 한국어 번역을 입력하세요:',
    "glossary.ask_edit": '"{en}"의 새 한국어 번역:',
    "glossary.confirm_delete": '"{en}" 항목을 삭제할까요?',
    "glossary.select_first": "항목을 먼저 선택하세요.",
    "common.ok": "확인",
    "common.cancel": "취소",
    "common.error": "오류",
    "common.warning": "경고",
    "common.info": "알림",
    "common.yes": "예",
    "common.no": "아니오",
}
```

- [ ] **Step 6: Create `bg3gui/i18n/en.py`**

```python
# bg3gui/i18n/en.py
STRINGS = {
    "app.title": "BG3 MOD TRANSLATOR",
    "app.subtitle": "Powered by Gemini AI · v5.0",
    "menu.settings": "Settings",
    "menu.translate": "Translate",
    "menu.review": "Review",
    "menu.glossary": "Glossary",
    "translate.file_label": "PAK File / Folder",
    "translate.browse": "Browse",
    "translate.target_lang": "Target Language",
    "translate.model": "AI Model",
    "translate.start": "▶  Start Translation",
    "translate.pause": "⏸",
    "translate.stop": "⏹",
    "translate.log_header": "TRANSLATION LOG",
    "translate.log_clear": "Clear",
    "translate.progress": "{current} / {total} files · {pct}%",
    "translate.done": "✅ Translation complete!",
    "translate.cancelled": "⏹ Cancelled",
    "translate.error": "❌ Error occurred",
    "translate.status.translating": "▶ Processing {file} — {done}/{total}",
    "translate.status.idle": "Idle",
    "translate.confirm_stop": "Stop translation?",
    "settings.title": "Settings",
    "settings.api_key": "Gemini API Key",
    "settings.show": "Show",
    "settings.hide": "Hide",
    "settings.divine_path": "Divine.exe Path",
    "settings.model_1": "AI Model (Primary)",
    "settings.model_2": "AI Model (Fallback)",
    "settings.ui_scale": "UI Scale",
    "settings.target_language": "Translation Target Language",
    "settings.app_language": "App UI Language",
    "settings.cache_path": "Translation Cache File",
    "settings.skip_existing": "Skip already-translated PAKs",
    "settings.mcm_enabled": "Auto-process MCM",
    "settings.save": "Save",
    "settings.test_api": "Test API",
    "settings.api_ok": "✅ API connection successful",
    "settings.api_fail": "❌ API error: {err}",
    "settings.saved": "✅ Saved",
    "settings.lang_restart": "App UI language changed. Restart to apply.",
    "review.pak_label": "PAK to Review",
    "review.open": "Open",
    "review.files": "Files",
    "review.source_lang": "English Source",
    "review.target_lang": "Translation",
    "review.prev": "◀ Prev",
    "review.next": "Next ▶",
    "review.save": "Save (Ctrl+S)",
    "review.modified_only": "Show Modified Only",
    "review.all": "Show All",
    "review.nav": "Item {idx} / {total}",
    "review.none": "No items",
    "review.saved_ok": "Reviewed PAK saved:\n{path}",
    "glossary.search_placeholder": "Search English or target language...",
    "glossary.clear": "Clear",
    "glossary.builtin_tab": "📚 Built-in Glossary",
    "glossary.custom_tab": "✏️ My Glossary",
    "glossary.builtin_info": "{count} entries — read-only.",
    "glossary.custom_info": "My Glossary overrides the built-in one.",
    "glossary.col_en": "English",
    "glossary.col_ko": "Translation",
    "glossary.add": "+ Add",
    "glossary.edit": "Edit",
    "glossary.delete": "Delete",
    "glossary.save": "💾 Save",
    "glossary.saved": "✅ Saved ({count} entries)",
    "glossary.ask_en": "Enter English word:",
    "glossary.ask_ko": 'Enter translation for "{en}":',
    "glossary.ask_edit": 'New translation for "{en}":',
    "glossary.confirm_delete": 'Delete entry "{en}"?',
    "glossary.select_first": "Please select an entry first.",
    "common.ok": "OK",
    "common.cancel": "Cancel",
    "common.error": "Error",
    "common.warning": "Warning",
    "common.info": "Info",
    "common.yes": "Yes",
    "common.no": "No",
}
```

- [ ] **Step 7: Create `bg3gui/i18n/__init__.py`**

```python
# bg3gui/i18n/__init__.py
from __future__ import annotations

_strings: dict = {}


def load(lang_code: str) -> None:
    global _strings
    if lang_code == "en":
        from .en import STRINGS
    else:
        from .ko import STRINGS
    _strings = STRINGS


def t(key: str, **kwargs) -> str:
    text = _strings.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text
```

- [ ] **Step 8: Add `app_language` to `bg3core/config.py`**

`ui_scale` 필드 다음 줄에 추가:
```python
    target_language: str = "Korean"
    app_language: str = "ko"      # "ko" | "en"
```

- [ ] **Step 9: Run tests — all pass**

```
python -m pytest tests/test_i18n.py tests/test_theme.py tests/ -v
```
Expected: 모든 기존 테스트(79개) + 신규 4개 = 83 passed.

- [ ] **Step 10: Commit**

```
git add bg3gui/theme.py bg3gui/i18n/ bg3core/config.py tests/test_i18n.py tests/test_theme.py
git rm bg3gui/i18n.py
git commit -m "feat(gui): theme constants, i18n ko/en system, config app_language"
```

---

### Task 2: TitleBar + Sidebar

**Files:**
- Create: `bg3gui/titlebar.py`
- Create: `bg3gui/sidebar.py`

- [ ] **Step 1: Create `bg3gui/titlebar.py`**

```python
# bg3gui/titlebar.py
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QPoint
from . import theme
from .i18n import t


class TitleBar(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(46)
        self._drag_pos: QPoint | None = None
        self.setObjectName("TitleBar")
        self.setStyleSheet(f"""
            #TitleBar {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {theme.HEADER_GRAD_START},
                    stop:0.5 {theme.HEADER_GRAD_END},
                    stop:1 {theme.HEADER_GRAD_START});
                border-bottom: 1px solid {theme.GOLD};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 10, 0)
        layout.setSpacing(10)

        icon = QLabel("⚔")
        icon.setFixedSize(26, 26)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            f"background:{theme.GOLD};color:#1a1000;border-radius:4px;"
            "font-size:14px;padding:0;"
        )
        layout.addWidget(icon)

        title_col = QWidget()
        title_col.setStyleSheet("background:transparent;")
        vcol = QVBoxLayout(title_col)
        vcol.setContentsMargins(0, 0, 0, 0)
        vcol.setSpacing(0)

        self._lbl_title = QLabel(t("app.title"))
        self._lbl_title.setStyleSheet(
            f"color:{theme.GOLD};font-weight:bold;font-size:13px;letter-spacing:1.5px;"
        )
        self._lbl_subtitle = QLabel(t("app.subtitle"))
        self._lbl_subtitle.setStyleSheet("color:#7a6a3a;font-size:10px;")

        vcol.addWidget(self._lbl_title)
        vcol.addWidget(self._lbl_subtitle)
        layout.addWidget(title_col)
        layout.addStretch()

        for text, obj_name, style in [
            ("─", "btn_tb_min",
             f"background:#2a2a2a;border:1px solid #444;color:#888;font-size:10px;"),
            ("□", "btn_tb_max",
             f"background:#2a2a2a;border:1px solid #444;color:#888;font-size:10px;"),
            ("✕", "btn_tb_close",
             f"background:{theme.CLOSE_BG};border:1px solid #8b3a3a;color:#ff9999;font-size:10px;"),
        ]:
            btn = QPushButton(text)
            btn.setObjectName(obj_name)
            btn.setFixedSize(18, 18)
            btn.setStyleSheet(
                f"QPushButton#{obj_name}{{{style}border-radius:3px;padding:0;}}"
                f"QPushButton#{obj_name}:hover{{opacity:0.8;}}"
            )
            layout.addWidget(btn)

        self.findChild(QPushButton, "btn_tb_min").clicked.connect(
            lambda: self.window().showMinimized()
        )
        self.findChild(QPushButton, "btn_tb_max").clicked.connect(self._toggle_max)
        self.findChild(QPushButton, "btn_tb_close").clicked.connect(self.window().close)

    def _toggle_max(self) -> None:
        w = self.window()
        w.showNormal() if w.isMaximized() else w.showMaximized()

    def retranslate(self) -> None:
        self._lbl_title.setText(t("app.title"))
        self._lbl_subtitle.setText(t("app.subtitle"))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event) -> None:
        self._toggle_max()
```

- [ ] **Step 2: Create `bg3gui/sidebar.py`**

```python
# bg3gui/sidebar.py
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal, Qt
from . import theme
from .i18n import t

_PAGES = [
    ("⚙", "menu.settings"),
    ("🔄", "menu.translate"),
    ("🔍", "menu.review"),
    ("📖", "menu.glossary"),
]

_STYLE_ACTIVE = f"""
    QPushButton {{
        background:#2a2000;
        border:1px solid #3a2800;
        border-left:3px solid {theme.GOLD};
        border-radius:5px;
        color:{theme.GOLD};
        font-size:10px;
        padding:9px 5px;
        font-weight:bold;
        text-align:center;
    }}
"""
_STYLE_IDLE = f"""
    QPushButton {{
        background:transparent;
        border:none;
        border-radius:5px;
        color:#666;
        font-size:10px;
        padding:9px 5px;
        text-align:center;
    }}
    QPushButton:hover {{
        background:#2a2a2a;
        color:#888;
    }}
"""


class NavigationSidebar(QWidget):
    page_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedWidth(96)
        self.setObjectName("NavigationSidebar")
        self.setStyleSheet(
            f"#NavigationSidebar{{background:{theme.BG_SIDEBAR};"
            f"border-right:1px solid #2a2a2a;}}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 10)
        layout.setSpacing(3)

        menu_lbl = QLabel("MENU")
        menu_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        menu_lbl.setStyleSheet("color:#555;font-size:9px;letter-spacing:1px;background:transparent;")
        layout.addWidget(menu_lbl)
        layout.addSpacing(6)

        self._buttons: list[QPushButton] = []
        for icon, key in _PAGES:
            btn = QPushButton(f"{icon}\n{t(key)}")
            btn.setStyleSheet(_STYLE_IDLE)
            btn.clicked.connect(lambda _checked, b=btn: self._on_click(b))
            layout.addWidget(btn)
            self._buttons.append(btn)

        layout.addStretch()

        ver = QLabel("v5.0")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet("color:#3a3a3a;font-size:9px;background:transparent;")
        layout.addWidget(ver)

        self._set_active(1)  # 번역 탭이 기본

    def _on_click(self, btn: QPushButton) -> None:
        idx = self._buttons.index(btn)
        self._set_active(idx)
        self.page_changed.emit(idx)

    def _set_active(self, idx: int) -> None:
        for i, btn in enumerate(self._buttons):
            btn.setStyleSheet(_STYLE_ACTIVE if i == idx else _STYLE_IDLE)

    def set_page(self, idx: int) -> None:
        self._set_active(idx)

    def retranslate(self) -> None:
        for btn, (icon, key) in zip(self._buttons, _PAGES):
            btn.setText(f"{icon}\n{t(key)}")
```

- [ ] **Step 3: Verify PySide6 import works**

```
python -c "from bg3gui.titlebar import TitleBar; from bg3gui.sidebar import NavigationSidebar; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Run all tests**

```
python -m pytest tests/ -v
```
Expected: 83 passed.

- [ ] **Step 5: Commit**

```
git add bg3gui/titlebar.py bg3gui/sidebar.py
git commit -m "feat(gui): custom TitleBar + NavigationSidebar (PySide6)"
```

---

### Task 3: PathPicker widget + QThread Worker

**Files:**
- Rewrite: `bg3gui/widgets/path_picker.py`
- Rewrite: `bg3gui/widgets/log_view.py`
- Rewrite: `bg3gui/widgets/progress_panel.py`
- Rewrite: `bg3gui/workers.py`

- [ ] **Step 1: Rewrite `bg3gui/widgets/path_picker.py`**

```python
# bg3gui/widgets/path_picker.py
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog
from PySide6.QtCore import Signal
from .. import theme
from ..i18n import t


class PathPicker(QWidget):
    path_changed = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        mode: str = "file",          # "file" | "dir"
        label_key: str = "common.browse",
        filetypes: list[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._filetypes = filetypes or [("All files", "*.*")]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText("")
        layout.addWidget(self._edit)

        self._btn = QPushButton(t(label_key))
        self._btn.setFixedWidth(60)
        self._btn.clicked.connect(self._browse)
        layout.addWidget(self._btn)

    def _browse(self) -> None:
        if self._mode == "dir":
            path = QFileDialog.getExistingDirectory(self, t("common.browse"), self._edit.text())
        else:
            filter_str = ";;".join(f"{name} ({ext})" for name, ext in self._filetypes)
            path, _ = QFileDialog.getOpenFileName(
                self, t("common.browse"), self._edit.text(), filter_str
            )
        if path:
            self._edit.setText(path)
            self.path_changed.emit(path)

    def get(self) -> str:
        return self._edit.text().strip()

    def set(self, path: str) -> None:
        self._edit.setText(path)
```

- [ ] **Step 2: Rewrite `bg3gui/widgets/log_view.py`**

```python
# bg3gui/widgets/log_view.py
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtCore import Qt
from .. import theme
from ..i18n import t


class LogView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QHBoxLayout()
        lbl = QLabel(t("translate.log_header"))
        lbl.setStyleSheet(f"color:{theme.TEXT_MUTED};font-size:9px;letter-spacing:1px;background:transparent;")
        header.addWidget(lbl)
        header.addStretch()
        self._btn_clear = QPushButton(t("translate.log_clear"))
        self._btn_clear.setStyleSheet(
            f"QPushButton{{color:{theme.TEXT_MUTED};background:transparent;border:none;font-size:9px;padding:0;}}"
            f"QPushButton:hover{{color:{theme.TEXT_SECONDARY};}}"
        )
        self._btn_clear.clicked.connect(self.clear)
        header.addWidget(self._btn_clear)
        layout.addLayout(header)

        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        layout.addWidget(self._text)

    def append(self, message: str) -> None:
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        if message.startswith("✅"):
            fmt.setForeground(QColor(theme.SUCCESS))
        elif message.startswith("▶"):
            fmt.setForeground(QColor(theme.GOLD))
        elif message.startswith("❌") or message.startswith("⚠"):
            fmt.setForeground(QColor("#cc4444"))
        elif message.startswith("⏳"):
            fmt.setForeground(QColor(theme.TEXT_MUTED))
        else:
            fmt.setForeground(QColor(theme.TEXT_PRIMARY))
        cursor.insertText(message + "\n", fmt)
        self._text.setTextCursor(cursor)
        self._text.ensureCursorVisible()

    def clear(self) -> None:
        self._text.clear()

    def retranslate(self) -> None:
        self._btn_clear.setText(t("translate.log_clear"))
```

- [ ] **Step 3: Rewrite `bg3gui/widgets/progress_panel.py`**

```python
# bg3gui/widgets/progress_panel.py
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QHBoxLayout, QProgressBar, QLabel
from PySide6.QtCore import Qt
from .. import theme
from ..i18n import t


class ProgressPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(8)
        layout.addWidget(self._bar)

        self._lbl = QLabel(t("translate.progress", current=0, total=0, pct=0))
        self._lbl.setStyleSheet(f"color:{theme.GOLD};font-size:11px;background:transparent;white-space:nowrap;")
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._lbl.setFixedWidth(130)
        layout.addWidget(self._lbl)

    def update(self, current: int, total: int) -> None:
        pct = int(current / total * 100) if total > 0 else 0
        self._bar.setValue(pct)
        self._lbl.setText(t("translate.progress", current=current, total=total, pct=pct))

    def reset(self) -> None:
        self._bar.setValue(0)
        self._lbl.setText(t("translate.progress", current=0, total=0, pct=0))
```

- [ ] **Step 4: Rewrite `bg3gui/workers.py`**

```python
# bg3gui/workers.py
from __future__ import annotations
import os
import traceback
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from bg3core.config import UserConfig, get_default_cache_path, get_default_log_dir
from bg3core.pipeline import run_batch
from bg3core.logger import CallbackLogger


class TranslationWorker(QThread):
    log_line = Signal(str)       # 로그 한 줄
    progress = Signal(int, int, str)  # current, total, filename
    finished = Signal()
    error = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        cfg: UserConfig,
        target_path: str,
        cancel_event: threading.Event,
        pause_event: threading.Event,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.target_path = target_path
        self.cancel_event = cancel_event
        self.pause_event = pause_event

    def run(self) -> None:
        cfg = self.cfg
        cache_file = cfg.cache_path or get_default_cache_path()
        log_dir = cfg.log_dir or get_default_log_dir()
        os.makedirs(log_dir, exist_ok=True)
        log_file = str(Path(log_dir) / "translation_errors.txt")
        work_dir = Path(cache_file).parent

        logger = CallbackLogger(
            on_log=lambda e: self.log_line.emit(
                e.message if hasattr(e, "message") else str(e)
            ),
            on_progress=lambda e: None,
        )

        def on_progress(stage: str, current: int, total: int, message: str, pak_name=None):
            self.progress.emit(current, total, message)

        try:
            run_batch(
                api_key=cfg.api_key,
                divine_path=cfg.divine_exe_path,
                target_pak=self.target_path,
                log_file=log_file,
                cache_file=cache_file,
                work_dir=work_dir,
                skip_if_target_exists=cfg.skip_if_korean_exists,
                target_language=cfg.target_language,
                mcm_enabled=cfg.mcm_enabled,
                cancel_event=self.cancel_event,
                pause_event=self.pause_event,
                on_progress=on_progress,
                logger=logger,
            )
            self.finished.emit()
        except InterruptedError:
            self.cancelled.emit()
        except Exception:
            self.error.emit(traceback.format_exc())
```

- [ ] **Step 5: Verify imports**

```
python -c "
from bg3gui.widgets.path_picker import PathPicker
from bg3gui.widgets.log_view import LogView
from bg3gui.widgets.progress_panel import ProgressPanel
from bg3gui.workers import TranslationWorker
print('OK')
"
```

- [ ] **Step 6: Run all tests**

```
python -m pytest tests/ -v
```

- [ ] **Step 7: Commit**

```
git add bg3gui/workers.py bg3gui/widgets/
git commit -m "feat(gui): PySide6 PathPicker, LogView, ProgressPanel, QThread worker"
```

---

### Task 4: Settings Tab

**Files:**
- Rewrite: `bg3gui/settings_tab.py`

- [ ] **Step 1: Rewrite `bg3gui/settings_tab.py`**

```python
# bg3gui/settings_tab.py
from __future__ import annotations
import threading
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QCheckBox, QScrollArea, QFrame,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer

from bg3core.config import UserConfig, save_config, auto_detect_divine
from bg3core.language import LANGUAGE_PROFILES
from . import theme
from .i18n import t
from .widgets.path_picker import PathPicker

_LANG_OPTIONS = sorted(
    [p for p in LANGUAGE_PROFILES.values() if p.folder_name != "English"],
    key=lambda p: (0 if p.folder_name == "Korean" else 1, p.display_name),
)
_DISPLAY_TO_FOLDER = {p.display_name: p.folder_name for p in _LANG_OPTIONS}
_FOLDER_TO_DISPLAY = {p.folder_name: p.display_name for p in _LANG_OPTIONS}

_APP_LANG_OPTIONS = [("한국어", "ko"), ("English", "en")]
_APP_LANG_DISPLAY = {code: label for label, code in _APP_LANG_OPTIONS}
_APP_LANG_CODE = {label: code for label, code in _APP_LANG_OPTIONS}


def _row_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{theme.TEXT_SECONDARY};font-size:11px;background:transparent;")
    return lbl


class SettingsTab(QWidget):
    def __init__(self, on_config_saved: Callable[[UserConfig], None], parent=None) -> None:
        super().__init__(parent)
        self._on_config_saved = on_config_saved
        self._cfg: UserConfig | None = None

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        container = QWidget()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)

        # ── API Key ──
        layout.addWidget(_row_label(t("settings.api_key")))
        api_row = QHBoxLayout()
        self._api_edit = QLineEdit()
        self._api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        api_row.addWidget(self._api_edit)
        self._btn_show = QPushButton(t("settings.show"))
        self._btn_show.setFixedWidth(56)
        self._btn_show.setCheckable(True)
        self._btn_show.toggled.connect(self._toggle_api_visibility)
        api_row.addWidget(self._btn_show)
        layout.addLayout(api_row)

        # ── Divine.exe ──
        layout.addWidget(_row_label(t("settings.divine_path")))
        self._divine_picker = PathPicker(
            mode="file",
            filetypes=[("Divine.exe", "Divine.exe"), ("Executable", "*.exe")],
        )
        layout.addWidget(self._divine_picker)

        # ── Models ──
        layout.addWidget(_row_label(t("settings.model_1")))
        self._model1_combo = QComboBox()
        layout.addWidget(self._model1_combo)

        layout.addWidget(_row_label(t("settings.model_2")))
        self._model2_combo = QComboBox()
        layout.addWidget(self._model2_combo)

        # ── UI Scale ──
        layout.addWidget(_row_label(t("settings.ui_scale")))
        self._scale_combo = QComboBox()
        self._scale_combo.addItems(["auto", "1.0", "1.25", "1.5", "1.75", "2.0"])
        layout.addWidget(self._scale_combo)

        # ── Target Language ──
        layout.addWidget(_row_label(t("settings.target_language")))
        self._lang_combo = QComboBox()
        self._lang_combo.addItems([p.display_name for p in _LANG_OPTIONS])
        layout.addWidget(self._lang_combo)

        # ── App UI Language ──
        layout.addWidget(_row_label(t("settings.app_language")))
        self._app_lang_combo = QComboBox()
        self._app_lang_combo.addItems([label for label, _ in _APP_LANG_OPTIONS])
        layout.addWidget(self._app_lang_combo)

        # ── Cache ──
        layout.addWidget(_row_label(t("settings.cache_path")))
        self._cache_picker = PathPicker(mode="file", filetypes=[("JSON", "*.json")])
        layout.addWidget(self._cache_picker)

        # ── Checkboxes ──
        self._skip_check = QCheckBox(t("settings.skip_existing"))
        layout.addWidget(self._skip_check)
        self._mcm_check = QCheckBox(t("settings.mcm_enabled"))
        layout.addWidget(self._mcm_check)

        # ── Divider ──
        div = QFrame()
        div.setObjectName("divider")
        div.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(div)

        # ── Buttons ──
        btn_row = QHBoxLayout()
        self._btn_save = QPushButton(t("settings.save"))
        self._btn_save.setObjectName("btn_start")
        self._btn_save.setFixedHeight(36)
        self._btn_save.clicked.connect(self._save)
        btn_row.addWidget(self._btn_save)

        self._btn_test = QPushButton(t("settings.test_api"))
        self._btn_test.setFixedHeight(36)
        self._btn_test.clicked.connect(self._test_api)
        btn_row.addWidget(self._btn_test)
        layout.addLayout(btn_row)

        self._lbl_status = QLabel("")
        self._lbl_status.setStyleSheet(f"color:{theme.GOLD};background:transparent;")
        layout.addWidget(self._lbl_status)

        layout.addStretch()

    def _toggle_api_visibility(self, checked: bool) -> None:
        if checked:
            self._api_edit.setEchoMode(QLineEdit.EchoMode.Normal)
            self._btn_show.setText(t("settings.hide"))
        else:
            self._api_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self._btn_show.setText(t("settings.show"))

    def load_config(self, cfg: UserConfig) -> None:
        self._cfg = cfg
        self._api_edit.setText(cfg.api_key)
        self._divine_picker.set(cfg.divine_exe_path)
        from bg3core.constants import MODELS_TO_TRY
        models = list(MODELS_TO_TRY) + ["gemini-2.5-flash", "gemini-2.5-pro"]
        for combo in (self._model1_combo, self._model2_combo):
            combo.clear()
            combo.addItems(models)
        if cfg.model_preference:
            self._model1_combo.setCurrentText(cfg.model_preference[0] if len(cfg.model_preference) > 0 else models[0])
            self._model2_combo.setCurrentText(cfg.model_preference[1] if len(cfg.model_preference) > 1 else models[1] if len(models) > 1 else models[0])
        self._scale_combo.setCurrentText(cfg.ui_scale)
        self._lang_combo.setCurrentText(
            _FOLDER_TO_DISPLAY.get(cfg.target_language, _LANG_OPTIONS[0].display_name)
        )
        app_lang_label = _APP_LANG_DISPLAY.get(cfg.app_language, "한국어")
        self._app_lang_combo.setCurrentText(app_lang_label)
        self._cache_picker.set(cfg.cache_path)
        self._skip_check.setChecked(cfg.skip_if_korean_exists)
        self._mcm_check.setChecked(cfg.mcm_enabled)

    def _build_config(self) -> UserConfig:
        cfg = UserConfig()
        cfg.api_key = self._api_edit.text().strip()
        cfg.divine_exe_path = self._divine_picker.get()
        cfg.model_preference = [
            self._model1_combo.currentText(),
            self._model2_combo.currentText(),
        ]
        cfg.ui_scale = self._scale_combo.currentText()
        cfg.target_language = _DISPLAY_TO_FOLDER.get(
            self._lang_combo.currentText(), "Korean"
        )
        cfg.app_language = _APP_LANG_CODE.get(
            self._app_lang_combo.currentText(), "ko"
        )
        cfg.cache_path = self._cache_picker.get()
        cfg.skip_if_korean_exists = self._skip_check.isChecked()
        cfg.mcm_enabled = self._mcm_check.isChecked()
        if self._cfg:
            cfg.last_pak_dir = self._cfg.last_pak_dir
            cfg.last_output_dir = self._cfg.last_output_dir
            cfg.log_dir = self._cfg.log_dir
        return cfg

    def _save(self) -> None:
        cfg = self._build_config()
        prev_lang = self._cfg.app_language if self._cfg else "ko"
        save_config(cfg)
        self._cfg = cfg
        self._on_config_saved(cfg)
        self._show_status(t("settings.saved"))
        if cfg.app_language != prev_lang:
            QMessageBox.information(self, t("common.info"), t("settings.lang_restart"))

    def _show_status(self, msg: str, ms: int = 3000) -> None:
        self._lbl_status.setText(msg)
        QTimer.singleShot(ms, lambda: self._lbl_status.setText(""))

    def _test_api(self) -> None:
        key = self._api_edit.text().strip()
        if not key:
            self._show_status("❌ API Key가 없습니다.")
            return

        def _check():
            try:
                import urllib.request, json
                url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
                with urllib.request.urlopen(url, timeout=10) as r:
                    json.loads(r.read())
                self._show_status(t("settings.api_ok"))
            except Exception as e:
                self._show_status(t("settings.api_fail", err=str(e)[:60]))

        threading.Thread(target=_check, daemon=True).start()
```

- [ ] **Step 2: Verify import**

```
python -c "from bg3gui.settings_tab import SettingsTab; print('OK')"
```

- [ ] **Step 3: Run all tests**

```
python -m pytest tests/ -v
```

- [ ] **Step 4: Commit**

```
git add bg3gui/settings_tab.py
git commit -m "feat(gui): settings tab (PySide6) with target language + app UI language"
```

---

### Task 5: Translate Tab

**Files:**
- Rewrite: `bg3gui/translate_tab.py`

- [ ] **Step 1: Rewrite `bg3gui/translate_tab.py`**

```python
# bg3gui/translate_tab.py
from __future__ import annotations
import threading

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt

from bg3core.config import UserConfig
from bg3core.language import LANGUAGE_PROFILES
from . import theme
from .i18n import t
from .workers import TranslationWorker
from .widgets.path_picker import PathPicker
from .widgets.log_view import LogView
from .widgets.progress_panel import ProgressPanel

_LANG_OPTIONS = sorted(
    [p for p in LANGUAGE_PROFILES.values() if p.folder_name != "English"],
    key=lambda p: (0 if p.folder_name == "Korean" else 1, p.display_name),
)
_FOLDER_TO_DISPLAY = {p.folder_name: p.display_name for p in _LANG_OPTIONS}
_DISPLAY_TO_FOLDER = {p.display_name: p.folder_name for p in _LANG_OPTIONS}


class TranslateTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cfg: UserConfig | None = None
        self._worker: TranslationWorker | None = None
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._running = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # File picker
        self._picker = PathPicker(
            mode="file",
            filetypes=[("PAK files", "*.pak"), ("All files", "*.*")],
            label_key="translate.browse",
        )
        # Also allow folder selection via a separate button
        file_row = QHBoxLayout()
        file_row.addWidget(self._picker)
        self._btn_folder = QPushButton("📁")
        self._btn_folder.setToolTip("폴더 선택")
        self._btn_folder.setFixedWidth(36)
        self._btn_folder.clicked.connect(self._pick_folder)
        file_row.addWidget(self._btn_folder)
        layout.addLayout(file_row)

        # Language + model row
        lang_row = QHBoxLayout()
        lang_row.setSpacing(8)
        from PySide6.QtWidgets import QComboBox
        self._lang_combo = QComboBox()
        self._lang_combo.addItems([p.display_name for p in _LANG_OPTIONS])
        lang_row.addWidget(self._lang_combo)
        self._model_combo = QComboBox()
        from bg3core.constants import MODELS_TO_TRY
        self._model_combo.addItems(list(MODELS_TO_TRY))
        lang_row.addWidget(self._model_combo)
        layout.addLayout(lang_row)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._btn_start = QPushButton(t("translate.start"))
        self._btn_start.setObjectName("btn_start")
        self._btn_start.setFixedHeight(38)
        self._btn_start.clicked.connect(self._on_start)
        btn_row.addWidget(self._btn_start)
        self._btn_pause = QPushButton(t("translate.pause"))
        self._btn_pause.setFixedSize(44, 38)
        self._btn_pause.setCheckable(True)
        self._btn_pause.setEnabled(False)
        self._btn_pause.clicked.connect(self._on_pause)
        btn_row.addWidget(self._btn_pause)
        self._btn_stop = QPushButton(t("translate.stop"))
        self._btn_stop.setFixedSize(44, 38)
        self._btn_stop.setEnabled(False)
        self._btn_stop.clicked.connect(self._on_stop)
        btn_row.addWidget(self._btn_stop)
        layout.addLayout(btn_row)

        # Progress
        self._progress = ProgressPanel()
        layout.addWidget(self._progress)

        # Log (dominant)
        self._log = LogView()
        layout.addWidget(self._log, stretch=1)

    def _pick_folder(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(self, t("translate.file_label"))
        if path:
            self._picker.set(path)

    def set_config(self, cfg: UserConfig) -> None:
        self._cfg = cfg
        self._lang_combo.setCurrentText(
            _FOLDER_TO_DISPLAY.get(cfg.target_language, _LANG_OPTIONS[0].display_name)
        )
        from bg3core.constants import MODELS_TO_TRY
        if cfg.model_preference:
            self._model_combo.setCurrentText(cfg.model_preference[0])

    def _on_start(self) -> None:
        if not self._cfg:
            QMessageBox.warning(self, t("common.warning"), "설정을 먼저 저장하세요.")
            return
        path = self._picker.get()
        if not path:
            QMessageBox.warning(self, t("common.warning"), "PAK 파일 또는 폴더를 선택하세요.")
            return
        if not self._cfg.api_key:
            QMessageBox.warning(self, t("common.warning"), "Gemini API Key를 설정하세요.")
            return

        # sync language to config before running
        self._cfg.target_language = _DISPLAY_TO_FOLDER.get(
            self._lang_combo.currentText(), "Korean"
        )

        self._cancel_event.clear()
        self._pause_event.clear()
        self._running = True
        self._progress.reset()
        self._log.clear()
        self._set_buttons_running(True)

        self._worker = TranslationWorker(
            self._cfg, path, self._cancel_event, self._pause_event, parent=self
        )
        self._worker.log_line.connect(self._log.append)
        self._worker.progress.connect(lambda c, total, _: self._progress.update(c, total))
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.cancelled.connect(self._on_cancelled)
        self._worker.start()

    def _on_pause(self, checked: bool) -> None:
        if checked:
            self._pause_event.set()
        else:
            self._pause_event.clear()

    def _on_stop(self) -> None:
        if QMessageBox.question(
            self, t("common.warning"), t("translate.confirm_stop"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            self._cancel_event.set()
            self._pause_event.clear()

    def _on_done(self) -> None:
        self._running = False
        self._set_buttons_running(False)
        self._log.append(t("translate.done"))

    def _on_error(self, tb: str) -> None:
        self._running = False
        self._set_buttons_running(False)
        self._log.append(t("translate.error"))
        self._log.append(tb)

    def _on_cancelled(self) -> None:
        self._running = False
        self._set_buttons_running(False)
        self._log.append(t("translate.cancelled"))

    def _set_buttons_running(self, running: bool) -> None:
        self._btn_start.setEnabled(not running)
        self._btn_pause.setEnabled(running)
        self._btn_stop.setEnabled(running)
        if not running:
            self._btn_pause.setChecked(False)
```

- [ ] **Step 2: Verify import**

```
python -c "from bg3gui.translate_tab import TranslateTab; print('OK')"
```

- [ ] **Step 3: Run all tests**

```
python -m pytest tests/ -v
```

- [ ] **Step 4: Commit**

```
git add bg3gui/translate_tab.py
git commit -m "feat(gui): translate tab (PySide6) with log-centric layout"
```

---

### Task 6: Reviewer Tab

**Files:**
- Rewrite: `bg3gui/reviewer_tab.py`

- [ ] **Step 1: Rewrite `bg3gui/reviewer_tab.py`**

```python
# bg3gui/reviewer_tab.py
from __future__ import annotations
import shutil
import tempfile
import threading
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QTextEdit, QMessageBox, QSplitter,
)
from PySide6.QtCore import Qt, Signal, QThread

from bg3core.config import UserConfig
from bg3core.divine import divine_extract, divine_repack, ensure_loca
from bg3core.reviewer import Entry, ReviewFile, load_review_files, save_modified_xml
from . import theme
from .i18n import t
from .widgets.path_picker import PathPicker


class _UnpackWorker(QThread):
    done = Signal(bool)

    def __init__(self, divine_path: str, pak_path: Path, dest: Path, parent=None):
        super().__init__(parent)
        self._divine = divine_path
        self._pak = pak_path
        self._dest = dest

    def run(self):
        ok = divine_extract(self._divine, self._pak, self._dest)
        self.done.emit(ok)


class ReviewerTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cfg: Optional[UserConfig] = None
        self._review_files: List[ReviewFile] = []
        self._current_file: Optional[ReviewFile] = None
        self._current_entries: List[Entry] = []
        self._current_idx: int = 0
        self._show_modified_only = False
        self._temp_dir: Optional[Path] = None
        self._pak_path: Optional[Path] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Top: PAK picker
        top_row = QHBoxLayout()
        self._picker = PathPicker(
            mode="file",
            filetypes=[("PAK files", "*.pak")],
            label_key="review.open",
        )
        top_row.addWidget(self._picker)
        self._btn_open = QPushButton(t("review.open"))
        self._btn_open.setFixedWidth(70)
        self._btn_open.clicked.connect(self._open_pak)
        top_row.addWidget(self._btn_open)
        layout.addLayout(top_row)

        # Splitter: file list (left) + editor (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # File list
        file_panel = QWidget()
        fp_layout = QVBoxLayout(file_panel)
        fp_layout.setContentsMargins(0, 0, 0, 0)
        fp_layout.setSpacing(4)
        fp_layout.addWidget(QLabel(t("review.files")))
        self._file_list = QListWidget()
        self._file_list.currentRowChanged.connect(self._on_file_select)
        fp_layout.addWidget(self._file_list)
        splitter.addWidget(file_panel)
        splitter.setStretchFactor(0, 0)

        # Editor
        edit_panel = QWidget()
        ep_layout = QVBoxLayout(edit_panel)
        ep_layout.setContentsMargins(0, 0, 0, 0)
        ep_layout.setSpacing(6)

        self._nav_label = QLabel(t("review.none"))
        self._nav_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._nav_label.setStyleSheet(f"color:{theme.TEXT_MUTED};background:transparent;")
        ep_layout.addWidget(self._nav_label)

        ep_layout.addWidget(QLabel(t("review.source_lang")))
        self._en_box = QTextEdit()
        self._en_box.setReadOnly(True)
        self._en_box.setFixedHeight(100)
        ep_layout.addWidget(self._en_box)

        ep_layout.addWidget(QLabel(t("review.target_lang")))
        self._kr_box = QTextEdit()
        self._kr_box.setFixedHeight(100)
        ep_layout.addWidget(self._kr_box)

        # Navigation buttons
        nav_row = QHBoxLayout()
        self._btn_prev = QPushButton(t("review.prev"))
        self._btn_prev.setFixedWidth(80)
        self._btn_prev.clicked.connect(self._prev)
        nav_row.addWidget(self._btn_prev)
        self._btn_next = QPushButton(t("review.next"))
        self._btn_next.setFixedWidth(80)
        self._btn_next.clicked.connect(self._next)
        nav_row.addWidget(self._btn_next)
        self._btn_save = QPushButton(t("review.save"))
        self._btn_save.clicked.connect(self._save_all)
        nav_row.addWidget(self._btn_save)
        self._btn_modified = QPushButton(t("review.modified_only"))
        self._btn_modified.setCheckable(True)
        self._btn_modified.toggled.connect(self._toggle_modified)
        nav_row.addWidget(self._btn_modified)
        nav_row.addStretch()
        ep_layout.addLayout(nav_row)
        ep_layout.addStretch()

        splitter.addWidget(edit_panel)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([180, 600])
        layout.addWidget(splitter, stretch=1)

        # Ctrl+S shortcut
        from PySide6.QtGui import QKeySequence, QShortcut
        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._save_all)

    def set_config(self, cfg: UserConfig) -> None:
        self._cfg = cfg

    def _open_pak(self) -> None:
        path_str = self._picker.get()
        if not path_str:
            return
        if not self._cfg or not self._cfg.divine_exe_path:
            QMessageBox.warning(self, t("common.warning"), "설정에서 Divine.exe 경로를 먼저 저장하세요.")
            return
        self._pak_path = Path(path_str)
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        self._temp_dir = Path(tempfile.mkdtemp(prefix="bg3_review_"))
        self._btn_open.setEnabled(False)
        self._worker = _UnpackWorker(
            self._cfg.divine_exe_path, self._pak_path, self._temp_dir, parent=self
        )
        self._worker.done.connect(self._on_unpack_done)
        self._worker.start()

    def _on_unpack_done(self, ok: bool) -> None:
        self._btn_open.setEnabled(True)
        if not ok:
            QMessageBox.critical(self, t("common.error"), "PAK 언팩에 실패했습니다.")
            return
        target_folder = self._cfg.target_language if self._cfg else "Korean"
        review_files = load_review_files(self._temp_dir, target_folder=target_folder)
        if not review_files:
            QMessageBox.warning(self, t("common.warning"),
                "번역 항목을 찾지 못했습니다.\n(대상 언어 폴더가 있는지 확인하세요)")
            return
        self._review_files = review_files
        self._file_list.clear()
        for rf in review_files:
            self._file_list.addItem(rf.filename)
        if review_files:
            self._file_list.setCurrentRow(0)

    def _on_file_select(self, row: int) -> None:
        if 0 <= row < len(self._review_files):
            self._load_file(self._review_files[row])

    def _load_file(self, rf: ReviewFile) -> None:
        self._current_file = rf
        self._current_entries = [
            e for e in rf.entries
            if not self._show_modified_only or e.modified
        ]
        self._current_idx = 0
        self._show_entry()

    def _show_entry(self) -> None:
        if not self._current_entries:
            self._nav_label.setText(t("review.none"))
            self._en_box.clear()
            self._kr_box.clear()
            return
        entry = self._current_entries[self._current_idx]
        total = len(self._current_entries)
        self._nav_label.setText(t("review.nav", idx=self._current_idx + 1, total=total))
        self._en_box.setPlainText(entry.english)
        self._kr_box.setPlainText(entry.display_target)

    def _commit_current(self) -> None:
        if not self._current_entries:
            return
        entry = self._current_entries[self._current_idx]
        new_text = self._kr_box.toPlainText()
        if new_text != entry.target_text:
            entry.modified = True
            entry.new_target = new_text

    def _next(self) -> None:
        self._commit_current()
        if self._current_entries and self._current_idx < len(self._current_entries) - 1:
            self._current_idx += 1
        self._show_entry()

    def _prev(self) -> None:
        self._commit_current()
        if self._current_idx > 0:
            self._current_idx -= 1
        self._show_entry()

    def _save_all(self) -> None:
        self._commit_current()
        if not self._review_files or not self._pak_path or not self._temp_dir:
            return
        modified = [rf for rf in self._review_files if any(e.modified for e in rf.entries)]
        if not modified:
            QMessageBox.information(self, t("common.info"), "수정된 항목이 없습니다.")
            return
        for rf in modified:
            save_modified_xml(rf)
        ensure_loca(self._cfg.divine_exe_path, self._temp_dir, force=True)
        out_pak = self._pak_path.parent / f"{self._pak_path.stem}_Reviewed.pak"
        if divine_repack(self._cfg.divine_exe_path, self._temp_dir, out_pak):
            QMessageBox.information(self, t("common.info"), t("review.saved_ok", path=out_pak.name))
        else:
            QMessageBox.critical(self, t("common.error"), "PAK 리팩에 실패했습니다.")

    def _toggle_modified(self, checked: bool) -> None:
        self._show_modified_only = checked
        self._btn_modified.setText(t("review.all") if checked else t("review.modified_only"))
        if self._current_file:
            self._load_file(self._current_file)
```

- [ ] **Step 2: Verify import**

```
python -c "from bg3gui.reviewer_tab import ReviewerTab; print('OK')"
```

- [ ] **Step 3: Run all tests**

```
python -m pytest tests/ -v
```

- [ ] **Step 4: Commit**

```
git add bg3gui/reviewer_tab.py
git commit -m "feat(gui): reviewer tab (PySide6)"
```

---

### Task 7: Glossary Tab

**Files:**
- Rewrite: `bg3gui/glossary_tab.py`

- [ ] **Step 1: Rewrite `bg3gui/glossary_tab.py`**

```python
# bg3gui/glossary_tab.py
from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt

from bg3core.glossary import GLOSSARY, load_custom_glossary, save_custom_glossary
from . import theme
from .i18n import t


class GlossaryTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._custom_data: dict = dict(load_custom_glossary())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Search row
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(t("glossary.search_placeholder"))
        self._search.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search)
        btn_clear = QPushButton(t("glossary.clear"))
        btn_clear.setFixedWidth(56)
        btn_clear.clicked.connect(lambda: self._search.clear())
        search_row.addWidget(btn_clear)
        layout.addLayout(search_row)

        # Inner tabs
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{border:1px solid {theme.DIVIDER};border-radius:4px;}}
            QTabBar::tab {{
                background:{theme.BG_CARD};color:{theme.TEXT_SECONDARY};
                padding:6px 14px;border-radius:4px 4px 0 0;margin-right:2px;
            }}
            QTabBar::tab:selected {{
                background:#2a2000;color:{theme.GOLD};
                border-bottom:2px solid {theme.GOLD};
            }}
        """)

        # Built-in tab
        builtin_w = QWidget()
        bl = QVBoxLayout(builtin_w)
        bl.setContentsMargins(8, 8, 8, 8)
        lbl_info = QLabel(t("glossary.builtin_info", count=len(GLOSSARY)))
        lbl_info.setObjectName("label_muted")
        bl.addWidget(lbl_info)
        self._base_tree = self._make_tree()
        bl.addWidget(self._base_tree)
        self._tabs.addTab(builtin_w, t("glossary.builtin_tab"))

        # Custom tab
        custom_w = QWidget()
        cl = QVBoxLayout(custom_w)
        cl.setContentsMargins(8, 8, 8, 8)
        lbl_custom = QLabel(t("glossary.custom_info"))
        lbl_custom.setObjectName("label_muted")
        cl.addWidget(lbl_custom)
        self._custom_tree = self._make_tree()
        self._custom_tree.itemDoubleClicked.connect(lambda *_: self._edit_entry())
        cl.addWidget(self._custom_tree)

        btn_row = QHBoxLayout()
        self._btn_add = QPushButton(t("glossary.add"))
        self._btn_add.clicked.connect(self._add_entry)
        btn_row.addWidget(self._btn_add)
        self._btn_edit = QPushButton(t("glossary.edit"))
        self._btn_edit.clicked.connect(self._edit_entry)
        btn_row.addWidget(self._btn_edit)
        self._btn_del = QPushButton(t("glossary.delete"))
        self._btn_del.setStyleSheet("QPushButton{background:#5a1a1a;border-color:#8b3a3a;color:#ff9999;}")
        self._btn_del.clicked.connect(self._delete_entry)
        btn_row.addWidget(self._btn_del)
        self._btn_save = QPushButton(t("glossary.save"))
        self._btn_save.setObjectName("btn_start")
        self._btn_save.clicked.connect(self._save)
        btn_row.addWidget(self._btn_save)
        self._lbl_saved = QLabel("")
        self._lbl_saved.setStyleSheet(f"color:{theme.GOLD};background:transparent;")
        btn_row.addWidget(self._lbl_saved)
        btn_row.addStretch()
        cl.addLayout(btn_row)
        self._tabs.addTab(custom_w, t("glossary.custom_tab"))

        layout.addWidget(self._tabs, stretch=1)

        self._base_all: list[tuple[str, str]] = list(GLOSSARY.items())
        self._custom_all: list[tuple[str, str]] = list(self._custom_data.items())
        self._populate(self._base_tree, self._base_all)
        self._populate(self._custom_tree, self._custom_all)

    def _make_tree(self) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setHeaderLabels([t("glossary.col_en"), t("glossary.col_ko")])
        tree.setAlternatingRowColors(True)
        tree.header().setStretchLastSection(True)
        tree.setColumnWidth(0, 300)
        return tree

    def _populate(self, tree: QTreeWidget, rows: list[tuple[str, str]]) -> None:
        tree.clear()
        for en, ko in rows:
            item = QTreeWidgetItem([en, ko])
            tree.addTopLevelItem(item)

    def _apply_filter(self, text: str) -> None:
        q = text.strip().lower()
        def filt(rows):
            return [(e, k) for e, k in rows if not q or q in e.lower() or q in k.lower()]
        self._populate(self._base_tree, filt(self._base_all))
        self._populate(self._custom_tree, filt(self._custom_all))

    def _selected_custom(self) -> tuple[str, str] | None:
        items = self._custom_tree.selectedItems()
        if not items:
            return None
        return items[0].text(0), items[0].text(1)

    def _add_entry(self) -> None:
        en, ok = QInputDialog.getText(self, t("glossary.add"), t("glossary.ask_en"))
        if not ok or not en.strip():
            return
        en = en.strip()
        ko, ok2 = QInputDialog.getText(self, t("glossary.add"), t("glossary.ask_ko", en=en))
        if not ok2 or not ko.strip():
            return
        self._custom_data[en] = ko.strip()
        self._refresh_custom()

    def _edit_entry(self) -> None:
        sel = self._selected_custom()
        if not sel:
            QMessageBox.warning(self, t("common.warning"), t("glossary.select_first"))
            return
        en, ko = sel
        new_ko, ok = QInputDialog.getText(
            self, t("glossary.edit"), t("glossary.ask_edit", en=en), text=ko
        )
        if ok and new_ko.strip():
            self._custom_data[en] = new_ko.strip()
            self._refresh_custom()

    def _delete_entry(self) -> None:
        sel = self._selected_custom()
        if not sel:
            QMessageBox.warning(self, t("common.warning"), t("glossary.select_first"))
            return
        en, _ = sel
        if QMessageBox.question(
            self, t("glossary.delete"), t("glossary.confirm_delete", en=en),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            self._custom_data.pop(en, None)
            self._refresh_custom()

    def _refresh_custom(self) -> None:
        self._custom_all = list(self._custom_data.items())
        self._apply_filter(self._search.text())

    def _save(self) -> None:
        save_custom_glossary(self._custom_data)
        self._lbl_saved.setText(t("glossary.saved", count=len(self._custom_data)))
        from PySide6.QtCore import QTimer
        QTimer.singleShot(3000, lambda: self._lbl_saved.setText(""))
```

- [ ] **Step 2: Verify import**

```
python -c "from bg3gui.glossary_tab import GlossaryTab; print('OK')"
```

- [ ] **Step 3: Run all tests**

```
python -m pytest tests/ -v
```

- [ ] **Step 4: Commit**

```
git add bg3gui/glossary_tab.py
git commit -m "feat(gui): glossary tab (PySide6) with built-in + custom CRUD"
```

---

### Task 8: App Assembly + Entry Points

**Files:**
- Rewrite: `bg3gui/app.py`
- Rewrite: `bg3gui/__init__.py`
- Create: `bg3_mod_translator.py`
- Modify: `bg3_autokorean_gui.py`

- [ ] **Step 1: Rewrite `bg3gui/app.py`**

```python
# bg3gui/app.py
from __future__ import annotations
import sys

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QLabel,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from bg3core.config import UserConfig, load_config, save_config, get_default_cache_path
from . import theme
from .i18n import load as i18n_load, t
from .titlebar import TitleBar
from .sidebar import NavigationSidebar
from .settings_tab import SettingsTab
from .translate_tab import TranslateTab
from .reviewer_tab import ReviewerTab
from .glossary_tab import GlossaryTab


class App(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        cfg = load_config()
        i18n_load(cfg.app_language)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.resize(900, 620)
        self.setMinimumSize(720, 500)
        self.setStyleSheet(theme.app_stylesheet())

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Title bar
        self._titlebar = TitleBar(self)
        root.addWidget(self._titlebar)

        # Body (sidebar + stacked content)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._sidebar = NavigationSidebar()
        body.addWidget(self._sidebar)

        self._stack = QStackedWidget()
        body.addWidget(self._stack, stretch=1)

        root.addLayout(body, stretch=1)

        # Status bar
        self._status_bar = QWidget()
        self._status_bar.setFixedHeight(22)
        self._status_bar.setStyleSheet(
            f"background:{theme.BG_LOG};border-top:1px solid {theme.DIVIDER};"
        )
        sb_layout = QHBoxLayout(self._status_bar)
        sb_layout.setContentsMargins(14, 0, 14, 0)
        self._lbl_status_left = QLabel(t("translate.status.idle"))
        self._lbl_status_left.setStyleSheet(f"color:{theme.GOLD};font-size:10px;background:transparent;")
        self._lbl_status_right = QLabel("")
        self._lbl_status_right.setStyleSheet(f"color:{theme.TEXT_MUTED};font-size:10px;background:transparent;")
        self._lbl_status_right.setAlignment(Qt.AlignmentFlag.AlignRight)
        sb_layout.addWidget(self._lbl_status_left)
        sb_layout.addStretch()
        sb_layout.addWidget(self._lbl_status_right)
        root.addWidget(self._status_bar)

        # Tabs
        self._settings_tab = SettingsTab(on_config_saved=self._on_config_saved)
        self._translate_tab = TranslateTab()
        self._reviewer_tab = ReviewerTab()
        self._glossary_tab = GlossaryTab()

        for tab in [self._settings_tab, self._translate_tab,
                    self._reviewer_tab, self._glossary_tab]:
            self._stack.addWidget(tab)

        self._stack.setCurrentIndex(1)  # start on translate

        self._sidebar.page_changed.connect(self._on_page_changed)
        self._sidebar.page_changed.connect(self._stack.setCurrentIndex)

        self._cfg = cfg
        self._settings_tab.load_config(cfg)
        self._translate_tab.set_config(cfg)
        self._reviewer_tab.set_config(cfg)
        self._update_status_right(cfg)

    def _on_page_changed(self, idx: int) -> None:
        self._stack.setCurrentIndex(idx)

    def _on_config_saved(self, cfg: UserConfig) -> None:
        self._cfg = cfg
        self._translate_tab.set_config(cfg)
        self._reviewer_tab.set_config(cfg)
        self._update_status_right(cfg)

    def _update_status_right(self, cfg: UserConfig) -> None:
        from bg3core.language import get_profile
        profile = get_profile(cfg.target_language)
        model = cfg.model_preference[0] if cfg.model_preference else "?"
        mcm = "MCM ✓" if cfg.mcm_enabled else "MCM ✗"
        self._lbl_status_right.setText(
            f"{profile.display_name.split('(')[0].strip()} · {model} · {mcm}"
        )
```

- [ ] **Step 2: Rewrite `bg3gui/__init__.py`**

```python
# bg3gui/__init__.py
from .app import App

__all__ = ["App"]
```

- [ ] **Step 3: Create `bg3_mod_translator.py`**

```python
# bg3_mod_translator.py
"""BG3 Mod Translator — 진입점."""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    base = Path(sys._MEIPASS)
else:
    base = Path(__file__).parent

if str(base) not in sys.path:
    sys.path.insert(0, str(base))

from PySide6.QtWidgets import QApplication
from bg3gui.app import App


def main() -> None:
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Update `bg3_autokorean_gui.py`**

```python
# bg3_autokorean_gui.py
"""BG3 Mod Translator — 하위 호환 진입점 (bg3_mod_translator.py로 리디렉션)."""
from bg3_mod_translator import main

if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run all tests**

```
python -m pytest tests/ -v
```
Expected: 83 passed.

- [ ] **Step 6: Smoke test — app launches**

```
python bg3_mod_translator.py
```
기대 동작:
- 앱 창이 열림 (860×620 근처)
- 골드 그라디언트 헤더에 "BG3 MOD TRANSLATOR" + v5.0 표시
- 사이드바에 설정/번역/검수/용어집 메뉴
- 번역 탭이 기본으로 열림
- 창 드래그 이동 가능
- 최소화/최대화/닫기 버튼 동작

- [ ] **Step 7: Final commit**

```
git add bg3gui/app.py bg3gui/__init__.py bg3_mod_translator.py bg3_autokorean_gui.py
git commit -m "feat(gui): app assembly + entry points — BG3 Mod Translator v5.0 완성"
```

---

## Self-Review

**Spec coverage 체크:**
- ✅ PySide6 + BG3 앰버 테마 (theme.py)
- ✅ 커스텀 골드 그라디언트 타이틀바 (titlebar.py)
- ✅ 라벨 사이드바 (sidebar.py)
- ✅ 번역 탭 로그 중심 레이아웃 (translate_tab.py)
- ✅ 설정 탭 — target_language + app_language (settings_tab.py)
- ✅ i18n ko/en (i18n/__init__.py + ko.py + en.py)
- ✅ config.app_language 필드 (config.py)
- ✅ QThread 워커 (workers.py)
- ✅ 검수 탭 (reviewer_tab.py)
- ✅ 용어집 탭 (glossary_tab.py)
- ✅ 신규 진입점 bg3_mod_translator.py
- ✅ 하단 상태바 (app.py)
- ✅ 앱 이름 BG3 Mod Translator

**Type consistency:**
- `t()` 함수: 모든 탭에서 동일하게 사용
- `UserConfig.app_language`: config.py Task 1에서 추가, settings_tab.py Task 4에서 사용
- `Entry.target_text / .new_target / .display_target`: reviewer_tab.py에서 v5.0 필드명 그대로 사용
- `ensure_loca(force=True)`: reviewer_tab.py에서 v5.0 서명 그대로 사용
