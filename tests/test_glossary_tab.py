"""② 용어집 인라인 편집 — GlossaryTab "내 용어집" 표 편집 동작 테스트 (offscreen Qt).

기본 용어집은 읽기전용 유지, 내 용어집만 Excel식 편집 QTableWidget로 바꾼다.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _new_tab(qapp):
    from bg3gui.glossary_tab import GlossaryTab
    tab = GlossaryTab()
    # 테스트 격리: 디스크 custom_glossary와 무관하게 데이터 주입
    tab._set_custom_data({})
    return tab


def test_custom_table_has_trailing_empty_row(qapp):
    tab = _new_tab(qapp)
    tab._set_custom_data({"Fireball": "화염구"})
    # 데이터 1행 + 신규 입력용 빈 행 1개
    assert tab._custom_table.rowCount() == 2
    assert tab._custom_table.item(0, 0).text() == "Fireball"
    assert tab._custom_table.item(0, 1).text() == "화염구"
    assert tab._custom_table.item(1, 0).text() == ""


def test_empty_data_shows_single_empty_row(qapp):
    tab = _new_tab(qapp)
    assert tab._custom_table.rowCount() == 1
    assert tab._custom_table.item(0, 0).text() == ""


def test_typing_in_trailing_row_adds_entry(qapp):
    tab = _new_tab(qapp)
    tab._custom_table.item(0, 0).setText("Haste")
    tab._custom_table.item(0, 1).setText("가속")
    assert tab._custom_data.get("Haste") == "가속"


def test_typing_in_trailing_row_appends_new_empty_row(qapp):
    tab = _new_tab(qapp)
    tab._custom_table.item(0, 0).setText("Haste")
    tab._custom_table.item(0, 1).setText("가속")
    # 빈 행이 다시 맨 아래에 생겨야 한다(연속 입력)
    assert tab._custom_table.rowCount() == 2
    assert tab._custom_table.item(1, 0).text() == ""


def test_editing_translation_updates_data(qapp):
    tab = _new_tab(qapp)
    tab._set_custom_data({"Fireball": "화염구"})
    tab._custom_table.item(0, 1).setText("불덩어리")
    assert tab._custom_data["Fireball"] == "불덩어리"


def test_clearing_english_removes_entry(qapp):
    tab = _new_tab(qapp)
    tab._set_custom_data({"Fireball": "화염구"})
    tab._custom_table.item(0, 0).setText("")
    assert "Fireball" not in tab._custom_data


def test_save_writes_custom_glossary(qapp, monkeypatch):
    saved = {}
    monkeypatch.setattr(
        "bg3gui.glossary_tab.save_custom_glossary",
        lambda d: saved.update(d),
    )
    tab = _new_tab(qapp)
    tab._set_custom_data({"Fireball": "화염구"})
    tab._save()
    assert saved == {"Fireball": "화염구"}


def test_delete_selected_row_removes_entry(qapp):
    tab = _new_tab(qapp)
    tab._set_custom_data({"Fireball": "화염구", "Haste": "가속"})
    tab._custom_table.setCurrentCell(0, 0)
    tab._delete_selected_row()
    assert "Fireball" not in tab._custom_data
    assert "Haste" in tab._custom_data
