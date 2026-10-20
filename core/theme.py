BG = "#1C1C1E"
PANEL = "#242426"
CARD = "#2C2C2E"
CARD_ON = "#26313F"
FIELD = "#1E1E20"
BORDER = "#38383A"
BORDER_ON = "#3E5B80"
TEXT = "#F5F5F7"
MUTED = "#98989D"
ACCENT = "#0A84FF"
ACCENT_HOVER = "#2E96FF"
DANGER = "#FF453A"

QSS = f"""
* {{
    font-family: "SF Pro Text", "Segoe UI Variable Text", "Segoe UI", sans-serif;
    font-size: 12px;
    color: {TEXT};
}}
QWidget#Root {{ background: {BG}; }}

QLabel#Title {{ font-size: 17px; font-weight: 600; letter-spacing: -0.2px; }}
QLabel#Subtitle {{ color: {MUTED}; font-size: 11px; }}
QLabel#SectionTitle {{ font-size: 11px; font-weight: 600; color: {MUTED}; }}
QLabel#Hint {{ color: {MUTED}; font-size: 10px; }}
QLabel#Badge {{ color: {MUTED}; font-size: 11px; }}

QFrame#Panel {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QFrame#Notice {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QLabel#NoticeText {{ color: {MUTED}; font-size: 11px; }}

QFrame#Card {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 12px;
}}
QFrame#Card[on="true"] {{
    background: {CARD_ON};
    border: 1px solid {BORDER_ON};
}}

QCheckBox {{ spacing: 8px; font-weight: 500; font-size: 12px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px;
    border: 1px solid #4A4A4E; border-radius: 5px; background: {FIELD};
}}
QCheckBox::indicator:hover {{ border: 1px solid {ACCENT}; }}
QCheckBox::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QListWidget {{
    background: {FIELD};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 4px 9px;
    selection-background-color: {ACCENT};
    selection-color: #FFFFFF;
}}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: #5A5A5E; background: #232325;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 15px; border: none; background: transparent;
}}
/* Стрелки рисуем границами: картинок в теме нет, а системные в тёмной
   палитре Fusion почти не видны. */
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    width: 0; height: 0;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-bottom: 4px solid {MUTED};
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    width: 0; height: 0;
    border-left: 3px solid transparent;
    border-right: 3px solid transparent;
    border-top: 4px solid {MUTED};
}}
QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {{ border-bottom-color: {TEXT}; }}
QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {{ border-top-color: {TEXT}; }}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {{ border-bottom-color: #4A4A4E; }}
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {{ border-top-color: #4A4A4E; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 4px;
    selection-background-color: {ACCENT};
    selection-color: #FFFFFF;
    outline: none;
}}
QListWidget {{ padding: 4px; }}
QListWidget::item {{ padding: 3px 6px; border-radius: 7px; }}
QListWidget::item:selected {{ background: {ACCENT}; color: #FFFFFF; }}

QPushButton {{
    background: #3A3A3C;
    border: none;
    border-radius: 15px;
    padding: 6px 16px;
    font-weight: 500;
    min-height: 18px;
}}
QPushButton:hover {{ background: #48484A; }}
QPushButton:pressed {{ background: #313133; }}
QPushButton:disabled {{ background: #2A2A2C; color: #5A5A5E; }}

QPushButton#Primary {{
    background: {ACCENT}; color: #FFFFFF;
    border: none; border-radius: 17px;
    padding: 8px 24px; font-size: 12px; font-weight: 600;
}}
QPushButton#Primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#Primary:disabled {{ background: #23405E; color: #7FA6CC; }}
QPushButton#Danger {{ background: #3A2A2A; color: {DANGER}; }}
QPushButton#Danger:hover {{ background: #4A3230; }}
QPushButton#Danger:disabled {{ background: #2A2A2C; color: #5A5A5E; }}
QPushButton#Ghost {{ background: transparent; color: {MUTED}; }}
QPushButton#Ghost:hover {{ background: #313133; color: {TEXT}; }}

QProgressBar {{
    background: #313133; border: none;
    border-radius: 3px; height: 6px; text-align: center;
}}
QProgressBar::chunk {{ border-radius: 3px; background: {ACCENT}; }}

QPlainTextEdit#Log {{
    font-family: "SF Mono", "Cascadia Mono", "Consolas", monospace;
    font-size: 10px; color: {MUTED}; background: {FIELD};
}}

QScrollArea {{ border: none; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 9px; margin: 3px; }}
QScrollBar::handle:vertical {{ background: #48484A; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #5A5A5E; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QToolTip {{
    background: {PANEL}; color: {TEXT};
    border: 1px solid {BORDER}; padding: 5px 8px; border-radius: 8px;
}}

QMessageBox, QInputDialog {{ background: {BG}; }}

QTabWidget::pane {{ border: none; background: {BG}; }}
QTabBar {{ background: {BG}; qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: transparent;
    color: {MUTED};
    padding: 7px 18px;
    margin: 8px 4px 4px 12px;
    border: 1px solid transparent;
    border-radius: 14px;
    font-weight: 500;
}}
QTabBar::tab:!first {{ margin-left: 0; }}
QTabBar::tab:hover {{ background: #313133; color: {TEXT}; }}
QTabBar::tab:selected {{
    background: {CARD_ON};
    border: 1px solid {BORDER_ON};
    color: {TEXT};
}}
"""
