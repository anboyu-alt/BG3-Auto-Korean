"""첫 실행 위저드 — FirstRunWizard 동작 테스트 (offscreen Qt).

설정 파일이 없을 때 API키·BG3 경로를 한 번에 안내·입력받는다.
자동 감지값(전달된 config)으로 prefill하고, 입력값으로 새 config를 만든다.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def test_wizard_prefills_from_config(qapp):
    from bg3gui.first_run_wizard import FirstRunWizard
    from bg3core.config import UserConfig

    cfg = UserConfig(bg3_install_path="D:/BG3")
    w = FirstRunWizard(cfg)
    assert w._bg3_picker.get() == "D:/BG3"


def test_result_config_uses_input(qapp):
    from bg3gui.first_run_wizard import FirstRunWizard
    from bg3core.config import UserConfig

    w = FirstRunWizard(UserConfig())
    w._api_edit.setText("KEY123")
    w._bg3_picker.set("X/BG3")
    out = w.result_config()
    assert out.api_key == "KEY123"
    assert out.bg3_install_path == "X/BG3"


def test_result_config_preserves_other_fields(qapp):
    # 위저드는 API/BG3만 다룬다. 자동 설정된 언어 등 나머지는 보존.
    from bg3gui.first_run_wizard import FirstRunWizard
    from bg3core.config import UserConfig

    cfg = UserConfig(target_language="French", app_language="fr")
    w = FirstRunWizard(cfg)
    w._api_edit.setText("K")
    out = w.result_config()
    assert out.target_language == "French"
    assert out.app_language == "fr"


def test_result_config_strips_whitespace(qapp):
    from bg3gui.first_run_wizard import FirstRunWizard
    from bg3core.config import UserConfig

    w = FirstRunWizard(UserConfig())
    w._api_edit.setText("  KEY  ")
    out = w.result_config()
    assert out.api_key == "KEY"
