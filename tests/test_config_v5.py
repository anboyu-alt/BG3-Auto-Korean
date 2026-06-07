from bg3core.config import UserConfig


def test_target_language_default():
    assert UserConfig().target_language == "Korean"


def test_target_language_serialized():
    cfg = UserConfig(target_language="French")
    assert cfg.__dict__["target_language"] == "French"
