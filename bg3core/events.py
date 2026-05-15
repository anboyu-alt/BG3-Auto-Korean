from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Optional


@dataclass
class ProgressEvent:
    stage: Literal["unpack", "translate", "repack", "done", "error"]
    current: int
    total: int
    message: str
    pak_name: Optional[str] = None


@dataclass
class LogEvent:
    level: Literal["info", "warn", "error", "debug"]
    text: str
    timestamp: datetime = field(default_factory=datetime.now)
