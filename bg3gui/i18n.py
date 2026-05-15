import customtkinter as ctk


def apply_korean_font(size: int = 12, bold: bool = False) -> ctk.CTkFont:
    weight = "bold" if bold else "normal"
    return ctk.CTkFont(family="Malgun Gothic", size=size, weight=weight)


def configure_default_font() -> None:
    """앱 전체 기본 한글 폰트 설정."""
    ctk.set_default_color_theme("blue")
