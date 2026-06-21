import glob
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from .constants import MODELS_TO_TRY


@dataclass
class UserConfig:
    api_key: str = ""
    divine_exe_path: str = ""
    model_preference: List[str] = field(default_factory=lambda: list(MODELS_TO_TRY))
    cache_path: str = ""
    log_dir: str = ""
    last_pak_dir: str = ""
    last_output_dir: str = ""
    skip_if_korean_exists: bool = True
    mcm_enabled: bool = True
    ui_scale: str = "auto"  # "auto" | "1.0" | "1.25" | "1.5" | "1.75" | "2.0"
    target_language: str = "Korean"
    app_language: str = "ko"      # "ko" | "en" | ... (v6.0: 15개 언어)
    bg3_install_path: str = ""    # …\Baldurs Gate 3 (공식 언어팩 참조·게임 언어 자동감지에 사용)


def get_config_dir() -> Path:
    appdata = os.environ.get("APPDATA", Path.home())
    return Path(appdata) / "BG3-Auto-Korean"


def get_config_path() -> Path:
    return get_config_dir() / "config.json"


def get_default_cache_path() -> str:
    return str(get_config_dir() / "translation_cache.json")


def get_default_log_dir() -> str:
    return str(get_config_dir() / "logs")


def load_config() -> UserConfig:
    path = get_config_path()
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            cfg = UserConfig()
            for k, v in data.items():
                if hasattr(cfg, k):
                    setattr(cfg, k, v)
            return cfg
        except Exception:
            pass
    return _first_run_defaults()


def _first_run_defaults() -> UserConfig:
    """설정 파일이 없을 때(첫 실행) 똑똑한 기본값을 제안한다.

    BG3 설치 경로와 Divine.exe를 자동 탐지하고, 게임 설정 언어로 번역 대상 언어와
    앱 UI 언어를 맞춘다. 사용자가 저장하면 이 값이 config.json에 기록된다.
    """
    cfg = UserConfig()
    divine = auto_detect_divine()
    if divine:
        cfg.divine_exe_path = divine
    bg3 = auto_detect_bg3()
    if bg3:
        cfg.bg3_install_path = bg3
        lang = detect_game_language(bg3)
        if lang:
            cfg.target_language = lang
            # 앱 UI 언어는 현재 ko/en (Phase 3에서 15개로 확장). 그때 lang→UI코드 매핑 확장.
            cfg.app_language = "ko" if lang == "Korean" else "en"
    return cfg


def save_config(cfg: UserConfig) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg.__dict__, f, ensure_ascii=False, indent=2)


def auto_detect_divine() -> Optional[str]:
    patterns = [
        r"C:\ExportTool-*\Packed\Tools\Divine.exe",
        r"C:\Users\*\Downloads\ExportTool-*\Packed\Tools\Divine.exe",
        r"D:\ExportTool-*\Packed\Tools\Divine.exe",
        r"E:\ExportTool-*\Packed\Tools\Divine.exe",
        r"F:\ExportTool-*\Packed\Tools\Divine.exe",
        r"C:\Program Files\ExportTool-*\Packed\Tools\Divine.exe",
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return str(sorted(matches)[-1])
    return None


_BG3_REL = os.path.join("steamapps", "common", "Baldurs Gate 3")


def _steam_library_paths() -> List[str]:
    """Steam 라이브러리 폴더 경로 목록. 레지스트리 SteamPath + libraryfolders.vdf 파싱."""
    libs: List[str] = []
    steam = None
    try:
        import winreg
        for hive, key, name in (
            (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
        ):
            try:
                with winreg.OpenKey(hive, key) as k:
                    steam = winreg.QueryValueEx(k, name)[0]
                    break
            except OSError:
                continue
    except Exception:
        steam = None
    if not steam:
        return libs
    steam = steam.replace("/", "\\")
    libs.append(steam)
    vdf = Path(steam) / "steamapps" / "libraryfolders.vdf"
    if vdf.exists():
        try:
            text = vdf.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r'"path"\s*"([^"]+)"', text):
                libs.append(m.group(1).replace("\\\\", "\\"))
        except Exception:
            pass
    # 중복 제거(순서 유지)
    return list(dict.fromkeys(libs))


def auto_detect_bg3() -> Optional[str]:
    """BG3 설치 폴더(…\\Baldurs Gate 3)를 자동 탐지. 못 찾으면 None.

    Steam 라이브러리들을 우선 확인하고, 실패 시 흔한 경로를 글롭으로 시도한다.
    language.lsx 존재로 유효성을 검증한다.
    """
    candidates: List[str] = [os.path.join(lib, _BG3_REL) for lib in _steam_library_paths()]
    candidates += glob.glob(r"?:\SteamLibrary\steamapps\common\Baldurs Gate 3")
    candidates += glob.glob(r"?:\Program Files (x86)\Steam\steamapps\common\Baldurs Gate 3")
    candidates += glob.glob(r"?:\GOG Games\Baldurs Gate 3")
    for path in candidates:
        if os.path.isfile(os.path.join(path, "Data", "Localization", "language.lsx")):
            return path
    return None


def detect_game_language(bg3_install_path: str) -> Optional[str]:
    """BG3 language.lsx에서 게임 설정 언어를 읽어 반환(예: "Korean"). 못 읽으면 None.

    LANGUAGE_PROFILES의 folder_name과 동일한 식별자를 반환하도록 게임이 기록한다.
    """
    if not bg3_install_path:
        return None
    lsx = Path(bg3_install_path) / "Data" / "Localization" / "language.lsx"
    if not lsx.is_file():
        return None
    try:
        text = lsx.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    m = re.search(r'value="Language".*?id="Value"\s+value="([^"]+)"', text, re.DOTALL)
    return m.group(1) if m else None
