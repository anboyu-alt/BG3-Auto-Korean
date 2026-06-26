from __future__ import annotations
import copy

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame,
)
from PySide6.QtCore import Qt

from bg3core.config import UserConfig
from . import theme
from .i18n import t
from .widgets.path_picker import PathPicker


class FirstRunWizard(QDialog):
    """첫 실행 안내 위저드.

    설정 파일이 없을 때 한 번 떠서 API 키·BG3 설치 폴더를 한자리에서 안내·입력받는다.
    BG3는 전달된 config(자동 감지값)로 prefill한다.
    여기서 다루지 않는 나머지 설정(언어 등)은 그대로 보존한다.
    """

    def __init__(self, cfg: UserConfig, parent=None) -> None:
        super().__init__(parent)
        self._cfg = copy.deepcopy(cfg)
        self.setWindowTitle(t("wizard.title"))
        self.setModal(True)
        self.setMinimumWidth(540)
        self.setStyleSheet(theme.app_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(12)

        title = QLabel(t("wizard.heading"))
        title.setStyleSheet(f"color:{theme.GOLD};font-size:16px;font-weight:bold;background:transparent;")
        layout.addWidget(title)

        intro = QLabel(t("wizard.intro"))
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color:{theme.TEXT_SECONDARY};background:transparent;")
        layout.addWidget(intro)

        div = QFrame()
        div.setObjectName("divider")
        div.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(div)

        # 1. API Key (필수)
        layout.addWidget(self._step_label(t("wizard.step_api")))
        self._api_edit = QLineEdit()
        self._api_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_edit.setText(self._cfg.api_key)
        layout.addWidget(self._api_edit)
        api_hint = QLabel(t("wizard.api_hint"))
        api_hint.setWordWrap(True)
        api_hint.setStyleSheet(f"color:{theme.TEXT_MUTED};font-size:11px;background:transparent;")
        layout.addWidget(api_hint)

        # 2. BG3 설치 폴더 (자동 감지 prefill, 선택)
        layout.addWidget(self._step_label(t("wizard.step_bg3")))
        self._bg3_picker = PathPicker(mode="dir")
        self._bg3_picker.set(self._cfg.bg3_install_path)
        layout.addWidget(self._bg3_picker)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_later = QPushButton(t("wizard.later"))
        self._btn_later.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_later)
        self._btn_start = QPushButton(t("wizard.start"))
        self._btn_start.setObjectName("btn_start")
        self._btn_start.setFixedHeight(36)
        self._btn_start.clicked.connect(self.accept)
        btn_row.addWidget(self._btn_start)
        layout.addLayout(btn_row)

    def _step_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:{theme.TEXT_PRIMARY};font-weight:bold;background:transparent;")
        return lbl

    def result_config(self) -> UserConfig:
        out = copy.deepcopy(self._cfg)
        out.api_key = self._api_edit.text().strip()
        out.bg3_install_path = self._bg3_picker.get()
        return out
