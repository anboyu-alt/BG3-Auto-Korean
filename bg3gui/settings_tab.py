from __future__ import annotations
import threading
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QScrollArea, QFrame,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer

from bg3core.config import UserConfig, save_config, auto_detect_bg3
from bg3core.language import LANGUAGE_PROFILES, UI_LANG_CODE
from . import theme
from .i18n import t, t_for
from .widgets.path_picker import PathPicker
from .widgets.no_scroll_combo import NoScrollComboBox
from .widgets.description_panel import DescriptionPanel, vertical_divider

# 번역 대상 언어 선택은 번역 탭에만 둔다(설정 탭에서는 제거).
# 앱 UI 언어 = 15개 언어. 라벨은 각 언어의 표시명(예: "한국어 (Korean)").
_APP_LANG_OPTIONS = [
    (LANGUAGE_PROFILES[fn].display_name, code) for fn, code in UI_LANG_CODE.items()
]
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

        # 좌측: 컨트롤(스크롤) ~50% · 우측: 기능 설명 패널 ~50%
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(scroll, stretch=1)
        outer.addWidget(vertical_divider())
        outer.addWidget(self._build_description_panel(), stretch=1)

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
        self._btn_show.setMinimumWidth(64)
        self._btn_show.setCheckable(True)
        self._btn_show.toggled.connect(self._toggle_api_visibility)
        api_row.addWidget(self._btn_show)
        layout.addLayout(api_row)

        # ── BG3 설치 폴더 ──
        layout.addWidget(_row_label(t("settings.bg3_path")))
        self._bg3_picker = PathPicker(mode="dir")
        layout.addWidget(self._bg3_picker)

        # AI 모델 선택은 번역 탭에만 둔다(설정 탭에서는 제거).

        # ── UI Scale ──
        layout.addWidget(_row_label(t("settings.ui_scale")))
        self._scale_combo = NoScrollComboBox()
        self._scale_combo.addItems(["auto", "1.0", "1.25", "1.5", "1.75", "2.0"])
        layout.addWidget(self._scale_combo)

        # ── App UI Language ──
        layout.addWidget(_row_label(t("settings.app_language")))
        self._app_lang_combo = NoScrollComboBox()
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
        self._official_check = QCheckBox(t("settings.use_official_glossary"))
        layout.addWidget(self._official_check)

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

    def _build_description_panel(self) -> DescriptionPanel:
        items = [
            (t("settings.api_key"), t("desc.settings.api_key")),
            (t("settings.bg3_path"), t("desc.settings.bg3")),
            (t("settings.ui_scale"), t("desc.settings.ui_scale")),
            (t("settings.app_language"), t("desc.settings.app_lang")),
            (t("settings.cache_path"), t("desc.settings.cache")),
            (t("settings.skip_existing"), t("desc.settings.skip")),
            (t("settings.mcm_enabled"), t("desc.settings.mcm")),
            (t("settings.use_official_glossary"), t("desc.settings.official")),
        ]
        return DescriptionPanel(t("desc.settings.heading"), items)

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
        # 비어 있으면 자동 감지값으로 채워 보여준다(저장 전엔 미저장).
        self._bg3_picker.set(cfg.bg3_install_path or (auto_detect_bg3() or ""))
        self._scale_combo.setCurrentText(cfg.ui_scale)
        self._app_lang_combo.setCurrentText(
            _APP_LANG_DISPLAY.get(cfg.app_language, "한국어")
        )
        self._cache_picker.set(cfg.cache_path)
        self._skip_check.setChecked(cfg.skip_if_korean_exists)
        self._mcm_check.setChecked(cfg.mcm_enabled)
        self._official_check.setChecked(getattr(cfg, "use_official_glossary", False))

    def _build_config(self) -> UserConfig:
        cfg = UserConfig()
        cfg.api_key = self._api_edit.text().strip()
        cfg.bg3_install_path = self._bg3_picker.get()
        cfg.ui_scale = self._scale_combo.currentText()
        cfg.app_language = _APP_LANG_CODE.get(
            self._app_lang_combo.currentText(), "ko"
        )
        cfg.cache_path = self._cache_picker.get()
        cfg.skip_if_korean_exists = self._skip_check.isChecked()
        cfg.mcm_enabled = self._mcm_check.isChecked()
        cfg.use_official_glossary = self._official_check.isChecked()
        if self._cfg:
            # 번역 대상 언어·AI 모델은 번역 탭에서 관리하므로 설정 저장 시 기존 값을 보존한다.
            cfg.target_language = self._cfg.target_language
            cfg.model_preference = self._cfg.model_preference
            cfg.last_pak_dir = self._cfg.last_pak_dir
            cfg.last_output_dir = self._cfg.last_output_dir
            cfg.log_dir = self._cfg.log_dir
        return cfg

    def _save(self) -> None:
        cfg = self._build_config()
        prev_lang = self._cfg.app_language if self._cfg else "ko"
        prev_scale = self._cfg.ui_scale if self._cfg else "auto"
        save_config(cfg)
        self._cfg = cfg
        self._on_config_saved(cfg)
        self._show_status(t("settings.saved"))
        if cfg.app_language != prev_lang:
            # 안내는 새로 선택한 UI 언어로 보여줘야 이용자가 알아본다.
            QMessageBox.information(
                self,
                t_for(cfg.app_language, "common.info"),
                t_for(cfg.app_language, "settings.lang_restart"),
            )
        elif cfg.ui_scale != prev_scale:
            # 배율은 런타임에 못 바꾸고 재시작해야 적용된다.
            QMessageBox.information(self, t("common.info"), t("settings.scale_restart"))

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
