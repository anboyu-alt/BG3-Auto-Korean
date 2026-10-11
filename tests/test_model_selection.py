import json

from bg3core import config as config_mod
from bg3core.constants import MODELS_TO_TRY
from bg3core.translate import _thinking_config


def test_gemini3_uses_thinking_level():
    for m in ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite",
              "gemini-3.8-flash", "gemini-3.1-pro-preview"):
        assert _thinking_config(m) == {"thinkingLevel": "low"}


def test_legacy_gemini_keeps_zero_budget():
    assert _thinking_config("gemini-2.5-flash") == {"thinkingBudget": 0}


def _load_with(tmp_path, monkeypatch, prefs):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"model_preference": prefs}), encoding="utf-8")
    monkeypatch.setattr(config_mod, "get_config_path", lambda: path)
    return config_mod.load_config()


def test_retired_saved_model_falls_back_to_default(tmp_path, monkeypatch):
    cfg = _load_with(tmp_path, monkeypatch, ["gemini-2.5-pro"])
    assert cfg.model_preference == list(MODELS_TO_TRY)


def test_current_saved_model_is_kept(tmp_path, monkeypatch):
    cfg = _load_with(tmp_path, monkeypatch, ["gemini-3.8-flash", "gemini-2.5-flash-lite"])
    assert cfg.model_preference == ["gemini-3.8-flash"]
