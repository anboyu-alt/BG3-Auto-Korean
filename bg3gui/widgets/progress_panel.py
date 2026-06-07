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
        self._lbl.setStyleSheet(
            f"color:{theme.GOLD};font-size:11px;background:transparent;white-space:nowrap;"
        )
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._lbl.setFixedWidth(140)
        layout.addWidget(self._lbl)

    def update(self, current: int, total: int) -> None:
        pct = int(current / total * 100) if total > 0 else 0
        self._bar.setValue(pct)
        self._lbl.setText(t("translate.progress", current=current, total=total, pct=pct))

    def reset(self) -> None:
        self._bar.setValue(0)
        self._lbl.setText(t("translate.progress", current=0, total=0, pct=0))
