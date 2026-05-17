import webbrowser
from typing import Callable, Optional

import customtkinter as ctk
from tkinter import messagebox

from bg3core.config import UserConfig, save_config
from bg3core.divine import check_divine_exe
from .widgets.path_picker import PathPicker


class SettingsTab(ctk.CTkFrame):
    def __init__(self, master, on_config_saved: Optional[Callable[[UserConfig], None]] = None, **kwargs):
        super().__init__(master, **kwargs)
        self._on_config_saved = on_config_saved
        self._cfg: Optional[UserConfig] = None
        font = ctk.CTkFont(family="Malgun Gothic", size=12)
        font_b = ctk.CTkFont(family="Malgun Gothic", size=12, weight="bold")
        font_s = ctk.CTkFont(family="Malgun Gothic", size=11)

        # ── API 키 ──
        row = 0
        ctk.CTkLabel(self, text="Gemini API 키", font=font_b).grid(
            row=row, column=0, columnspan=3, padx=16, pady=(16, 4), sticky="w"
        )
        row += 1
        self._api_entry = ctk.CTkEntry(self, font=font, show="*", width=400)
        self._api_entry.grid(row=row, column=0, columnspan=2, padx=16, pady=2, sticky="ew")
        self._show_btn = ctk.CTkButton(
            self, text="보기", font=font, width=60, command=self._toggle_api_vis
        )
        self._show_btn.grid(row=row, column=2, padx=(4, 16), pady=2)
        self._api_visible = False

        row += 1
        ctk.CTkButton(
            self, text="API 키 발급 페이지 열기 →", font=font_s,
            command=lambda: webbrowser.open("https://aistudio.google.com"),
            fg_color="transparent", text_color=("blue", "lightblue"),
        ).grid(row=row, column=0, padx=16, pady=(0, 8), sticky="w")

        # ── Divine.exe ──
        row += 1
        ctk.CTkLabel(self, text="Divine.exe 경로 (LSLib ExportTool)", font=font_b).grid(
            row=row, column=0, columnspan=3, padx=16, pady=(8, 4), sticky="w"
        )
        row += 1
        self._divine_picker = PathPicker(
            self, label="",
            mode="file",
            filetypes=[("실행 파일", "*.exe"), ("All files", "*.*")],
        )
        self._divine_picker.grid(row=row, column=0, columnspan=3, padx=16, pady=2, sticky="ew")

        row += 1
        ctk.CTkButton(
            self, text="LSLib 다운로드 페이지 열기 →", font=font_s,
            command=lambda: webbrowser.open("https://github.com/Norbyte/lslib/releases"),
            fg_color="transparent", text_color=("blue", "lightblue"),
        ).grid(row=row, column=0, padx=16, pady=(0, 8), sticky="w")

        # ── 모델 ──
        row += 1
        ctk.CTkLabel(self, text="AI 모델 (우선순위)", font=font_b).grid(
            row=row, column=0, columnspan=3, padx=16, pady=(8, 4), sticky="w"
        )
        row += 1
        self._model1 = ctk.CTkComboBox(
            self, font=font, width=260,
            values=["gemini-3.1-flash-lite", "gemini-2.5-flash-lite", "gemini-2.5-flash"],
        )
        self._model1.grid(row=row, column=0, padx=16, pady=2, sticky="w")
        ctk.CTkLabel(self, text="→ 1순위", font=font_s).grid(row=row, column=1, sticky="w")

        row += 1
        self._model2 = ctk.CTkComboBox(
            self, font=font, width=260,
            values=["gemini-2.5-flash-lite", "gemini-3.1-flash-lite", "gemini-2.5-flash"],
        )
        self._model2.grid(row=row, column=0, padx=16, pady=2, sticky="w")
        ctk.CTkLabel(self, text="→ 폴백", font=font_s).grid(row=row, column=1, sticky="w")

        # ── UI 배율 ──
        row += 1
        ctk.CTkLabel(self, text="UI 배율 (글씨 크기)", font=font_b).grid(
            row=row, column=0, columnspan=3, padx=16, pady=(12, 4), sticky="w"
        )
        row += 1
        self._scale_label_to_value = {
            "자동 (모니터 DPI)": "auto",
            "100%": "1.0",
            "125%": "1.25",
            "150%": "1.5",
            "175%": "1.75",
            "200%": "2.0",
        }
        self._scale_value_to_label = {v: k for k, v in self._scale_label_to_value.items()}
        self._scale_combo = ctk.CTkComboBox(
            self, font=font, width=260,
            values=list(self._scale_label_to_value.keys()),
            state="readonly",
        )
        self._scale_combo.grid(row=row, column=0, padx=16, pady=2, sticky="w")
        ctk.CTkLabel(
            self, text="고해상도 모니터에서 글씨가 작으면 키우세요", font=font_s, text_color="gray",
        ).grid(row=row, column=1, columnspan=2, padx=(4, 16), sticky="w")

        # ── 캐시 ──
        row += 1
        ctk.CTkLabel(self, text="번역 캐시 파일", font=font_b).grid(
            row=row, column=0, columnspan=3, padx=16, pady=(12, 4), sticky="w"
        )
        row += 1
        self._cache_picker = PathPicker(
            self, label="",
            mode="file",
            filetypes=[("JSON 파일", "*.json"), ("All files", "*.*")],
        )
        self._cache_picker.grid(row=row, column=0, columnspan=3, padx=16, pady=2, sticky="ew")

        # ── Korean 폴더 스킵 ──
        row += 1
        self._skip_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self, text="Korean 폴더가 이미 있으면 스킵",
            font=font, variable=self._skip_var,
        ).grid(row=row, column=0, padx=16, pady=(8, 2), sticky="w")

        # ── MCM 자동 처리 ──
        row += 1
        self._mcm_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            self, text="MCM 의존 모드 자동 처리 (블루프린트·Lua)",
            font=font, variable=self._mcm_var,
        ).grid(row=row, column=0, padx=16, pady=(2, 8), sticky="w")

        # ── 버튼 + 저장 안내 ──
        row += 1
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=3, padx=16, pady=(8, 4), sticky="ew")
        ctk.CTkButton(btn_frame, text="저장", font=font_b, command=self._save).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="테스트 연결", font=font, command=self._test).pack(side="left")

        row += 1
        ctk.CTkLabel(
            self,
            text="💾  저장하면 다음 실행 시에도 API 키와 경로가 자동으로 불러와집니다.",
            font=font_s,
            text_color="gray",
        ).grid(row=row, column=0, columnspan=3, padx=16, pady=(0, 16), sticky="w")

        self.grid_columnconfigure(0, weight=1)

    def load_config(self, cfg: UserConfig) -> None:
        self._cfg = cfg
        self._api_entry.delete(0, "end")
        self._api_entry.insert(0, cfg.api_key)
        self._divine_picker.set(cfg.divine_exe_path)
        if cfg.model_preference:
            self._model1.set(cfg.model_preference[0] if len(cfg.model_preference) > 0 else "gemini-3.1-flash-lite")
            self._model2.set(cfg.model_preference[1] if len(cfg.model_preference) > 1 else "gemini-2.5-flash-lite")
        self._cache_picker.set(cfg.cache_path)
        self._skip_var.set(cfg.skip_if_korean_exists)
        self._mcm_var.set(cfg.mcm_enabled)
        scale_label = self._scale_value_to_label.get(cfg.ui_scale, "자동 (모니터 DPI)")
        self._scale_combo.set(scale_label)

    def _build_config(self) -> UserConfig:
        cfg = self._cfg or UserConfig()
        cfg.api_key = self._api_entry.get().strip()
        cfg.divine_exe_path = self._divine_picker.get()
        cfg.model_preference = [m for m in [self._model1.get(), self._model2.get()] if m]
        cfg.cache_path = self._cache_picker.get()
        cfg.skip_if_korean_exists = self._skip_var.get()
        cfg.mcm_enabled = self._mcm_var.get()
        cfg.ui_scale = self._scale_label_to_value.get(self._scale_combo.get(), "auto")
        return cfg

    def _save(self) -> None:
        prev_scale = self._cfg.ui_scale if self._cfg else "auto"
        cfg = self._build_config()
        save_config(cfg)
        scale_changed = cfg.ui_scale != prev_scale
        self._cfg = cfg
        if self._on_config_saved:
            self._on_config_saved(cfg)
        if scale_changed:
            messagebox.showinfo(
                "저장 완료",
                "설정이 저장되었습니다.\n\nUI 배율은 프로그램을 다시 실행하면 적용됩니다.",
            )
        else:
            messagebox.showinfo("저장 완료", "설정이 저장되었습니다.\n다음에 실행해도 자동으로 불러옵니다.")

    def _test(self) -> None:
        cfg = self._build_config()
        errors = []
        if not cfg.api_key:
            errors.append("• API 키가 비어 있습니다.")
        if not cfg.divine_exe_path:
            errors.append("• Divine.exe 경로가 비어 있습니다.")
        elif not check_divine_exe(cfg.divine_exe_path):
            errors.append(f"• Divine.exe를 찾을 수 없습니다:\n  {cfg.divine_exe_path}")
        if errors:
            messagebox.showerror("설정 오류", "\n".join(errors))
        else:
            messagebox.showinfo("확인 완료", "API 키와 Divine.exe 경로가 올바릅니다.\n(API 키 유효성은 실제 번역 시 확인됩니다)")

    def _toggle_api_vis(self) -> None:
        self._api_visible = not self._api_visible
        self._api_entry.configure(show="" if self._api_visible else "*")
        self._show_btn.configure(text="숨기기" if self._api_visible else "보기")
