# bg3gui/widgets/log_view.py
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
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
