# bg3gui/workers.py
from __future__ import annotations
import os
import traceback
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from bg3core.config import UserConfig, get_default_cache_path, get_default_log_dir
from bg3core.pipeline import run_batch
from bg3core.logger import CallbackLogger


class TranslationWorker(QThread):
    log_line = Signal(str)
    progress = Signal(int, int, str)
    finished = Signal()
    error = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        cfg: UserConfig,
        target_path: str,
        cancel_event: threading.Event,
        pause_event: threading.Event,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.cfg = cfg
        self.target_path = target_path
        self.cancel_event = cancel_event
        self.pause_event = pause_event

    def run(self) -> None:
        cfg = self.cfg
        cache_file = cfg.cache_path or get_default_cache_path()
        log_dir = cfg.log_dir or get_default_log_dir()
        os.makedirs(log_dir, exist_ok=True)
        log_file = str(Path(log_dir) / "translation_errors.txt")
        work_dir = Path(cache_file).parent

        logger = CallbackLogger(
            on_log=lambda e: self.log_line.emit(
                e.message if hasattr(e, "message") else str(e)
            ),
            on_progress=lambda e: None,
        )

        def on_progress(stage: str, current: int, total: int, message: str, pak_name=None):
            self.progress.emit(current, total, message)

        try:
            run_batch(
                api_key=cfg.api_key,
                divine_path=cfg.divine_exe_path,
                target_pak=self.target_path,
                log_file=log_file,
                cache_file=cache_file,
                work_dir=work_dir,
                skip_if_target_exists=cfg.skip_if_korean_exists,
                target_language=getattr(cfg, "target_language", "Korean"),
                mcm_enabled=cfg.mcm_enabled,
                cancel_event=self.cancel_event,
                pause_event=self.pause_event,
                on_progress=on_progress,
                logger=logger,
            )
            self.finished.emit()
        except InterruptedError:
            self.cancelled.emit()
        except Exception:
            self.error.emit(traceback.format_exc())
