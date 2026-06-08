"""BG3 Mod Translator — 진입점."""
import os
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    base = Path(sys._MEIPASS)
else:
    base = Path(__file__).parent

if str(base) not in sys.path:
    sys.path.insert(0, str(base))


def _apply_ui_scale() -> None:
    """저장된 UI 배율을 QApplication 생성 전에 환경변수로 적용한다.

    Qt는 QT_SCALE_FACTOR를 QApplication 인스턴스화 시점에 읽으므로 반드시
    그 전에 설정해야 한다. "auto"이거나 값이 잘못되면 건드리지 않고 Qt 기본
    고해상도 스케일링에 맡긴다. 사용자가 직접 지정한 값은 존중하기 위해
    이미 환경변수가 설정돼 있으면 덮어쓰지 않는다.
    """
    if os.environ.get("QT_SCALE_FACTOR"):
        return
    try:
        from bg3core.config import load_config
        scale = (load_config().ui_scale or "auto").strip().lower()
    except Exception:
        return
    if not scale or scale == "auto":
        return
    try:
        if float(scale) > 0:
            os.environ["QT_SCALE_FACTOR"] = scale
    except ValueError:
        pass


def main() -> None:
    _apply_ui_scale()

    from PySide6.QtWidgets import QApplication
    from bg3gui.app import App

    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
