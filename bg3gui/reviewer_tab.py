from __future__ import annotations
import shutil
import tempfile
import threading
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QTextEdit, QMessageBox, QSplitter,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QKeySequence, QShortcut

from bg3core.config import UserConfig
from bg3core.divine import divine_extract, divine_repack, ensure_loca
from bg3core.mcm.loca_handles import mirror_loca_to_source_languages
from bg3core.reviewer import Entry, ReviewFile, load_review_files, save_modified_xml
from . import theme
from .i18n import t
from .widgets.path_picker import PathPicker
from .widgets.description_panel import DescriptionPanel


class _UnpackWorker(QThread):
    done = Signal(bool)

    def __init__(self, divine_path: str, pak_path: Path, dest: Path, parent=None):
        super().__init__(parent)
        self._divine = divine_path
        self._pak = pak_path
        self._dest = dest

    def run(self):
        ok = divine_extract(self._divine, self._pak, self._dest)
        self.done.emit(ok)


class ReviewerTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cfg: Optional[UserConfig] = None
        self._review_files: List[ReviewFile] = []
        self._current_file: Optional[ReviewFile] = None
        self._current_entries: List[Entry] = []
        self._current_idx: int = 0
        self._show_modified_only = False
        self._temp_dir: Optional[Path] = None
        self._pak_path: Optional[Path] = None

        # 좌측: 검수 컨트롤 ~50% · 우측: 기능 설명 패널 ~50% (드래그로 비율 조절 가능)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        outer_split = QSplitter(Qt.Orientation.Horizontal)
        outer_split.setChildrenCollapsible(False)
        left = QWidget()
        outer_split.addWidget(left)
        panel = self._build_description_panel()
        panel.setMinimumWidth(280)
        outer_split.addWidget(panel)
        outer_split.setStretchFactor(0, 1)
        outer_split.setStretchFactor(1, 1)
        outer_split.setSizes([500, 500])
        root.addWidget(outer_split)

        layout = QVBoxLayout(left)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Top: PAK picker
        top_row = QHBoxLayout()
        self._picker = PathPicker(
            mode="file",
            filetypes=[("PAK files", "*.pak")],
        )
        top_row.addWidget(self._picker)
        self._btn_open = QPushButton(t("review.open"))
        self._btn_open.setFixedWidth(70)
        self._btn_open.clicked.connect(self._open_pak)
        top_row.addWidget(self._btn_open)
        layout.addLayout(top_row)

        # Splitter: file list (left) + editor (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        file_panel = QWidget()
        fp_layout = QVBoxLayout(file_panel)
        fp_layout.setContentsMargins(0, 0, 0, 0)
        fp_layout.setSpacing(4)
        fp_layout.addWidget(QLabel(t("review.files")))
        self._file_list = QListWidget()
        self._file_list.currentRowChanged.connect(self._on_file_select)
        fp_layout.addWidget(self._file_list)
        splitter.addWidget(file_panel)

        edit_panel = QWidget()
        ep_layout = QVBoxLayout(edit_panel)
        ep_layout.setContentsMargins(0, 0, 0, 0)
        ep_layout.setSpacing(6)

        self._nav_label = QLabel(t("review.none"))
        self._nav_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._nav_label.setStyleSheet(f"color:{theme.TEXT_MUTED};background:transparent;")
        ep_layout.addWidget(self._nav_label)

        ep_layout.addWidget(QLabel(t("review.source_lang")))
        self._en_box = QTextEdit()
        self._en_box.setReadOnly(True)
        self._en_box.setFixedHeight(100)
        ep_layout.addWidget(self._en_box)

        ep_layout.addWidget(QLabel(t("review.target_lang")))
        self._kr_box = QTextEdit()
        self._kr_box.setFixedHeight(100)
        ep_layout.addWidget(self._kr_box)

        nav_row = QHBoxLayout()
        self._btn_prev = QPushButton(t("review.prev"))
        self._btn_prev.setFixedWidth(80)
        self._btn_prev.clicked.connect(self._prev)
        nav_row.addWidget(self._btn_prev)
        self._btn_next = QPushButton(t("review.next"))
        self._btn_next.setFixedWidth(80)
        self._btn_next.clicked.connect(self._next)
        nav_row.addWidget(self._btn_next)
        self._btn_save = QPushButton(t("review.save"))
        self._btn_save.clicked.connect(self._save_all)
        nav_row.addWidget(self._btn_save)
        self._btn_modified = QPushButton(t("review.modified_only"))
        self._btn_modified.setCheckable(True)
        self._btn_modified.toggled.connect(self._toggle_modified)
        nav_row.addWidget(self._btn_modified)
        nav_row.addStretch()
        ep_layout.addLayout(nav_row)
        ep_layout.addStretch()

        splitter.addWidget(edit_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([140, 300])
        layout.addWidget(splitter, stretch=1)

        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._save_all)

    def _build_description_panel(self) -> DescriptionPanel:
        items = [
            (t("review.pak_label"), t("desc.review.open")),
            (t("review.files"), t("desc.review.files")),
            (t("review.source_lang"), t("desc.review.edit")),
            (t("review.save"), t("desc.review.save")),
        ]
        return DescriptionPanel(t("desc.review.heading"), items)

    def set_config(self, cfg: UserConfig) -> None:
        self._cfg = cfg

    def _open_pak(self) -> None:
        path_str = self._picker.get()
        if not path_str:
            return
        if not self._cfg or not self._cfg.divine_exe_path:
            QMessageBox.warning(self, t("common.warning"), "설정에서 Divine.exe 경로를 먼저 저장하세요.")
            return
        self._pak_path = Path(path_str)
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        self._temp_dir = Path(tempfile.mkdtemp(prefix="bg3_review_"))
        self._btn_open.setEnabled(False)
        self._unpack_worker = _UnpackWorker(
            self._cfg.divine_exe_path, self._pak_path, self._temp_dir, parent=self
        )
        self._unpack_worker.done.connect(self._on_unpack_done)
        self._unpack_worker.start()

    def _on_unpack_done(self, ok: bool) -> None:
        self._btn_open.setEnabled(True)
        if not ok:
            QMessageBox.critical(self, t("common.error"), "PAK 언팩에 실패했습니다.")
            return
        target_folder = self._cfg.target_language if self._cfg else "Korean"
        review_files = load_review_files(self._temp_dir, target_folder=target_folder)
        if not review_files:
            QMessageBox.warning(self, t("common.warning"),
                "번역 항목을 찾지 못했습니다.\n(대상 언어 폴더가 있는지 확인하세요)")
            return
        self._review_files = review_files
        self._file_list.clear()
        for rf in review_files:
            self._file_list.addItem(rf.filename)
        if review_files:
            self._file_list.setCurrentRow(0)

    def _on_file_select(self, row: int) -> None:
        if 0 <= row < len(self._review_files):
            self._load_file(self._review_files[row])

    def _load_file(self, rf: ReviewFile) -> None:
        self._current_file = rf
        self._current_entries = [
            e for e in rf.entries
            if not self._show_modified_only or e.modified
        ]
        self._current_idx = 0
        self._show_entry()

    def _show_entry(self) -> None:
        if not self._current_entries:
            self._nav_label.setText(t("review.none"))
            self._en_box.clear()
            self._kr_box.clear()
            return
        entry = self._current_entries[self._current_idx]
        total = len(self._current_entries)
        self._nav_label.setText(t("review.nav", idx=self._current_idx + 1, total=total))
        self._en_box.setPlainText(entry.english)
        self._kr_box.setPlainText(entry.display_target)

    def _commit_current(self) -> None:
        if not self._current_entries:
            return
        entry = self._current_entries[self._current_idx]
        new_text = self._kr_box.toPlainText()
        if new_text != entry.target_text:
            entry.modified = True
            entry.new_target = new_text

    def _next(self) -> None:
        self._commit_current()
        if self._current_entries and self._current_idx < len(self._current_entries) - 1:
            self._current_idx += 1
        self._show_entry()

    def _prev(self) -> None:
        self._commit_current()
        if self._current_idx > 0:
            self._current_idx -= 1
        self._show_entry()

    def _save_all(self) -> None:
        self._commit_current()
        if not self._review_files or not self._pak_path or not self._temp_dir:
            return
        modified = [rf for rf in self._review_files if any(e.modified for e in rf.entries)]
        if not modified:
            QMessageBox.information(self, t("common.info"), "수정된 항목이 없습니다.")
            return
        for rf in modified:
            save_modified_xml(rf)
        ensure_loca(self._cfg.divine_exe_path, self._temp_dir, force=True)
        # 번역 파이프라인과 동일하게: 영어 원문 .xml은 보존하고 번역된 .loca를
        # 소스 언어 폴더 .loca로 복사(영어 핸들을 읽는 모드의 인게임 번역 유지).
        mirror_loca_to_source_languages(
            self._temp_dir,
            target_folder=getattr(self._cfg, "target_language", "Korean"),
        )
        out_pak = self._pak_path.parent / f"{self._pak_path.stem}_Reviewed.pak"
        if divine_repack(self._cfg.divine_exe_path, self._temp_dir, out_pak):
            QMessageBox.information(self, t("common.info"), t("review.saved_ok", path=out_pak.name))
        else:
            QMessageBox.critical(self, t("common.error"), "PAK 리팩에 실패했습니다.")

    def _toggle_modified(self, checked: bool) -> None:
        self._show_modified_only = checked
        self._btn_modified.setText(t("review.all") if checked else t("review.modified_only"))
        if self._current_file:
            self._load_file(self._current_file)
