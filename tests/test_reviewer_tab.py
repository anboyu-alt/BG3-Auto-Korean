"""① 검수 탭 — 세로 카드 리스트 UI 동작 테스트 (offscreen Qt).

항목마다 [원문(읽기전용 라벨, 전체표시) ↑ / 번역(편집) ↓]을 세로로 쌓고,
파일이 여러 개면 상단 드롭다운으로 고른다(1개면 숨김). 코어(bg3core.reviewer)는
그대로, UI만 바꾼다.
"""
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _make_review_file(name="test.xml"):
    from bg3core.reviewer import Entry, ReviewFile
    entries = [
        Entry(contentuid="h1", english="Fireball", target_text="화염구"),
        Entry(contentuid="h2", english="Haste", target_text="가속"),
        Entry(contentuid="h3", english="Bless", target_text="축복"),
    ]
    return ReviewFile(name, entries, Path("x.xml"), "<xml/>")


def _new_tab(qapp):
    from bg3gui.reviewer_tab import ReviewerTab
    return ReviewerTab()


# ── 카드 로드 ────────────────────────────────────────────────
def test_loads_entries_as_cards(qapp):
    tab = _new_tab(qapp)
    rf = _make_review_file()
    tab._load_file(rf)
    assert len(tab._editors) == 3
    assert len(tab._source_labels) == 3
    assert tab._source_labels[0].text() == "Fireball"
    assert tab._editors[0].toPlainText() == "화염구"
    assert tab._source_labels[2].text() == "Bless"


def test_source_label_is_readonly(qapp):
    # 원문은 편집 위젯이 아니라 라벨이어야 한다(읽기전용·전체표시).
    from PySide6.QtWidgets import QLabel
    tab = _new_tab(qapp)
    tab._load_file(_make_review_file())
    assert isinstance(tab._source_labels[0], QLabel)
    assert tab._source_labels[0].wordWrap() is True


# ── 편집 → entry 반영 ────────────────────────────────────────
def test_editing_translation_marks_entry_modified(qapp):
    tab = _new_tab(qapp)
    rf = _make_review_file()
    tab._load_file(rf)
    tab._editors[0].setPlainText("불덩어리")
    assert rf.entries[0].modified is True
    assert rf.entries[0].new_target == "불덩어리"


def test_loading_does_not_mark_modified(qapp):
    tab = _new_tab(qapp)
    rf = _make_review_file()
    tab._load_file(rf)
    assert all(not e.modified for e in rf.entries)


def test_unchanged_value_does_not_mark_modified(qapp):
    tab = _new_tab(qapp)
    rf = _make_review_file()
    tab._load_file(rf)
    tab._editors[1].setPlainText("가속")  # 동일 값
    assert rf.entries[1].modified is False


# ── 필터 ─────────────────────────────────────────────────────
def test_show_modified_only_filters(qapp):
    tab = _new_tab(qapp)
    rf = _make_review_file()
    rf.entries[1].modified = True
    rf.entries[1].new_target = "빠름"
    tab._current_file = rf
    tab._show_modified_only = True
    tab._load_file(rf)
    assert len(tab._editors) == 1
    assert tab._source_labels[0].text() == "Haste"
    assert tab._editors[0].toPlainText() == "빠름"


def test_reload_shows_new_target(qapp):
    tab = _new_tab(qapp)
    rf = _make_review_file()
    tab._load_file(rf)
    tab._editors[0].setPlainText("불덩어리")
    tab._load_file(rf)
    assert tab._editors[0].toPlainText() == "불덩어리"


# ── 파일 드롭다운 (목록 → 콤보) ──────────────────────────────
def test_multiple_files_shown_in_combo(qapp):
    tab = _new_tab(qapp)
    tab._show_review_files([_make_review_file("a.xml"), _make_review_file("b.xml")])
    assert tab._file_combo.count() == 2
    assert not tab._file_combo.isHidden()


def test_single_file_hides_combo(qapp):
    tab = _new_tab(qapp)
    tab._show_review_files([_make_review_file("only.xml")])
    assert tab._file_combo.isHidden()
    # 단일 파일은 자동 로드되어 카드가 보여야 한다
    assert len(tab._editors) == 3


# ── 도움말 접기 ──────────────────────────────────────────────
def test_help_panel_toggle(qapp):
    tab = _new_tab(qapp)
    tab._toggle_help(False)
    assert tab._desc_panel.isHidden()
    tab._toggle_help(True)
    assert not tab._desc_panel.isHidden()
