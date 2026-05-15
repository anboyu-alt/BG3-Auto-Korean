import sys
from datetime import datetime
from typing import Callable, Optional

from .events import LogEvent, ProgressEvent


class CallbackLogger:
    def __init__(
        self,
        on_log: Optional[Callable[[LogEvent], None]] = None,
        on_progress: Optional[Callable[[ProgressEvent], None]] = None,
    ):
        self._on_log = on_log
        self._on_progress = on_progress

    def _emit(self, level: str, text: str) -> None:
        event = LogEvent(level=level, text=text, timestamp=datetime.now())
        if self._on_log:
            self._on_log(event)
        else:
            print(text, file=sys.stdout)

    def info(self, text: str) -> None:
        self._emit("info", text)

    def warn(self, text: str) -> None:
        self._emit("warn", text)

    def error(self, text: str) -> None:
        self._emit("error", text)

    def debug(self, text: str) -> None:
        self._emit("debug", text)

    def progress(
        self,
        stage: str,
        current: int,
        total: int,
        message: str,
        pak_name: Optional[str] = None,
    ) -> None:
        event = ProgressEvent(
            stage=stage,
            current=current,
            total=total,
            message=message,
            pak_name=pak_name,
        )
        if self._on_progress:
            self._on_progress(event)


# stdout 출력 전용 기본 로거 (CLI 호환)
_stdout_logger = CallbackLogger()


def get_stdout_logger() -> CallbackLogger:
    return _stdout_logger
