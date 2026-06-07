import queue
import shutil
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from typing import List, Optional

import customtkinter as ctk
from tkinter import messagebox, ttk

from bg3core.config import UserConfig
from bg3core.divine import divine_extract, divine_repack, ensure_loca
from bg3core.reviewer import Entry, ReviewFile, load_review_files, save_modified_xml
from .widgets.path_picker import PathPicker


class ReviewerTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._cfg: Optional[UserConfig] = None
        self._review_files: List[ReviewFile] = []
        self._current_file: Optional[ReviewFile] = None
        self._current_entries: List[Entry] = []
        self._current_idx: int = 0
        self._show_modified_only = False
        self._temp_dir: Optional[Path] = None
        self._pak_path: Optional[Path] = None
        self._event_queue: queue.Queue = queue.Queue()

        font = ctk.CTkFont(family="Malgun Gothic", size=12)
        font_b = ctk.CTkFont(family="Malgun Gothic", size=12, weight="bold")
        font_s = ctk.CTkFont(family="Malgun Gothic", size=11)

        # ── 상단: PAK 선택 ──
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(16, 4))
        self._pak_picker = PathPicker(
            top, label="검수할 PAK",
            mode="file",
            filetypes=[("PAK 파일", "*.pak"), ("All files", "*.*")],
        )
        self._pak_picker.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(top, text="열기", font=font_b, width=80, command=self._open_pak).pack(side="left")

        # ── 중단: 파일 트리 + 편집 영역 ──
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=16, pady=4)

        # 파일 트리 (좌측)
        tree_frame = ctk.CTkFrame(main, width=180)
        tree_frame.pack(side="left", fill="y", padx=(0, 8))
        tree_frame.pack_propagate(False)
        ctk.CTkLabel(tree_frame, text="파일 목록", font=font_b).pack(pady=(8, 4))
        scale = ctk.ScalingTracker.get_widget_scaling(self)
        self._file_tree = tk.Listbox(
            tree_frame, font=("Malgun Gothic", int(10 * scale)), selectmode="single",
            bg="#2b2b2b", fg="white", selectbackground="#1f6aa5",
        )
        self._file_tree.pack(fill="both", expand=True, padx=4, pady=(0, 8))
        self._file_tree.bind("<<ListboxSelect>>", self._on_file_select)

        # 편집 영역 (우측)
        edit_frame = ctk.CTkFrame(main, fg_color="transparent")
        edit_frame.pack(side="left", fill="both", expand=True)

        self._nav_label = ctk.CTkLabel(edit_frame, text="항목 0 / 0", font=font_s)
        self._nav_label.pack(anchor="e", pady=(4, 0))

        ctk.CTkLabel(edit_frame, text="영어 원문", font=font_b).pack(anchor="w")
        self._en_box = ctk.CTkTextbox(
            edit_frame, height=120, font=font_s, state="disabled", wrap="word"
        )
        self._en_box.pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(edit_frame, text="한국어 번역", font=font_b).pack(anchor="w")
        self._kr_box = ctk.CTkTextbox(edit_frame, height=120, font=font_s, wrap="word")
        self._kr_box.pack(fill="x", pady=(2, 8))

        # 네비게이션 버튼
        nav = ctk.CTkFrame(edit_frame, fg_color="transparent")
        nav.pack(fill="x", pady=4)
        ctk.CTkButton(nav, text="◀ 이전", font=font, width=80, command=self._prev).pack(side="left", padx=(0, 4))
        ctk.CTkButton(nav, text="다음 ▶", font=font, width=80, command=self._next).pack(side="left", padx=(0, 8))
        ctk.CTkButton(nav, text="저장 (Ctrl+S)", font=font_b, command=self._save_all).pack(side="left", padx=(0, 4))
        self._modified_only_btn = ctk.CTkButton(
            nav, text="수정 항목만 보기", font=font, command=self._toggle_modified_only
        )
        self._modified_only_btn.pack(side="left")

        # 단축키 (CTk는 bind_all 미지원 — 편집 박스에 직접 바인딩)
        self._kr_box.bind("<Control-s>", lambda e: self._save_all())

    def set_config(self, cfg: UserConfig) -> None:
        self._cfg = cfg

    def _open_pak(self) -> None:
        pak_str = self._pak_picker.get()
        if not pak_str:
            messagebox.showwarning("입력 필요", "PAK 파일을 선택해 주세요.")
            return
        if not self._cfg or not self._cfg.divine_exe_path:
            messagebox.showerror("설정 오류", "설정 탭에서 Divine.exe 경로를 먼저 저장하세요.")
            return

        self._pak_path = Path(pak_str)
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)
        self._temp_dir = Path(tempfile.mkdtemp(prefix="bg3_review_"))

        def _unpack():
            ok = divine_extract(self._cfg.divine_exe_path, self._pak_path, self._temp_dir)
            self._event_queue.put(("unpack_done", ok))

        threading.Thread(target=_unpack, daemon=True).start()
        self._poll_open()

    def _poll_open(self) -> None:
        try:
            kind, data = self._event_queue.get_nowait()
            if kind == "unpack_done":
                if not data:
                    messagebox.showerror("오류", "PAK 언팩에 실패했습니다.")
                    return
                review_files = load_review_files(self._temp_dir)
                if not review_files:
                    messagebox.showwarning("항목 없음", "검수할 번역 항목을 찾지 못했습니다.\n(Korean 폴더가 있는지 확인하세요)")
                    return
                self._review_files = review_files
                self._populate_tree()
                return
        except queue.Empty:
            pass
        self.after(200, self._poll_open)

    def _populate_tree(self) -> None:
        self._file_tree.delete(0, "end")
        for rf in self._review_files:
            self._file_tree.insert("end", rf.filename)
        if self._review_files:
            self._file_tree.selection_set(0)
            self._load_file(self._review_files[0])

    def _on_file_select(self, event=None) -> None:
        sel = self._file_tree.curselection()
        if sel and self._review_files:
            self._load_file(self._review_files[sel[0]])

    def _load_file(self, rf: ReviewFile) -> None:
        self._current_file = rf
        self._current_entries = [
            e for e in rf.entries
            if not self._show_modified_only or e.modified
        ]
        self._current_idx = 0
        self._show_entry()

    def _show_entry(self) -> None:
        if not self._current_entries:
            self._nav_label.configure(text="항목 없음")
            self._en_box.configure(state="normal")
            self._en_box.delete("1.0", "end")
            self._en_box.configure(state="disabled")
            self._kr_box.delete("1.0", "end")
            return
        entry = self._current_entries[self._current_idx]
        total = len(self._current_entries)
        self._nav_label.configure(text=f"항목 {self._current_idx + 1} / {total}")
        self._en_box.configure(state="normal")
        self._en_box.delete("1.0", "end")
        self._en_box.insert("1.0", entry.english)
        self._en_box.configure(state="disabled")
        self._kr_box.delete("1.0", "end")
        self._kr_box.insert("1.0", entry.display_korean)

    def _commit_current(self) -> None:
        if not self._current_entries:
            return
        entry = self._current_entries[self._current_idx]
        new_text = self._kr_box.get("1.0", "end-1c")
        if new_text != entry.korean:
            entry.modified = True
            entry.new_korean = new_text

    def _next(self) -> None:
        self._commit_current()
        if self._current_entries and self._current_idx < len(self._current_entries) - 1:
            self._current_idx += 1
        self._show_entry()

    def _prev(self) -> None:
        self._commit_current()
        if self._current_idx > 0:
            self._current_idx -= 1
        self._show_entry()

    def _save_all(self) -> None:
        self._commit_current()
        if not self._review_files or not self._pak_path or not self._temp_dir:
            return
        modified = [rf for rf in self._review_files if any(e.modified for e in rf.entries)]
        if not modified:
            messagebox.showinfo("저장", "수정된 항목이 없습니다.")
            return
        for rf in modified:
            save_modified_xml(rf)

        # BG3는 .loca 바이너리를 읽으므로, 편집된 xml에서 .loca를 강제 재생성한다.
        # force=True: 검수는 기존 번역을 수정하므로 기존 .loca도 덮어써야 한다.
        ensure_loca(self._cfg.divine_exe_path, self._temp_dir, force=True)

        stem = self._pak_path.stem
        out_pak = self._pak_path.parent / f"{stem}_Reviewed.pak"
        if divine_repack(self._cfg.divine_exe_path, self._temp_dir, out_pak):
            messagebox.showinfo("저장 완료", f"검수 PAK 저장 완료:\n{out_pak.name}")
        else:
            messagebox.showerror("오류", "PAK 리팩에 실패했습니다.")

    def _toggle_modified_only(self) -> None:
        self._show_modified_only = not self._show_modified_only
        self._modified_only_btn.configure(
            text="전체 보기" if self._show_modified_only else "수정 항목만 보기"
        )
        if self._current_file:
            self._load_file(self._current_file)
