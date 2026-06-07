"""BG3 Mod Translator — 진입점."""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    base = Path(sys._MEIPASS)
else:
    base = Path(__file__).parent

if str(base) not in sys.path:
    sys.path.insert(0, str(base))

from PySide6.QtWidgets import QApplication
from bg3gui.app import App


def main() -> None:
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
