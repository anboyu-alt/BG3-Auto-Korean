import customtkinter as ctk
from tkinter import filedialog
from typing import Callable, Optional


class PathPicker(ctk.CTkFrame):
    """경로 입력 + 찾아보기 버튼 조합 위젯."""

    def __init__(
        self,
        master,
        label: str,
        mode: str = "file",          # "file" | "dir"
        filetypes: Optional[list] = None,
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._mode = mode
        self._filetypes = filetypes or [("All files", "*.*")]
        self._on_change = on_change
        font = ctk.CTkFont(family="Malgun Gothic", size=12)

        ctk.CTkLabel(self, text=label, font=font, width=120, anchor="w").grid(
            row=0, column=0, padx=(0, 6), sticky="w"
        )
        self._entry = ctk.CTkEntry(self, font=font, width=320)
        self._entry.grid(row=0, column=1, padx=(0, 6), sticky="ew")
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            self, text="찾아보기", font=font, width=80, command=self._browse
        ).grid(row=0, column=2)

    def _browse(self) -> None:
        if self._mode == "dir":
            path = filedialog.askdirectory()
        else:
            path = filedialog.askopenfilename(filetypes=self._filetypes)
        if path:
            self.set(path)

    def get(self) -> str:
        return self._entry.get().strip()

    def set(self, value: str) -> None:
        self._entry.delete(0, "end")
        self._entry.insert(0, value)
        if self._on_change:
            self._on_change(value)
