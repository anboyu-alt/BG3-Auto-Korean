from __future__ import annotations
import threading
from typing import Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QMessageBox, QFileDialog, QSplitter,
)
from PySide6.QtCore import Qt

from bg3core.config import UserConfig, save_config
from bg3core.language import LANGUAGE_PROFILES
from bg3core.constants import MODELS_TO_TRY
from . import theme
from .i18n import t
from .workers import TranslationWorker
from .widgets.path_picker import PathPicker
from .widgets.log_view import LogView
from .widgets.progress_panel import ProgressPanel
from .widgets.description_panel import DescriptionPanel

_LANG_OPTIONS = sorted(
    LANGUAGE_PROFILES.values(),
    key=lambda p: (0 if p.folder_name == "Korean" else 1, p.display_name),
)
_FOLDER_TO_DISPLAY = {p.folder_name: p.display_name for p in _LANG_OPTIONS}
_DISPLAY_TO_FOLDER = {p.display_name: p.folder_name for p in _LANG_OPTIONS}

# 모델 선택 목록(기본 + 자주 쓰는 모델). 중복 제거, 순서 유지.
_MODEL_OPTIONS = list(dict.fromkeys(
    list(MODELS_TO_TRY) + ["gemini-2.5-flash", "gemini-2.5-pro"]
))


class TranslateTab(QWidget):
    def __init__(
        self,
        on_config_saved: Callable[[UserConfig], None] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._on_config_saved = on_config_saved
        self._cfg: UserConfig | None = None
        self._worker: TranslationWorker | None = None
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._running = False

        # 좌측: 컨트롤+로그 ~50% · 우측: 기능 설명 패널 ~50% (드래그로 비율 조절 가능)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        left = QWidget()
        split.addWidget(left)
        panel = self._build_description_panel()
        panel.setMinimumWidth(280)
        split.addWidget(panel)
        split.setStretchFactor(0, 1)
        split.setStretchFactor(1, 1)
        split.setSizes([500, 500])
        root.addWidget(split)

        layout = QVBoxLayout(left)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        # File picker row (file + folder button)
        file_row = QHBoxLayout()
        self._picker = PathPicker(
            mode="file",
            filetypes=[("PAK files", "*.pak"), ("All files", "*.*")],
            label_key="translate.browse",
        )
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
        self._lang_combo = QComboBox()
        self._lang_combo.addItems([p.display_name for p in _LANG_OPTIONS])
        self._lang_combo.currentTextChanged.connect(self._on_lang_changed)
        lang_row.addWidget(self._lang_combo)
        self._model_combo = QComboBox()
        self._model_combo.addItems(_MODEL_OPTIONS)
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
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

        # Log (dominant — stretch=1)
        self._log = LogView()
        layout.addWidget(self._log, stretch=1)

    def _build_description_panel(self) -> DescriptionPanel:
        items = [
            (t("translate.file_label"), t("desc.translate.file")),
            (t("translate.target_lang"), t("desc.translate.lang")),
            (t("translate.model"), t("desc.translate.model")),
            (t("translate.start"), t("desc.translate.controls")),
        ]
        return DescriptionPanel(t("desc.translate.heading"), items)

    def _pick_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, t("translate.file_label"))
        if path:
            self._picker.set(path)

    def set_config(self, cfg: UserConfig) -> None:
        self._cfg = cfg
        # 프로그램이 콤보를 채우는 동안에는 변경 시그널을 막아, 사용자 선택이
        # 아닌 경우 저장이 트리거되지 않도록 한다.
        self._lang_combo.blockSignals(True)
        self._lang_combo.setCurrentText(
            _FOLDER_TO_DISPLAY.get(cfg.target_language, _LANG_OPTIONS[0].display_name)
        )
        self._lang_combo.blockSignals(False)
        self._model_combo.blockSignals(True)
        if cfg.model_preference:
            self._model_combo.setCurrentText(cfg.model_preference[0])
        self._model_combo.blockSignals(False)

    def _on_model_changed(self, model_name: str) -> None:
        """사용자가 AI 모델을 바꾸면 즉시 config에 영속화한다(엔진은 이 값을 1순위로 사용)."""
        if not self._cfg or not model_name:
            return
        self._cfg.model_preference = [model_name]
        save_config(self._cfg)
        if self._on_config_saved:
            self._on_config_saved(self._cfg)

    def _on_lang_changed(self, display_name: str) -> None:
        """사용자가 번역 대상 언어를 바꾸면 즉시 config에 영속화한다.

        대상 언어 선택은 번역 탭에만 있으므로(설정 탭에서 제거됨) 여기서 저장해야
        재시작 후에도 유지되고 상태바도 갱신된다.
        """
        if not self._cfg:
            return
        self._cfg.target_language = _DISPLAY_TO_FOLDER.get(display_name, "Korean")
        save_config(self._cfg)
        if self._on_config_saved:
            self._on_config_saved(self._cfg)

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
