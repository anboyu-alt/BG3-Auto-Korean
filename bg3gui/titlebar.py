# bg3gui/titlebar.py
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, QPoint
from bg3core.constants import __version__
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
        self._lbl_subtitle = QLabel(t("app.subtitle", version=__version__))
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
        self._lbl_subtitle.setText(t("app.subtitle", version=__version__))

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
