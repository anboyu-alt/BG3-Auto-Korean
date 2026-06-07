# bg3gui/theme.py
BG_APP = "#1e1e1e"
BG_SIDEBAR = "#151515"
BG_CARD = "#2a2a2a"
BG_LOG = "#111111"
GOLD = "#d4a843"
GOLD_LIGHT = "#e8b840"
GOLD_DARK = "#c49a30"
HEADER_GRAD_START = "#1a1400"
HEADER_GRAD_END = "#2d2100"
DIVIDER = "#2a2a2a"
TEXT_PRIMARY = "#cccccc"
TEXT_SECONDARY = "#888888"
TEXT_MUTED = "#555555"
SUCCESS = "#4a9a4a"
CLOSE_BG = "#5a1a1a"


def app_stylesheet() -> str:
    return f"""
QWidget {{
    background-color: {BG_APP};
    color: {TEXT_PRIMARY};
    font-family: "Malgun Gothic", "Segoe UI", sans-serif;
    font-size: 13px;
}}
QLineEdit, QComboBox {{
    background-color: {BG_CARD};
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    padding: 7px 10px;
    color: {TEXT_PRIMARY};
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {GOLD};
}}
QPlainTextEdit {{
    background-color: {BG_LOG};
    border: 1px solid {DIVIDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 6px;
}}
QPushButton {{
    background-color: {BG_CARD};
    border: 1px solid #3a3a3a;
    border-radius: 5px;
    padding: 8px 14px;
    color: {TEXT_SECONDARY};
}}
QPushButton:hover {{
    border-color: {GOLD};
    color: {TEXT_PRIMARY};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    border-color: #2a2a2a;
}}
QPushButton#btn_start {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {GOLD_DARK}, stop:1 {GOLD_LIGHT});
    color: #1a1000;
    font-weight: bold;
    border: none;
    font-size: 13px;
}}
QPushButton#btn_start:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {GOLD_LIGHT}, stop:1 #f0c060);
}}
QPushButton#btn_start:disabled {{
    background: #3a3a2a;
    color: #666;
}}
QProgressBar {{
    background-color: {BG_CARD};
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {GOLD_DARK}, stop:1 {GOLD_LIGHT});
    border-radius: 4px;
}}
QScrollBar:vertical {{
    background: {BG_CARD};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #444;
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid #444;
    border-radius: 3px;
    background: {BG_CARD};
}}
QCheckBox::indicator:checked {{
    background: {GOLD};
    border-color: {GOLD};
}}
QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}
QLabel#label_muted {{
    color: {TEXT_MUTED};
    font-size: 11px;
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {BG_CARD};
    border: 1px solid #3a3a3a;
    selection-background-color: #3a2800;
    color: {TEXT_PRIMARY};
    outline: none;
}}
QTreeWidget {{
    background: {BG_LOG};
    border: 1px solid {DIVIDER};
    border-radius: 4px;
    color: {TEXT_PRIMARY};
    alternate-background-color: #1a1a1a;
}}
QTreeWidget::item:selected {{
    background: #3a2800;
    color: {GOLD};
}}
QTreeWidget QHeaderView::section {{
    background: {BG_CARD};
    color: {TEXT_SECONDARY};
    border: none;
    border-bottom: 1px solid {DIVIDER};
    padding: 5px 8px;
    font-weight: bold;
}}
QFrame#divider {{
    background: {DIVIDER};
    max-height: 1px;
    min-height: 1px;
}}
"""
