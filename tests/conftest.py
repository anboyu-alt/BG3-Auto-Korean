import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FIXTURE_SRC = ROOT / "tests" / "fixtures" / "tooltip_manager"


@pytest.fixture
def tooltip_manager_root(tmp_path):
    """Tooltip Manager fixture를 tmp_path로 복사한 뒤 그 경로 반환."""
    dest = tmp_path / "tooltip_manager"
    shutil.copytree(FIXTURE_SRC, dest)
    return dest


@pytest.fixture
def passthrough_translate():
    """입력 텍스트를 그대로 한글 prefix와 함께 반환하는 mock 번역기."""
    def fn(texts, label):
        return {t: f"[KO]{t}" for t in texts}
    return fn


@pytest.fixture
def identity_translate():
    """입력을 그대로 반환하는 mock — 치환 횟수만 검증할 때."""
    def fn(texts, label):
        return {t: t for t in texts}
    return fn
