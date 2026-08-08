
DARK_QSS = """
* { outline: none; }
QWidget {
    background-color: #14161c;
    color: #e6e8ef;
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog { background-color: #14161c; }
QToolBar {
    background-color: #1b1e27;
    border: none;
    padding: 6px;
    spacing: 6px;
}
QStatusBar { background-color: #1b1e27; color: #9aa0b4; }
QLabel { background: transparent; }
QLabel[role="metricValue"] { font-size: 16px; font-weight: 600; color: #f2f4fa; }
QLabel[role="metricLabel"] { color: #8b90a6; font-size: 11px; letter-spacing: 0.5px; text-transform: uppercase; }
QLabel[pnl="up"] { color: #3ddc97; }
QLabel[pnl="down"] { color: #ff6b6b; }
QFrame[card="true"] {
    background-color: #1b1e27;
    border: 1px solid #262a36;
    border-radius: 10px;
}
QGroupBox {
    border: 1px solid #262a36;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 12px;
    font-weight: 600;
    color: #c8cbdc;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QPushButton {
    background-color: #262a36;
    border: 1px solid #33384a;
    border-radius: 8px;
    padding: 7px 14px;
    color: #e6e8ef;
}
QPushButton:hover { background-color: #313644; border-color: #454c63; }
QPushButton:pressed { background-color: #20232c; }
QPushButton:checked { background-color: #3d6bff; border-color: #3d6bff; color: white; }
QPushButton#accent { background-color: #3d6bff; border-color: #3d6bff; color: white; font-weight: 600; }
QPushButton#accent:hover { background-color: #5580ff; }
QPushButton#danger { background-color: #4a2430; border-color: #7a3247; color: #ff9db3; }
QPushButton#danger:hover { background-color: #5c2c3c; }
QTableWidget, QTableView {
    background-color: #14161c;
    alternate-background-color: #181a22;
    gridline-color: #23262f;
    border: 1px solid #262a36;
    border-radius: 8px;
    selection-background-color: #2c3550;
}
QHeaderView::section {
    background-color: #1b1e27;
    color: #9aa0b4;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #262a36;
    font-weight: 600;
}
QTableWidget::item, QTableView::item { padding: 3px 6px; }
QTabWidget::pane { border: 1px solid #262a36; border-radius: 8px; top: -1px; }
QTabBar::tab {
    background: #1b1e27; color: #9aa0b4; padding: 8px 16px;
    border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px;
}
QTabBar::tab:selected { background: #262a36; color: #f2f4fa; }
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #1b1e27;
    border: 1px solid #33384a;
    border-radius: 6px;
    padding: 5px 8px;
    color: #e6e8ef;
}
QComboBox QAbstractItemView {
    background-color: #1b1e27;
    color: #e6e8ef;
    selection-background-color: #3d6bff;
}
QCheckBox { spacing: 8px; }
QScrollBar:vertical { background: #14161c; width: 10px; }
QScrollBar::handle:vertical { background: #33384a; border-radius: 5px; min-height: 20px; }
QScrollBar:horizontal { background: #14161c; height: 10px; }
QScrollBar::handle:horizontal { background: #33384a; border-radius: 5px; min-width: 20px; }
QSlider::groove:horizontal { height: 4px; background: #262a36; border-radius: 2px; }
QSlider::handle:horizontal { background: #3d6bff; width: 14px; margin: -6px 0; border-radius: 7px; }
QProgressBar { background: #1b1e27; border: 1px solid #262a36; border-radius: 6px; text-align: center; }
QProgressBar::chunk { background-color: #3d6bff; border-radius: 6px; }
QSplitter::handle { background: #14161c; }
QMenu { background-color: #1b1e27; border: 1px solid #262a36; }
QMenu::item:selected { background-color: #2c3550; }
"""

