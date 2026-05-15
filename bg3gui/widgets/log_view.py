from collections import deque
from typing import Optional

import customtkinter as ctk


_MAX_LINES = 5000

_TAG_COLORS = {
    "info":  ("#000000", "#ffffff"),
    "warn":  ("#b45309", "#fef3c7"),
    "error": ("#dc2626", "#fee2e2"),
    "debug": ("#6b7280", "#f3f4f6"),
}


class LogView(ctk.CTkTextbox):
    def __init__(self, master, **kwargs):
        kwargs.setdefault("state", "disabled")
        kwargs.setdefault("wrap", "word")
        kwargs.setdefault("font", ctk.CTkFont(family="Malgun Gothic", size=11))
        super().__init__(master, **kwargs)
        self._line_buf: deque = deque(maxlen=_MAX_LINES)
        self._auto_scroll = True

    def append(self, text: str, level: str = "info") -> None:
        self._line_buf.append((text, level))
        self.configure(state="normal")
        self.insert("end", text + "\n")
        # ring buffer: 라인 수 초과 시 맨 위 줄 제거
        lines = int(self.index("end-1c").split(".")[0])
        if lines > _MAX_LINES:
            self.delete("1.0", f"{lines - _MAX_LINES}.0")
        if self._auto_scroll:
            self.see("end")
        self.configure(state="disabled")

    def clear(self) -> None:
        self._line_buf.clear()
        self.configure(state="normal")
        self.delete("1.0", "end")
        self.configure(state="disabled")
