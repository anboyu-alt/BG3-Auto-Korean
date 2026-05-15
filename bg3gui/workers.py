import queue
import threading
import traceback
from pathlib import Path
from typing import Optional

from bg3core.config import UserConfig, get_default_cache_path, get_default_log_dir
from bg3core.events import LogEvent, ProgressEvent
from bg3core.logger import CallbackLogger
from bg3core.pipeline import run_batch


class TranslationWorker(threading.Thread):
    def __init__(
        self,
        cfg: UserConfig,
        target_path: str,
        event_queue: queue.Queue,
        cancel_event: threading.Event,
        pause_event: threading.Event,
    ):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.target_path = target_path
        self.event_queue = event_queue
        self.cancel_event = cancel_event
        self.pause_event = pause_event

    def run(self) -> None:
        cfg = self.cfg
        cache_file = cfg.cache_path or get_default_cache_path()
        log_dir = cfg.log_dir or get_default_log_dir()

        import os
        os.makedirs(log_dir, exist_ok=True)
        log_file = str(Path(log_dir) / "translation_errors.txt")

        work_dir = Path(cache_file).parent

        logger = CallbackLogger(
            on_log=lambda e: self.event_queue.put(("log", e)),
            on_progress=lambda e: self.event_queue.put(("progress", e)),
        )

        def on_progress(stage, current, total, message, pak_name=None):
            self.event_queue.put(("progress", ProgressEvent(
                stage=stage,
                current=current,
                total=total,
                message=message,
                pak_name=pak_name,
            )))

        try:
            run_batch(
                api_key=cfg.api_key,
                divine_path=cfg.divine_exe_path,
                target_pak=self.target_path,
                log_file=log_file,
                cache_file=cache_file,
                work_dir=work_dir,
                skip_if_korean_exists=cfg.skip_if_korean_exists,
                cancel_event=self.cancel_event,
                pause_event=self.pause_event,
                on_progress=on_progress,
                logger=logger,
            )
            self.event_queue.put(("done", None))
        except InterruptedError:
            self.event_queue.put(("cancelled", None))
        except Exception:
            self.event_queue.put(("error", traceback.format_exc()))