LIGHT_QSS = """
* { outline: none; }
QWidget {
    background-color: #f5f6fa;
    color: #1c1e26;
    font-family: "Segoe UI", "Inter", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}
QMainWindow, QDialog { background-color: #f5f6fa; }
QToolBar {
    background-color: #ffffff;
    border: none;
    padding: 6px;
    spacing: 6px;
    border-bottom: 1px solid #e3e5ec;
}
QStatusBar { background-color: #ffffff; color: #5b5f73; }
QLabel { background: transparent; }
QLabel[role="metricValue"] { font-size: 16px; font-weight: 600; color: #14161c; }
QLabel[role="metricLabel"] { color: #7a7f92; font-size: 11px; letter-spacing: 0.5px; text-transform: uppercase; }
QLabel[pnl="up"] { color: #14a374; }
QLabel[pnl="down"] { color: #e2493d; }
QFrame[card="true"] {
    background-color: #ffffff;
    border: 1px solid #e3e5ec;
    border-radius: 10px;
}
QGroupBox {
    border: 1px solid #e3e5ec;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 12px;
    font-weight: 600;
    color: #3a3d4d;
    background-color: #ffffff;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QPushButton {
    background-color: #ffffff;
    border: 1px solid #d7dae3;
    border-radius: 8px;
    padding: 7px 14px;
    color: #1c1e26;
}
QPushButton:hover { background-color: #eef0f6; border-color: #c3c7d6; }
QPushButton:pressed { background-color: #e3e5ec; }
QPushButton:checked { background-color: #3d6bff; border-color: #3d6bff; color: white; }
QPushButton#accent { background-color: #3d6bff; border-color: #3d6bff; color: white; font-weight: 600; }
QPushButton#accent:hover { background-color: #5580ff; }
QPushButton#danger { background-color: #fde8ea; border-color: #f3b7bd; color: #c22b3a; }
QPushButton#danger:hover { background-color: #fbd6da; }
QTableWidget, QTableView {
    background-color: #ffffff;
    alternate-background-color: #f7f8fc;
    gridline-color: #e9eaf1;
    border: 1px solid #e3e5ec;
    border-radius: 8px;
    selection-background-color: #dbe4ff;
}
QHeaderView::section {
    background-color: #ffffff;
    color: #7a7f92;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #e3e5ec;
    font-weight: 600;
}
QTableWidget::item, QTableView::item { padding: 3px 6px; }
QTabWidget::pane { border: 1px solid #e3e5ec; border-radius: 8px; top: -1px; background: #ffffff; }
QTabBar::tab {
    background: #eef0f6; color: #5b5f73; padding: 8px 16px;
    border-top-left-radius: 8px; border-top-right-radius: 8px; margin-right: 2px;
}
QTabBar::tab:selected { background: #ffffff; color: #14161c; }
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #ffffff;
    border: 1px solid #d7dae3;
    border-radius: 6px;
    padding: 5px 8px;
    color: #1c1e26;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #1c1e26;
    selection-background-color: #3d6bff;
}
QCheckBox { spacing: 8px; }
QScrollBar:vertical { background: #f5f6fa; width: 10px; }
QScrollBar::handle:vertical { background: #d7dae3; border-radius: 5px; min-height: 20px; }
QScrollBar:horizontal { background: #f5f6fa; height: 10px; }
QScrollBar::handle:horizontal { background: #d7dae3; border-radius: 5px; min-width: 20px; }
QSlider::groove:horizontal { height: 4px; background: #e3e5ec; border-radius: 2px; }
QSlider::handle:horizontal { background: #3d6bff; width: 14px; margin: -6px 0; border-radius: 7px; }
QProgressBar { background: #ffffff; border: 1px solid #e3e5ec; border-radius: 6px; text-align: center; }
QProgressBar::chunk { background-color: #3d6bff; border-radius: 6px; }
QSplitter::handle { background: #f5f6fa; }
QMenu { background-color: #ffffff; border: 1px solid #e3e5ec; }
QMenu::item:selected { background-color: #dbe4ff; }
"""

PALETTE = {
    "dark": {
        "bid": "#3ddc97",
        "ask": "#ff6b6b",
        "accent": "#3d6bff",
        "grid": "#262a36",
        "text": "#e6e8ef",
        "chart_bg": "#14161c",
        "candle_bull": "#3ddc97",
        "candle_bear": "#ff6b6b",
    },
    "light": {
        "bid": "#14a374",
        "ask": "#e2493d",
        "accent": "#3d6bff",
        "grid": "#e3e5ec",
        "text": "#1c1e26",
        "chart_bg": "#ffffff",
        "candle_bull": "#14a374",
        "candle_bear": "#e2493d",
    },
}

CHART_BACKGROUND_PRESETS = {
    "Match theme": None,
    "Midnight": "#0b0c10",
    "Slate": "#161a22",
    "Navy": "#0d1b2a",
    "Charcoal": "#1e1e1e",
    "Paper": "#faf7f0",
    "Off white": "#f5f6fa",
    "Pure white": "#ffffff",
    "Deep purple": "#150a24",
}


def apply_theme(app, mode: str):
    """mode: 'dark' or 'light'"""
    app.setStyleSheet(DARK_QSS if mode == "dark" else LIGHT_QSS)


def metric_label_pair(label_widget, value_widget):
    label_widget.setProperty("role", "metricLabel")
    value_widget.setProperty("role", "metricValue")
