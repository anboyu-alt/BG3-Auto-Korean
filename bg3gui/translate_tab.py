import queue
import threading
from typing import Optional

import customtkinter as ctk
from tkinter import messagebox

from bg3core.config import UserConfig
from bg3core.events import LogEvent, ProgressEvent
from .widgets.log_view import LogView
from .widgets.path_picker import PathPicker
from .widgets.progress_panel import ProgressPanel
from .workers import TranslationWorker


class TranslateTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._cfg: Optional[UserConfig] = None
        self._worker: Optional[TranslationWorker] = None
        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._event_queue: queue.Queue = queue.Queue()
        self._running = False

        font = ctk.CTkFont(family="Malgun Gothic", size=12)
        font_b = ctk.CTkFont(family="Malgun Gothic", size=12, weight="bold")

        # ── 입력 ──
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=16, pady=(16, 4))

        self._pak_picker = PathPicker(
            input_frame,
            label="PAK 파일/폴더",
            mode="file",
            filetypes=[("PAK 파일", "*.pak"), ("All files", "*.*")],
        )
        self._pak_picker.pack(fill="x", pady=2)

        # ── 진행률 ──
        self._progress = ProgressPanel(self)
        self._progress.pack(fill="x", padx=16, pady=8)

        # ── 버튼 ──
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=4)

        self._start_btn = ctk.CTkButton(
            btn_frame, text="▶ 시작", font=font_b, command=self._start, state="disabled"
        )
        self._start_btn.pack(side="left", padx=(0, 8))

        self._pause_btn = ctk.CTkButton(
            btn_frame, text="⏸ 일시정지", font=font, command=self._toggle_pause, state="disabled"
        )
        self._pause_btn.pack(side="left", padx=(0, 8))

        self._stop_btn = ctk.CTkButton(
            btn_frame, text="⏹ 중단", font=font, command=self._stop,
            state="disabled", fg_color="#dc2626", hover_color="#b91c1c",
        )
        self._stop_btn.pack(side="left")

        self._status_label = ctk.CTkLabel(
            btn_frame, text="설정 탭에서 API 키와 Divine.exe를 먼저 저장하세요.",
            font=ctk.CTkFont(family="Malgun Gothic", size=11),
            text_color="gray",
        )
        self._status_label.pack(side="left", padx=16)

        # ── 로그 ──
        ctk.CTkLabel(self, text="로그", font=font_b).pack(anchor="w", padx=16, pady=(8, 2))
        self._log = LogView(self, height=320)
        self._log.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def set_config(self, cfg: UserConfig) -> None:
        self._cfg = cfg
        ready = bool(cfg.api_key and cfg.divine_exe_path)
        self._start_btn.configure(state="normal" if ready else "disabled")
        hint = "" if ready else "설정 탭에서 API 키와 Divine.exe를 먼저 저장하세요."
        self._status_label.configure(text=hint)

    def _start(self) -> None:
        if not self._cfg:
            return
        target = self._pak_picker.get()
        if not target:
            messagebox.showwarning("입력 필요", "PAK 파일 또는 폴더를 선택해 주세요.")
            return

        self._log.clear()
        self._progress.reset()
        self._cancel_event.clear()
        self._pause_event.clear()
        self._running = True
        self._set_btn_state(running=True)

        self._worker = TranslationWorker(
            cfg=self._cfg,
            target_path=target,
            event_queue=self._event_queue,
            cancel_event=self._cancel_event,
            pause_event=self._pause_event,
        )
        self._worker.start()
        self._poll()

    def _poll(self) -> None:
        try:
            while True:
                kind, data = self._event_queue.get_nowait()
                if kind == "log" and isinstance(data, LogEvent):
                    self._log.append(data.text, data.level)
                elif kind == "progress" and isinstance(data, ProgressEvent):
                    self._progress.update_stage(
                        data.stage, data.current, data.total, data.message
                    )
                elif kind == "done":
                    self._on_finished("✅ 번역 완료!")
                    return
                elif kind == "cancelled":
                    self._on_finished("⏹ 중단됨")
                    return
                elif kind == "error":
                    self._log.append(f"❌ 오류:\n{data}", "error")
                    self._on_finished("❌ 오류 발생")
                    return
        except queue.Empty:
            pass

        if self._running:
            self.after(100, self._poll)

    def _on_finished(self, msg: str) -> None:
        self._running = False
        self._set_btn_state(running=False)
        self._log.append(f"\n{msg}")
        self._status_label.configure(text=msg)

    def _toggle_pause(self) -> None:
        if self._pause_event.is_set():
            self._pause_event.clear()
            self._pause_btn.configure(text="⏸ 일시정지")
            self._log.append("▶ 재개")
        else:
            self._pause_event.set()
            self._pause_btn.configure(text="▶ 재개")
            self._log.append("⏸ 일시정지 중...")

    def _stop(self) -> None:
        if messagebox.askyesno("중단 확인", "번역을 중단하시겠습니까?"):
            self._cancel_event.set()
            self._pause_event.clear()
            self._log.append("⏹ 중단 요청됨...")

    def _set_btn_state(self, running: bool) -> None:
        self._start_btn.configure(state="disabled" if running else "normal")
        self._pause_btn.configure(state="normal" if running else "disabled")
        self._stop_btn.configure(state="normal" if running else "disabled")
        self._pak_picker._entry.configure(state="disabled" if running else "normal")
