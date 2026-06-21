from __future__ import annotations
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QTreeWidget, QTreeWidgetItem,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView,
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

        # Custom tab — Excel식 인라인 편집 테이블
        custom_w = QWidget()
        cl = QVBoxLayout(custom_w)
        cl.setContentsMargins(8, 8, 8, 8)
        lbl_custom = QLabel(t("glossary.custom_info"))
        lbl_custom.setObjectName("label_muted")
        cl.addWidget(lbl_custom)

        self._custom_table = QTableWidget(0, 2)
        self._custom_table.setHorizontalHeaderLabels([t("glossary.col_en"), t("glossary.col_ko")])
        self._custom_table.verticalHeader().setVisible(False)
        self._custom_table.setAlternatingRowColors(True)
        self._custom_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        chdr = self._custom_table.horizontalHeader()
        chdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        chdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._custom_table.setColumnWidth(0, 300)
        self._custom_table.cellChanged.connect(self._on_custom_cell_changed)
        cl.addWidget(self._custom_table)

        btn_row = QHBoxLayout()
        self._btn_del = QPushButton(t("glossary.delete"))
        self._btn_del.setStyleSheet(
            f"QPushButton{{background:{theme.CLOSE_BG};border:1px solid #8b3a3a;color:#ff9999;}}"
            f"QPushButton:hover{{background:#7a2020;}}"
        )
        self._btn_del.clicked.connect(self._delete_selected_row)
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
        self._populate(self._base_tree, self._base_all)
        self._populate_custom_table()

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
        # 검색은 기본 용어집(많음)에만 적용. 내 용어집은 인라인 편집 테이블이라
        # 항상 전체를 보여준다(보통 소량).
        q = text.strip().lower()
        rows = [(e, k) for e, k in self._base_all if not q or q in e.lower() or q in k.lower()]
        self._populate(self._base_tree, rows)

    def _set_custom_data(self, data: dict) -> None:
        """테스트/외부에서 내 용어집 데이터를 주입하고 테이블을 다시 그린다."""
        self._custom_data = dict(data)
        self._populate_custom_table()

    def _cell_text(self, row: int, col: int) -> str:
        item = self._custom_table.item(row, col)
        return item.text() if item else ""

    def _populate_custom_table(self) -> None:
        self._custom_table.blockSignals(True)
        rows = list(self._custom_data.items())
        self._custom_table.setRowCount(len(rows) + 1)  # 맨 아래 신규 입력용 빈 행
        for r, (en, ko) in enumerate(rows):
            self._custom_table.setItem(r, 0, QTableWidgetItem(en))
            self._custom_table.setItem(r, 1, QTableWidgetItem(ko))
        empty = len(rows)
        self._custom_table.setItem(empty, 0, QTableWidgetItem(""))
        self._custom_table.setItem(empty, 1, QTableWidgetItem(""))
        self._custom_table.blockSignals(False)

    def _rebuild_custom_data(self) -> None:
        data: dict = {}
        for r in range(self._custom_table.rowCount()):
            en = self._cell_text(r, 0).strip()
            ko = self._cell_text(r, 1).strip()
            if en:
                data[en] = ko
        self._custom_data = data

    def _on_custom_cell_changed(self, row: int, col: int) -> None:
        self._rebuild_custom_data()
        # 마지막 행이 채워졌으면 새 빈 행을 추가해 연속 입력을 가능하게 한다.
        last = self._custom_table.rowCount() - 1
        if last < 0 or self._cell_text(last, 0).strip() or self._cell_text(last, 1).strip():
            self._custom_table.blockSignals(True)
            r = self._custom_table.rowCount()
            self._custom_table.insertRow(r)
            self._custom_table.setItem(r, 0, QTableWidgetItem(""))
            self._custom_table.setItem(r, 1, QTableWidgetItem(""))
            self._custom_table.blockSignals(False)

    def _delete_selected_row(self) -> None:
        row = self._custom_table.currentRow()
        if row < 0 or row >= self._custom_table.rowCount():
            return
        self._custom_table.blockSignals(True)
        self._custom_table.removeRow(row)
        self._custom_table.blockSignals(False)
        self._rebuild_custom_data()

    def _save(self) -> None:
        self._rebuild_custom_data()
        save_custom_glossary(self._custom_data)
        self._lbl_saved.setText(t("glossary.saved", count=len(self._custom_data)))
        QTimer.singleShot(3000, lambda: self._lbl_saved.setText(""))
