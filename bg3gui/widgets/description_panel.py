from __future__ import annotations
from typing import List, Tuple

from PySide6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

from .. import theme


def vertical_divider() -> QFrame:
    """좌측 컨트롤과 우측 설명 패널 사이의 1px 세로 구분선."""
    f = QFrame()
    f.setFixedWidth(1)
    f.setStyleSheet(f"background:{theme.DIVIDER};border:none;")
    return f


class DescriptionPanel(QScrollArea):
    """창 우측에 표시하는 기능 설명 패널.

    (용어, 설명) 목록을 받아 제목 + 항목별 설명으로 렌더링한다. 앱 UI 언어는
    재시작 시에만 바뀌므로 생성 시점의 문구로 한 번만 구성한다(동적 재번역 불필요).
    """

    def __init__(
        self,
        heading: str,
        items: List[Tuple[str, str]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        body = QWidget()
        self.setWidget(body)
        v = QVBoxLayout(body)
        v.setContentsMargins(20, 18, 12, 18)
        v.setSpacing(12)

        if heading:
            h = QLabel(heading)
            h.setWordWrap(True)
            h.setStyleSheet(
                f"color:{theme.GOLD};font-size:13px;font-weight:bold;"
                "background:transparent;"
            )
            v.addWidget(h)

        for term, desc in items:
            term_lbl = QLabel(term)
            term_lbl.setWordWrap(True)
            term_lbl.setStyleSheet(
                f"color:{theme.TEXT_PRIMARY};font-size:11px;font-weight:bold;"
                "background:transparent;"
            )
            v.addWidget(term_lbl)

            desc_lbl = QLabel(desc)
            desc_lbl.setWordWrap(True)
            desc_lbl.setStyleSheet(
                f"color:{theme.TEXT_SECONDARY};font-size:10px;line-height:140%;"
                "background:transparent;"
            )
            v.addWidget(desc_lbl)

        v.addStretch()
