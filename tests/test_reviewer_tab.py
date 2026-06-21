"""① 검수 탭 테이블화 — ReviewerTab 위젯 동작 테스트 (offscreen Qt).

코어(bg3core.reviewer)는 그대로 두고 UI만 QTableWidget로 바꾼다. 테이블 로드/
편집 반영/읽기전용/필터 동작을 검증한다.
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


def _make_review_file():
    from bg3core.reviewer import Entry, ReviewFile
    entries = [
        Entry(contentuid="h1", english="Fireball", target_text="화염구"),
        Entry(contentuid="h2", english="Haste", target_text="가속"),
        Entry(contentuid="h3", english="Bless", target_text="축복"),
    ]
    return ReviewFile("test.xml", entries, Path("x.xml"), "<xml/>")


def _new_tab(qapp):
    from bg3gui.reviewer_tab import ReviewerTab
    return ReviewerTab()


def test_table_loads_all_entries(qapp):
    tab = _new_tab(qapp)
    rf = _make_review_file()
    tab._review_files = [rf]
    tab._load_file(rf)
    assert tab._table.rowCount() == 3
    assert tab._table.item(0, 0).text() == "Fireball"
    assert tab._table.item(0, 1).text() == "화염구"
    assert tab._table.item(2, 0).text() == "Bless"


def test_english_column_is_readonly(qapp):
    from PySide6.QtCore import Qt
    tab = _new_tab(qapp)
    rf = _make_review_file()
    tab._load_file(rf)
    en_item = tab._table.item(0, 0)
    tr_item = tab._table.item(0, 1)
    assert not (en_item.flags() & Qt.ItemFlag.ItemIsEditable)
    assert tr_item.flags() & Qt.ItemFlag.ItemIsEditable


def test_editing_translation_marks_entry_modified(qapp):
    tab = _new_tab(qapp)
    rf = _make_review_file()
    tab._load_file(rf)
    tab._table.item(0, 1).setText("불덩어리")  # cellChanged 발생
    assert rf.entries[0].modified is True
    assert rf.entries[0].new_target == "불덩어리"


def test_loading_file_does_not_mark_modified(qapp):
    # 프로그램적 채우기(setItem)는 modified를 만들면 안 된다(시그널 차단).
    tab = _new_tab(qapp)
    rf = _make_review_file()
    tab._load_file(rf)
    assert all(not e.modified for e in rf.entries)


def test_unchanged_value_does_not_mark_modified(qapp):
    tab = _new_tab(qapp)
    rf = _make_review_file()
    tab._load_file(rf)
    tab._table.item(1, 1).setText("가속")  # 동일 값
    assert rf.entries[1].modified is False


def test_show_modified_only_filters_rows(qapp):
    tab = _new_tab(qapp)
    rf = _make_review_file()
    rf.entries[1].modified = True
    rf.entries[1].new_target = "빠름"
    tab._review_files = [rf]
    tab._current_file = rf
    tab._show_modified_only = True
    tab._load_file(rf)
    assert tab._table.rowCount() == 1
    assert tab._table.item(0, 0).text() == "Haste"
    assert tab._table.item(0, 1).text() == "빠름"


def test_modified_filter_shows_new_target(qapp):
    # display_target: modified면 new_target을 보여준다.
    tab = _new_tab(qapp)
    rf = _make_review_file()
    tab._load_file(rf)
    tab._table.item(0, 1).setText("불덩어리")
    # 다시 로드하면 편집값이 보여야 한다.
    tab._load_file(rf)
    assert tab._table.item(0, 1).text() == "불덩어리"


def test_table_columns_both_stretch(qapp):
    # 원문·번역 칸이 1:1로 균등하게 늘어나야 한다(번역 칸만 좁던 문제).
    from PySide6.QtWidgets import QHeaderView
    tab = _new_tab(qapp)
    tab._load_file(_make_review_file())
    hdr = tab._table.horizontalHeader()
    assert hdr.sectionResizeMode(0) == QHeaderView.ResizeMode.Stretch
    assert hdr.sectionResizeMode(1) == QHeaderView.ResizeMode.Stretch


def test_help_panel_toggle(qapp):
    # 도움말 패널을 접으면 표가 넓어진다.
    tab = _new_tab(qapp)
    tab._toggle_help(False)
    assert tab._desc_panel.isHidden()
    tab._toggle_help(True)
    assert not tab._desc_panel.isHidden()
