from __future__ import annotations
import shutil
import tempfile
import threading
from pathlib import Path
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QSplitter, QComboBox, QScrollArea, QFrame, QPlainTextEdit,
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QKeySequence, QShortcut

from bg3core.config import UserConfig
from bg3core.packio import extract_pak, repack_pak, ensure_loca
from bg3core.mcm.loca_handles import mirror_loca_to_source_languages
from bg3core.reviewer import Entry, ReviewFile, load_review_files, save_modified_xml
from . import theme
from .i18n import t
from .widgets.path_picker import PathPicker
from .widgets.description_panel import DescriptionPanel


class _UnpackWorker(QThread):
    done = Signal(bool)

    def __init__(self, pak_path: Path, dest: Path, parent=None):
        super().__init__(parent)
        self._pak = pak_path
        self._dest = dest

    def run(self):
        ok = extract_pak(self._pak, self._dest)
        self.done.emit(ok)


class ReviewerTab(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cfg: Optional[UserConfig] = None
        self._review_files: List[ReviewFile] = []
        self._current_file: Optional[ReviewFile] = None
        self._current_entries: List[Entry] = []
        self._editors: List[QPlainTextEdit] = []
        self._source_labels: List[QLabel] = []
        self._show_modified_only = False
        self._temp_dir: Optional[Path] = None
        self._pak_path: Optional[Path] = None

        # 좌측: 검수 컨트롤 · 우측: 도움말(접기 가능). 검수 폭이 중요해 표 쪽을 넓게.
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        outer_split = QSplitter(Qt.Orientation.Horizontal)
        outer_split.setChildrenCollapsible(False)
        left = QWidget()
        outer_split.addWidget(left)
        self._desc_panel = self._build_description_panel()
        self._desc_panel.setMinimumWidth(200)
        outer_split.addWidget(self._desc_panel)
        outer_split.setStretchFactor(0, 4)
        outer_split.setStretchFactor(1, 1)
        outer_split.setSizes([820, 220])
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

        # 파일 드롭다운 (번역 파일이 여러 개일 때만 보임)
        self._file_combo = QComboBox()
        self._file_combo.currentIndexChanged.connect(self._on_file_index)
        self._file_combo.hide()
        layout.addWidget(self._file_combo)

        # Toolbar: 카운트 · 수정만 보기 · 저장 · 도움말 토글
        toolbar = QHBoxLayout()
        self._count_label = QLabel(t("review.none"))
        self._count_label.setStyleSheet(f"color:{theme.TEXT_MUTED};background:transparent;")
        toolbar.addWidget(self._count_label)
        toolbar.addStretch()
        self._btn_modified = QPushButton(t("review.modified_only"))
        self._btn_modified.setCheckable(True)
        self._btn_modified.toggled.connect(self._toggle_modified)
        toolbar.addWidget(self._btn_modified)
        self._btn_save = QPushButton(t("review.save"))
        self._btn_save.clicked.connect(self._save_all)
        toolbar.addWidget(self._btn_save)
        self._btn_help = QPushButton(t("review.toggle_help"))
        self._btn_help.setCheckable(True)
        self._btn_help.setChecked(True)
        self._btn_help.toggled.connect(self._toggle_help)
        toolbar.addWidget(self._btn_help)
        layout.addLayout(toolbar)

        # 카드 리스트: 항목마다 [원문 ↑ / 번역 ↓] 세로 블록을 쌓아 스크롤한다.
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        self._cards_host = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_host)
        self._cards_layout.setContentsMargins(0, 0, 8, 0)
        self._cards_layout.setSpacing(10)
        self._cards_layout.addStretch()
        self._scroll.setWidget(self._cards_host)
        layout.addWidget(self._scroll, stretch=1)

        QShortcut(QKeySequence("Ctrl+S"), self).activated.connect(self._save_all)

    def _toggle_help(self, checked: bool) -> None:
        self._desc_panel.setVisible(checked)

    def _build_description_panel(self) -> DescriptionPanel:
        items = [
            (t("review.pak_label"), t("desc.review.open")),
            (t("review.source_lang"), t("desc.review.edit")),
            (t("review.save"), t("desc.review.save")),
        ]
        return DescriptionPanel(t("desc.review.heading"), items)

    def set_config(self, cfg: UserConfig) -> None:
        self._cfg = cfg

    # ── PAK 열기 ─────────────────────────────────────────────
    def _open_pak(self) -> None:
        path_str = self._picker.get()
        if not path_str:
            return
        self._pak_path = Path(path_str)
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        self._temp_dir = Path(tempfile.mkdtemp(prefix="bg3_review_"))
        self._btn_open.setEnabled(False)
        self._unpack_worker = _UnpackWorker(
            self._pak_path, self._temp_dir, parent=self
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
        self._show_review_files(review_files)

    def _show_review_files(self, review_files: List[ReviewFile]) -> None:
        """검수 파일들을 UI에 채운다. 1개면 콤보를 숨기고 자동 로드, 여러 개면 콤보로 선택."""
        self._review_files = review_files
        self._file_combo.blockSignals(True)
        self._file_combo.clear()
        for rf in review_files:
            self._file_combo.addItem(rf.filename)
        self._file_combo.blockSignals(False)
        self._file_combo.setVisible(len(review_files) > 1)
        if review_files:
            self._file_combo.setCurrentIndex(0)
            self._load_file(review_files[0])

    def _on_file_index(self, idx: int) -> None:
        if 0 <= idx < len(self._review_files):
            self._load_file(self._review_files[idx])

    # ── 카드 채우기 ──────────────────────────────────────────
    def _load_file(self, rf: ReviewFile) -> None:
        self._current_file = rf
        self._current_entries = [
            e for e in rf.entries
            if not self._show_modified_only or e.modified
        ]
        self._populate_cards()

    def _clear_cards(self) -> None:
        # addStretch 항목 하나를 남기고 카드 위젯을 모두 제거한다.
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._editors = []
        self._source_labels = []

    def _populate_cards(self) -> None:
        self._clear_cards()
        for idx, entry in enumerate(self._current_entries):
            card = self._make_card(idx, entry)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
        self._update_count()
        # 레이아웃이 폭을 확정한 다음 틱에 줄바꿈 기준 높이를 다시 맞춘다.
        QTimer.singleShot(0, self._autosize_all)

    def _autosize_all(self) -> None:
        for ed in self._editors:
            self._autosize(ed)

    def _make_card(self, idx: int, entry: Entry) -> QFrame:
        card = QFrame()
        card.setObjectName("review_card")
        card.setStyleSheet(
            "QFrame#review_card{background:%s;border:1px solid %s;border-radius:6px;}"
            % (theme.BG_CARD, theme.DIVIDER)
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 12)
        cl.setSpacing(6)

        # 원문: 라벨로 전체 표시(줄바꿈) — 길어도 안 잘림. 복사용 선택 가능.
        src = QLabel(entry.english)
        src.setWordWrap(True)
        src.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        src.setStyleSheet(f"color:{theme.TEXT_SECONDARY};background:transparent;")
        cl.addWidget(src)

        # 번역: 편집 가능. 내용 길이에 맞춰 높이 자동 조절.
        tgt = QPlainTextEdit(entry.display_target)
        tgt.setStyleSheet(
            f"QPlainTextEdit{{background:{theme.BG_LOG};color:{theme.TEXT_PRIMARY};"
            f"border:1px solid {theme.DIVIDER};border-radius:4px;padding:4px;}}"
        )
        tgt.textChanged.connect(lambda i=idx: self._on_edit(i))
        tgt.textChanged.connect(lambda e=tgt: self._autosize(e))
        cl.addWidget(tgt)
        self._autosize(tgt)

        self._editors.append(tgt)
        self._source_labels.append(src)
        return card

    def _autosize(self, editor: QPlainTextEdit) -> None:
        # 실제 줄바꿈된 문서 높이에 맞춰 조절(최소 2줄, 너무 길면 상한 후 내부 스크롤).
        doc = editor.document()
        width = editor.viewport().width()
        if width > 0:
            doc.setTextWidth(width)
        h = int(doc.size().height() + editor.frameWidth() * 2 + 10)
        min_h = int(editor.fontMetrics().lineSpacing() * 2 + 14)
        editor.setFixedHeight(max(min_h, min(h, 320)))

    def resizeEvent(self, event) -> None:
        # 폭이 바뀌면(또는 처음 표시되면) 줄바꿈이 달라지므로 카드 높이를 다시 맞춘다.
        super().resizeEvent(event)
        self._autosize_all()

    def _update_count(self) -> None:
        if not self._current_entries:
            self._count_label.setText(t("review.none"))
            return
        modified = sum(1 for e in self._current_entries if e.modified)
        self._count_label.setText(
            t("review.count", total=len(self._current_entries), modified=modified)
        )

    def _on_edit(self, idx: int) -> None:
        if not (0 <= idx < len(self._current_entries)):
            return
        entry = self._current_entries[idx]
        new_text = self._editors[idx].toPlainText()
        if new_text != entry.target_text:
            entry.modified = True
            entry.new_target = new_text
            self._update_count()

    # ── 저장 / 필터 / 도움말 ─────────────────────────────────
    def _save_all(self) -> None:
        if not self._review_files or not self._pak_path or not self._temp_dir:
            return
        modified = [rf for rf in self._review_files if any(e.modified for e in rf.entries)]
        if not modified:
            QMessageBox.information(self, t("common.info"), "수정된 항목이 없습니다.")
            return
        for rf in modified:
            save_modified_xml(rf)
        ensure_loca(self._temp_dir, force=True)
        mirror_loca_to_source_languages(
            self._temp_dir,
            target_folder=getattr(self._cfg, "target_language", "Korean"),
        )
        out_pak = self._pak_path.parent / f"{self._pak_path.stem}_Reviewed.pak"
        if repack_pak(self._temp_dir, out_pak):
            QMessageBox.information(self, t("common.info"), t("review.saved_ok", path=out_pak.name))
        else:
            QMessageBox.critical(self, t("common.error"), "PAK 리팩에 실패했습니다.")

    def _toggle_modified(self, checked: bool) -> None:
        self._show_modified_only = checked
        self._btn_modified.setText(t("review.all") if checked else t("review.modified_only"))
        if self._current_file:
            self._load_file(self._current_file)
