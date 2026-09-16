# bg3gui/workers.py
from __future__ import annotations
import os
import traceback
import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from bg3core.config import UserConfig, get_default_cache_path, get_default_log_dir
from bg3core.pipeline import run_batch
from bg3core.translate import set_active_models
from bg3core.logger import CallbackLogger
from bg3core.events import LogEvent


def log_event_text(event: LogEvent) -> str:
    """로그 창에 표시할 본문. LogEvent의 필드는 `text`다(예전 코드가 `message`를
    찾다가 실패해 dataclass repr 전체가 로그에 찍히던 버그의 수정)."""
    return event.text


class TranslationWorker(QThread):
    log_line = Signal(str)
    progress = Signal(int, int, str)
    # QThread 내장 finished와 이름이 겹치면 스레드 종료 때마다 슬롯이 한 번 더 불려
    # 오류·중단 뒤에도 '번역 완료!'가 찍힌다. 별도 이름을 쓴다.
    done = Signal()
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
            on_log=lambda e: self.log_line.emit(log_event_text(e)),
            on_progress=lambda e: None,
        )

        def on_progress(stage: str, current: int, total: int, message: str, pak_name=None):
            self.progress.emit(current, total, message)

        # 사용자가 고른 모델을 엔진에 적용(1순위 → 폴백 순). 미설정 시 기본값 사용.
        set_active_models(getattr(cfg, "model_preference", None))

        try:
            run_batch(
                api_key=cfg.api_key,
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
                bg3_install_path=getattr(cfg, "bg3_install_path", ""),
                use_official_glossary=getattr(cfg, "use_official_glossary", False),
            )
            self.done.emit()
        except InterruptedError:
            self.cancelled.emit()
        except Exception:
            self.error.emit(traceback.format_exc())
