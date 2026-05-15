import customtkinter as ctk


class ProgressPanel(ctk.CTkFrame):
    """언팩 → 번역 → 리팩 3단계 진행률 패널."""

    _STAGES = [("unpack", "📤 언팩"), ("translate", "🔄 번역"), ("repack", "📥 리팩")]

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._font = ctk.CTkFont(family="Malgun Gothic", size=11)

        self._stage_labels: dict = {}
        self._stage_bars: dict = {}

        for col, (key, label) in enumerate(self._STAGES):
            ctk.CTkLabel(self, text=label, font=self._font).grid(
                row=0, column=col * 2, padx=(8, 2), pady=4, sticky="w"
            )
            bar = ctk.CTkProgressBar(self, width=120)
            bar.set(0)
            bar.grid(row=0, column=col * 2 + 1, padx=(0, 12), pady=4, sticky="ew")
            self._stage_bars[key] = bar
            self.grid_columnconfigure(col * 2 + 1, weight=1)

        self._status_label = ctk.CTkLabel(
            self, text="대기 중...", font=self._font, anchor="w"
        )
        self._status_label.grid(
            row=1, column=0, columnspan=6, padx=8, pady=(0, 4), sticky="ew"
        )

    def update_stage(self, stage: str, current: int, total: int, message: str) -> None:
        if stage in self._stage_bars:
            val = current / total if total > 0 else 0
            self._stage_bars[stage].set(val)
        if stage == "done":
            for bar in self._stage_bars.values():
                bar.set(1.0)
        self._status_label.configure(text=message[:120])

    def reset(self) -> None:
        for bar in self._stage_bars.values():
            bar.set(0)
        self._status_label.configure(text="대기 중...")
