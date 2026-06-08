from __future__ import annotations
import threading
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QScrollArea, QFrame,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer

from bg3core.config import UserConfig, save_config
from bg3core.language import LANGUAGE_PROFILES
from . import theme
from .i18n import t, t_for
from .widgets.path_picker import PathPicker
from .widgets.no_scroll_combo import NoScrollComboBox

_LANG_OPTIONS = sorted(
    LANGUAGE_PROFILES.values(),
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
        self._model1_combo = NoScrollComboBox()
        layout.addWidget(self._model1_combo)

        layout.addWidget(_row_label(t("settings.model_2")))
        self._model2_combo = NoScrollComboBox()
        layout.addWidget(self._model2_combo)

        # ── UI Scale ──
        layout.addWidget(_row_label(t("settings.ui_scale")))
        self._scale_combo = NoScrollComboBox()
        self._scale_combo.addItems(["auto", "1.0", "1.25", "1.5", "1.75", "2.0"])
        layout.addWidget(self._scale_combo)

        # ── Target Language ──
        layout.addWidget(_row_label(t("settings.target_language")))
        self._lang_combo = NoScrollComboBox()
        self._lang_combo.addItems([p.display_name for p in _LANG_OPTIONS])
        layout.addWidget(self._lang_combo)

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
        prefs = cfg.model_preference or []
        if prefs:
            self._model1_combo.setCurrentText(prefs[0] if len(prefs) > 0 else models[0])
            self._model2_combo.setCurrentText(prefs[1] if len(prefs) > 1 else (models[1] if len(models) > 1 else models[0]))
        self._scale_combo.setCurrentText(cfg.ui_scale)
        self._lang_combo.setCurrentText(
            _FOLDER_TO_DISPLAY.get(cfg.target_language, _LANG_OPTIONS[0].display_name)
        )
        self._app_lang_combo.setCurrentText(
            _APP_LANG_DISPLAY.get(cfg.app_language, "한국어")
        )
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
