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

        ver = QLabel("v6.0")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet("color:#3a3a3a;font-size:9px;background:transparent;")
        layout.addWidget(ver)

        self._set_active(1)  # translate tab default

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
