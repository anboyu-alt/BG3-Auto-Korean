import shutil
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from bg3core.config import UserConfig, get_default_cache_path, load_config, save_config
from .i18n import configure_default_font
from .settings_tab import SettingsTab
from .translate_tab import TranslateTab
from .reviewer_tab import ReviewerTab
from .glossary_tab import GlossaryTab


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        configure_default_font()
        ctk.set_appearance_mode("system")

        self.title("BG3 모드 자동 한글화 v3.0")
        self.geometry("860x680")
        self.minsize(720, 500)

        self._cfg: UserConfig = load_config()

        # 첫 실행 감지 (API 키 없음)
        self._first_run = not self._cfg.api_key

        self._tabs = ctk.CTkTabview(self, anchor="nw")
        self._tabs.pack(fill="both", expand=True, padx=12, pady=12)

        self._tabs.add("⚙️ 설정")
        self._tabs.add("🔄 번역")
        self._tabs.add("🔍 검수")
        self._tabs.add("📖 용어집")

        self._settings_tab = SettingsTab(
            self._tabs.tab("⚙️ 설정"),
            on_config_saved=self._on_config_saved,
        )
        self._settings_tab.pack(fill="both", expand=True)
        self._settings_tab.load_config(self._cfg)

        self._translate_tab = TranslateTab(self._tabs.tab("🔄 번역"))
        self._translate_tab.pack(fill="both", expand=True)
        self._translate_tab.set_config(self._cfg)

        self._reviewer_tab = ReviewerTab(self._tabs.tab("🔍 검수"))
        self._reviewer_tab.pack(fill="both", expand=True)
        self._reviewer_tab.set_config(self._cfg)

        self._glossary_tab = GlossaryTab(self._tabs.tab("📖 용어집"))
        self._glossary_tab.pack(fill="both", expand=True)

        # 첫 실행: 설정 탭으로 포커스
        if self._first_run:
            self._tabs.set("⚙️ 설정")
            self.after(300, self._show_onboarding)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_config_saved(self, cfg: UserConfig) -> None:
        self._cfg = cfg
        self._translate_tab.set_config(cfg)
        self._reviewer_tab.set_config(cfg)

    def _show_onboarding(self) -> None:
        messagebox.showinfo(
            "BG3 모드 자동 한글화에 오신 것을 환영합니다!",
            "처음 사용하시는군요!\n\n"
            "1. [설정] 탭에서 Gemini API 키와 Divine.exe 경로를 입력하세요.\n"
            "2. 저장 후 [번역] 탭에서 PAK 파일을 선택하고 시작하세요.\n\n"
            "API 키 발급: https://aistudio.google.com\n"
            "LSLib 다운로드: https://github.com/Norbyte/lslib/releases",
        )

    def _on_close(self) -> None:
        # 번역 중이면 확인
        if self._translate_tab._running:
            if not messagebox.askyesno(
                "종료 확인",
                "번역이 진행 중입니다. 정말 종료하시겠습니까?\n(진행 중인 파일은 저장되지 않을 수 있습니다)"
            ):
                return
            self._translate_tab._cancel_event.set()

        # 검수 임시 폴더 정리
        temp = getattr(self._reviewer_tab, "_temp_dir", None)
        if temp and Path(temp).exists():
            shutil.rmtree(temp, ignore_errors=True)

        self.destroy()
