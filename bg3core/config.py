import glob
import json
import os
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
    app_language: str = "ko"      # "ko" | "en"


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
    return UserConfig()


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
