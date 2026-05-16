import ctypes

import customtkinter as ctk


def apply_korean_font(size: int = 12, bold: bool = False) -> ctk.CTkFont:
    weight = "bold" if bold else "normal"
    return ctk.CTkFont(family="Malgun Gothic", size=size, weight=weight)


def configure_default_font() -> None:
    """앱 전체 기본 한글 폰트 설정."""
    ctk.set_default_color_theme("blue")


def enable_dpi_awareness() -> None:
    """Windows에서 DPI awareness를 활성화. 고DPI 모니터에서 tkinter 흐림 방지."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def detect_auto_scale() -> float:
    """시스템 DPI를 읽어 권장 UI 배율을 반환. 0.25 단위로 스냅. 실패 시 1.0."""
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        return max(1.0, round(dpi / 96.0 * 4) / 4)
    except Exception:
        return 1.0


def resolve_scale(scale_setting: str) -> float:
    """설정 값('auto' 또는 '1.0'~'2.0')을 실제 float 배율로 변환."""
    if scale_setting == "auto" or not scale_setting:
        return detect_auto_scale()
    try:
        return max(1.0, min(2.5, float(scale_setting)))
    except (TypeError, ValueError):
        return 1.0


def apply_ui_scale(scale_setting: str) -> float:
    """customtkinter 위젯/창 스케일을 적용하고 실제 적용된 배율을 반환."""
    scale = resolve_scale(scale_setting)
    ctk.set_widget_scaling(scale)
    ctk.set_window_scaling(scale)
    return scale
