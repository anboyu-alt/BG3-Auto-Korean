import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional

import customtkinter as ctk

from bg3core.glossary import (
    GLOSSARY,
    load_custom_glossary,
    save_custom_glossary,
)


class GlossaryTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        font = ctk.CTkFont(family="Malgun Gothic", size=12)
        font_b = ctk.CTkFont(family="Malgun Gothic", size=12, weight="bold")
        font_s = ctk.CTkFont(family="Malgun Gothic", size=11)

        # ── 검색창 ──
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.pack(fill="x", padx=16, pady=(12, 6))
        ctk.CTkLabel(search_frame, text="🔍 검색", font=font).pack(side="left", padx=(0, 8))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._apply_filter())
        ctk.CTkEntry(search_frame, textvariable=self._search_var, font=font, width=300,
                     placeholder_text="영어 또는 한국어로 검색...").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(search_frame, text="지우기", font=font_s, width=60,
                      command=lambda: self._search_var.set("")).pack(side="left", padx=(6, 0))

        # ── 내부 탭뷰 ──
        inner_tabs = ctk.CTkTabview(self, anchor="nw")
        inner_tabs.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        inner_tabs.add("📚 기본 용어집")
        inner_tabs.add("✏️ 내 용어집")

        # ── 기본 용어집 탭 ──
        self._build_base_tab(inner_tabs.tab("📚 기본 용어집"), font_s)

        # ── 내 용어집 탭 ──
        self._build_custom_tab(inner_tabs.tab("✏️ 내 용어집"), font, font_b, font_s)

        self._active_inner_tabs = inner_tabs

    # ── 기본 용어집 탭 ─────────────────────────────────────────
    def _build_base_tab(self, parent: ctk.CTkFrame, font_s) -> None:
        ctk.CTkLabel(
            parent,
            text=f"총 {len(GLOSSARY)}개 항목 — 읽기 전용입니다. 수정은 '내 용어집' 탭을 이용하세요.",
            font=font_s, text_color="gray",
        ).pack(anchor="w", padx=8, pady=(8, 4))

        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self._base_tree = self._make_tree(tree_frame)
        self._base_all_rows = list(GLOSSARY.items())
        self._populate_tree(self._base_tree, self._base_all_rows)

    # ── 내 용어집 탭 ───────────────────────────────────────────
    def _build_custom_tab(self, parent, font, font_b, font_s) -> None:
        ctk.CTkLabel(
            parent,
            text="ℹ️  내 용어집이 기본 용어집보다 우선 적용됩니다. 같은 영어 단어가 있으면 내 용어집 값이 사용됩니다.",
            font=font_s, text_color="gray",
            wraplength=700,
        ).pack(anchor="w", padx=8, pady=(8, 4))

        tree_frame = tk.Frame(parent)
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        self._custom_tree = self._make_tree(tree_frame)
        self._custom_tree.bind("<Double-1>", self._on_custom_double_click)
        self._custom_data: dict = dict(load_custom_glossary())
        self._custom_all_rows = list(self._custom_data.items())
        self._populate_tree(self._custom_tree, self._custom_all_rows)

        # 버튼 행
        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=8, pady=(4, 8))
        ctk.CTkButton(btn_frame, text="+ 추가", font=font_b, width=80,
                      command=self._add_entry).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_frame, text="수정", font=font, width=70,
                      command=self._edit_entry).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_frame, text="삭제", font=font, width=70,
                      fg_color="#dc2626", hover_color="#b91c1c",
                      command=self._delete_entry).pack(side="left", padx=(0, 16))
        ctk.CTkButton(btn_frame, text="💾 저장", font=font_b, width=80,
                      command=self._save).pack(side="left")
        self._saved_label = ctk.CTkLabel(btn_frame, text="", font=font_s, text_color="gray")
        self._saved_label.pack(side="left", padx=12)

    # ── 공통 트리뷰 팩토리 ────────────────────────────────────
    def _make_tree(self, parent) -> ttk.Treeview:
        scale = ctk.ScalingTracker.get_widget_scaling(self)
        style = ttk.Style()
        style.configure(
            "Glossary.Treeview",
            font=("Malgun Gothic", int(11 * scale)),
            rowheight=int(24 * scale),
        )
        style.configure(
            "Glossary.Treeview.Heading",
            font=("Malgun Gothic", int(11 * scale), "bold"),
        )

        vsb = ttk.Scrollbar(parent, orient="vertical")
        vsb.pack(side="right", fill="y")

        tree = ttk.Treeview(
            parent,
            columns=("en", "ko"),
            show="headings",
            style="Glossary.Treeview",
            yscrollcommand=vsb.set,
        )
        vsb.config(command=tree.yview)
        tree.heading("en", text="영어 (English)")
        tree.heading("ko", text="한국어")
        tree.column("en", width=300, stretch=True)
        tree.column("ko", width=300, stretch=True)
        tree.pack(fill="both", expand=True)
        return tree

    def _populate_tree(self, tree: ttk.Treeview, rows: list) -> None:
        tree.delete(*tree.get_children())
        for en, ko in rows:
            tree.insert("", "end", values=(en, ko))

    # ── 검색 필터 ─────────────────────────────────────────────
    def _apply_filter(self) -> None:
        q = self._search_var.get().strip().lower()
        if q:
            base_filtered = [(e, k) for e, k in self._base_all_rows if q in e.lower() or q in k.lower()]
            custom_filtered = [(e, k) for e, k in self._custom_all_rows if q in e.lower() or q in k.lower()]
        else:
            base_filtered = self._base_all_rows
            custom_filtered = self._custom_all_rows
        self._populate_tree(self._base_tree, base_filtered)
        self._populate_tree(self._custom_tree, custom_filtered)

    # ── 내 용어집 CRUD ────────────────────────────────────────
    def _add_entry(self) -> None:
        en = simpledialog.askstring("추가", "영어 단어를 입력하세요:", parent=self)
        if not en or not en.strip():
            return
        en = en.strip()
        ko = simpledialog.askstring("추가", f'"{en}"의 한국어 번역을 입력하세요:', parent=self)
        if not ko or not ko.strip():
            return
        ko = ko.strip()
        self._custom_data[en] = ko
        self._refresh_custom_tree()

    def _edit_entry(self) -> None:
        sel = self._custom_tree.selection()
        if not sel:
            messagebox.showwarning("선택 필요", "수정할 항목을 선택하세요.", parent=self)
            return
        en, ko = self._custom_tree.item(sel[0], "values")
        new_ko = simpledialog.askstring("수정", f'"{en}"의 새 한국어 번역:', initialvalue=ko, parent=self)
        if new_ko is not None and new_ko.strip():
            self._custom_data[en] = new_ko.strip()
            self._refresh_custom_tree()

    def _delete_entry(self) -> None:
        sel = self._custom_tree.selection()
        if not sel:
            messagebox.showwarning("선택 필요", "삭제할 항목을 선택하세요.", parent=self)
            return
        en = self._custom_tree.item(sel[0], "values")[0]
        if messagebox.askyesno("삭제 확인", f'"{en}" 항목을 삭제할까요?', parent=self):
            self._custom_data.pop(en, None)
            self._refresh_custom_tree()

    def _on_custom_double_click(self, event) -> None:
        self._edit_entry()

    def _refresh_custom_tree(self) -> None:
        self._custom_all_rows = list(self._custom_data.items())
        self._apply_filter()

    def _save(self) -> None:
        save_custom_glossary(self._custom_data)
        self._saved_label.configure(text=f"✅ 저장 완료 ({len(self._custom_data)}개)")
        self.after(3000, lambda: self._saved_label.configure(text=""))
