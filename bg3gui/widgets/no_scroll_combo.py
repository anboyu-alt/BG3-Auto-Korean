from __future__ import annotations

from PySide6.QtWidgets import QComboBox
from PySide6.QtCore import Qt


class NoScrollComboBox(QComboBox):
    """휠 스크롤로 선택값이 바뀌지 않는 콤보박스.

    스크롤 영역 안에 놓였을 때, 콤보 위에서 마우스 휠을 굴리면 선택값이
    바뀌는 대신 이벤트를 무시해 부모(스크롤 영역)가 페이지를 스크롤하도록
    한다. 콤보를 직접 클릭해 포커스를 준 상태에서는 평소처럼 휠로 항목을
    넘길 수 있다. 드롭다운을 펼친 목록 내부 스크롤도 그대로 동작한다.
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # 휠만으로는 포커스를 얻지 못하게 해, 단순히 지나가며 굴릴 때 값이
        # 바뀌지 않도록 한다(클릭/탭으로는 포커스 가능).
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt 시그니처)
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()
