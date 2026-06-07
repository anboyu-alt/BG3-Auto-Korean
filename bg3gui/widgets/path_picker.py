# bg3gui/widgets/path_picker.py
from __future__ import annotations
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog
from PySide6.QtCore import Signal
from .. import theme
from ..i18n import t


class PathPicker(QWidget):
    path_changed = Signal(str)

    def __init__(
        self,
        parent: QWidget | None = None,
        mode: str = "file",
        label_key: str = "common.browse",
        filetypes: list[tuple[str, str]] | None = None,
    ) -> None:
        super().__init__(parent)
        self._mode = mode
        self._filetypes = filetypes or [("All files", "*.*")]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._edit = QLineEdit()
        layout.addWidget(self._edit)

        self._btn = QPushButton(t(label_key))
        self._btn.setFixedWidth(60)
        self._btn.clicked.connect(self._browse)
        layout.addWidget(self._btn)

    def _browse(self) -> None:
        if self._mode == "dir":
            path = QFileDialog.getExistingDirectory(self, t("common.browse"), self._edit.text())
        else:
            filter_str = ";;".join(f"{name} ({ext})" for name, ext in self._filetypes)
            path, _ = QFileDialog.getOpenFileName(
                self, t("common.browse"), self._edit.text(), filter_str
            )
        if path:
            self._edit.setText(path)
            self.path_changed.emit(path)

    def get(self) -> str:
        return self._edit.text().strip()

    def set(self, path: str) -> None:
        self._edit.setText(path)
