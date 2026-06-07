from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QInputDialog, QMessageBox,
)
from PySide6.QtCore import Qt, QTimer

from bg3core.glossary import GLOSSARY, load_custom_glossary, save_custom_glossary
from . import theme
from .i18n import t


class GlossaryTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._custom_data: dict = dict(load_custom_glossary())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Search row
        search_row = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText(t("glossary.search_placeholder"))
        self._search.textChanged.connect(self._apply_filter)
        search_row.addWidget(self._search)
        btn_clear = QPushButton(t("glossary.clear"))
        btn_clear.setFixedWidth(56)
        btn_clear.clicked.connect(lambda: self._search.clear())
        search_row.addWidget(btn_clear)
        layout.addLayout(search_row)

        # Inner tabs
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{border:1px solid {theme.DIVIDER};border-radius:4px;}}
            QTabBar::tab {{
                background:{theme.BG_CARD};color:{theme.TEXT_SECONDARY};
                padding:6px 14px;border-radius:4px 4px 0 0;margin-right:2px;
            }}
            QTabBar::tab:selected {{
                background:#2a2000;color:{theme.GOLD};
                border-bottom:2px solid {theme.GOLD};
            }}
        """)

        # Built-in tab
        builtin_w = QWidget()
        bl = QVBoxLayout(builtin_w)
        bl.setContentsMargins(8, 8, 8, 8)
        lbl_info = QLabel(t("glossary.builtin_info", count=len(GLOSSARY)))
        lbl_info.setObjectName("label_muted")
        bl.addWidget(lbl_info)
        self._base_tree = self._make_tree()
        bl.addWidget(self._base_tree)
        self._tabs.addTab(builtin_w, t("glossary.builtin_tab"))

        # Custom tab
        custom_w = QWidget()
        cl = QVBoxLayout(custom_w)
        cl.setContentsMargins(8, 8, 8, 8)
        lbl_custom = QLabel(t("glossary.custom_info"))
        lbl_custom.setObjectName("label_muted")
        cl.addWidget(lbl_custom)
        self._custom_tree = self._make_tree()
        self._custom_tree.itemDoubleClicked.connect(lambda *_: self._edit_entry())
        cl.addWidget(self._custom_tree)

        btn_row = QHBoxLayout()
        self._btn_add = QPushButton(t("glossary.add"))
        self._btn_add.clicked.connect(self._add_entry)
        btn_row.addWidget(self._btn_add)
        self._btn_edit = QPushButton(t("glossary.edit"))
        self._btn_edit.clicked.connect(self._edit_entry)
        btn_row.addWidget(self._btn_edit)
        self._btn_del = QPushButton(t("glossary.delete"))
        self._btn_del.setStyleSheet(
            f"QPushButton{{background:{theme.CLOSE_BG};border:1px solid #8b3a3a;color:#ff9999;}}"
            f"QPushButton:hover{{background:#7a2020;}}"
        )
        self._btn_del.clicked.connect(self._delete_entry)
        btn_row.addWidget(self._btn_del)
        self._btn_save = QPushButton(t("glossary.save"))
        self._btn_save.setObjectName("btn_start")
        self._btn_save.clicked.connect(self._save)
        btn_row.addWidget(self._btn_save)
        self._lbl_saved = QLabel("")
        self._lbl_saved.setStyleSheet(f"color:{theme.GOLD};background:transparent;")
        btn_row.addWidget(self._lbl_saved)
        btn_row.addStretch()
        cl.addLayout(btn_row)
        self._tabs.addTab(custom_w, t("glossary.custom_tab"))

        layout.addWidget(self._tabs, stretch=1)

        self._base_all: list[tuple[str, str]] = list(GLOSSARY.items())
        self._custom_all: list[tuple[str, str]] = list(self._custom_data.items())
        self._populate(self._base_tree, self._base_all)
        self._populate(self._custom_tree, self._custom_all)

    def _make_tree(self) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setHeaderLabels([t("glossary.col_en"), t("glossary.col_ko")])
        tree.setAlternatingRowColors(True)
        tree.header().setStretchLastSection(True)
        tree.setColumnWidth(0, 300)
        return tree

    def _populate(self, tree: QTreeWidget, rows: list[tuple[str, str]]) -> None:
        tree.clear()
        for en, ko in rows:
            item = QTreeWidgetItem([en, ko])
            tree.addTopLevelItem(item)

    def _apply_filter(self, text: str) -> None:
        q = text.strip().lower()
        def filt(rows):
            return [(e, k) for e, k in rows if not q or q in e.lower() or q in k.lower()]
        self._populate(self._base_tree, filt(self._base_all))
        self._populate(self._custom_tree, filt(self._custom_all))

    def _selected_custom(self) -> tuple[str, str] | None:
        items = self._custom_tree.selectedItems()
        if not items:
            return None
        return items[0].text(0), items[0].text(1)

    def _add_entry(self) -> None:
        en, ok = QInputDialog.getText(self, t("glossary.add"), t("glossary.ask_en"))
        if not ok or not en.strip():
            return
        en = en.strip()
        ko, ok2 = QInputDialog.getText(self, t("glossary.add"), t("glossary.ask_ko", en=en))
        if not ok2 or not ko.strip():
            return
        self._custom_data[en] = ko.strip()
        self._refresh_custom()

    def _edit_entry(self) -> None:
        sel = self._selected_custom()
        if not sel:
            QMessageBox.warning(self, t("common.warning"), t("glossary.select_first"))
            return
        en, ko = sel
        new_ko, ok = QInputDialog.getText(
            self, t("glossary.edit"), t("glossary.ask_edit", en=en), text=ko
        )
        if ok and new_ko.strip():
            self._custom_data[en] = new_ko.strip()
            self._refresh_custom()

    def _delete_entry(self) -> None:
        sel = self._selected_custom()
        if not sel:
            QMessageBox.warning(self, t("common.warning"), t("glossary.select_first"))
            return
        en, _ = sel
        if QMessageBox.question(
            self, t("glossary.delete"), t("glossary.confirm_delete", en=en),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        ) == QMessageBox.StandardButton.Yes:
            self._custom_data.pop(en, None)
            self._refresh_custom()

    def _refresh_custom(self) -> None:
        self._custom_all = list(self._custom_data.items())
        self._apply_filter(self._search.text())

    def _save(self) -> None:
        save_custom_glossary(self._custom_data)
        self._lbl_saved.setText(t("glossary.saved", count=len(self._custom_data)))
        QTimer.singleShot(3000, lambda: self._lbl_saved.setText(""))
