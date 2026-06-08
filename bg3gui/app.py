from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QStackedWidget, QLabel,
)
from PySide6.QtCore import Qt

from bg3core.config import UserConfig, load_config, save_config
from bg3core.language import get_profile
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

        # Body: sidebar + stack
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
        self._lbl_status_left.setStyleSheet(
            f"color:{theme.GOLD};font-size:10px;background:transparent;"
        )
        self._lbl_status_right = QLabel("")
        self._lbl_status_right.setStyleSheet(
            f"color:{theme.TEXT_MUTED};font-size:10px;background:transparent;"
        )
        self._lbl_status_right.setAlignment(Qt.AlignmentFlag.AlignRight)
        sb_layout.addWidget(self._lbl_status_left)
        sb_layout.addStretch()
        sb_layout.addWidget(self._lbl_status_right)
        root.addWidget(self._status_bar)

        # Tabs
        self._settings_tab = SettingsTab(on_config_saved=self._on_config_saved)
        self._translate_tab = TranslateTab(on_config_saved=self._on_config_saved)
        self._reviewer_tab = ReviewerTab()
        self._glossary_tab = GlossaryTab()

        for tab in [self._settings_tab, self._translate_tab,
                    self._reviewer_tab, self._glossary_tab]:
            self._stack.addWidget(tab)

        self._stack.setCurrentIndex(1)  # start on translate tab

        self._sidebar.page_changed.connect(self._stack.setCurrentIndex)

        self._cfg = cfg
        self._settings_tab.load_config(cfg)
        self._translate_tab.set_config(cfg)
        self._reviewer_tab.set_config(cfg)
        self._update_status_right(cfg)

    def _on_config_saved(self, cfg: UserConfig) -> None:
        self._cfg = cfg
        self._translate_tab.set_config(cfg)
        self._reviewer_tab.set_config(cfg)
        self._update_status_right(cfg)

    def _update_status_right(self, cfg: UserConfig) -> None:
        profile = get_profile(cfg.target_language)
        # Show just the native name without the English part
        lang_name = profile.display_name.split(" (")[0].strip()
        model = cfg.model_preference[0] if cfg.model_preference else "?"
        mcm = "MCM ✓" if cfg.mcm_enabled else "MCM ✗"
        self._lbl_status_right.setText(f"{lang_name} · {model} · {mcm}")
