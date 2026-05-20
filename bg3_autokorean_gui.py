"""BG3 모드 자동 한글화 GUI v3.7 — 진입점."""

import sys
from pathlib import Path

# PyInstaller 번들 환경에서 프로젝트 루트를 sys.path에 추가
if getattr(sys, "frozen", False):
    base = Path(sys._MEIPASS)
else:
    base = Path(__file__).parent

if str(base) not in sys.path:
    sys.path.insert(0, str(base))

from bg3gui.app import App


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
