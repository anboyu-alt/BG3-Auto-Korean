"""제보 2·3: GUI 로그에 LogEvent repr이 아닌 본문이 떠야 하고, 언팩 실패 이유가 로그에 남아야 한다."""
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from bg3core.events import LogEvent
from bg3core.logger import CallbackLogger


def test_worker_log_line_uses_event_text():
    from bg3gui.workers import log_event_text
    e = LogEvent(level="info", text="[Summary]")
    assert log_event_text(e) == "[Summary]"


def _capture_logger():
    lines = []
    return CallbackLogger(on_log=lambda e: lines.append((e.level, e.text))), lines


def test_extract_pak_failure_reason_reaches_logger(tmp_path):
    from bg3core.packio import extract_pak
    bogus = tmp_path / "bogus.pak"
    bogus.write_bytes(b"not a pak at all, definitely longer than forty bytes......")
    logger, lines = _capture_logger()
    assert extract_pak(bogus, tmp_path / "out", logger=logger) is False
    assert any(lvl == "error" and "bogus.pak" in txt and "signature" in txt for lvl, txt in lines)


def test_process_pak_file_logs_unpack_failure(tmp_path):
    from bg3core.pipeline import process_pak_file
    bogus = tmp_path / "Mod.pak"
    bogus.write_bytes(b"\x00" * 64)
    logger, lines = _capture_logger()
    ok = process_pak_file(
        bogus, "", str(tmp_path / "log.txt"), str(tmp_path / "cache.json"),
        work_dir=tmp_path, logger=logger,
    )
    assert ok is False
    assert any(lvl == "error" and "Mod.pak" in txt for lvl, txt in lines)


def test_run_batch_single_pak_logs_failed_summary(tmp_path, monkeypatch):
    import bg3core.translate as t
    from bg3core.pipeline import run_batch
    # run_batch가 모듈 전역 번역 캐시를 실제 dict로 바꾸므로 다른 테스트로 새지 않게 격리
    monkeypatch.setattr(t, "_translation_cache", None)
    monkeypatch.setattr(t, "_cache_dirty", False)
    bogus = tmp_path / "Mod.pak"
    bogus.write_bytes(b"\x00" * 64)
    logger, lines = _capture_logger()
    run_batch("", str(bogus), str(tmp_path / "log.txt"), str(tmp_path / "cache.json"),
              work_dir=tmp_path, logger=logger)
    assert any(lvl == "error" and txt.strip().startswith("❌ Failed: Mod.pak") for lvl, txt in lines)


def test_worker_has_no_shadowed_finished_signal():
    """커스텀 완료 시그널이 QThread.finished를 가리지 않아야 완료 메시지가 한 번만 찍힌다."""
    from bg3gui.workers import TranslationWorker
    assert "finished" not in TranslationWorker.__dict__
    assert "done" in TranslationWorker.__dict__
