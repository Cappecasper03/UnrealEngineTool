"""UE5-inspired dark theme QSS stylesheet for the Unreal Engine Tool.

Everything is driven by a single QSS string applied to the QApplication.
"""

# ── Color Palette (mapped from the Godot C# theme) ──
# Using named colors so we could programmatically adjust them later
C_BG = "#1A1A1A"
C_SURFACE = "#252525"
C_SURFACE2 = "#2D2D2D"
C_PANEL = "#333333"
C_PANEL_LIGHT = "#383838"
C_ACCENT = "#1998FF"
C_ACCENT_ORANGE = "#FF6B35"
C_ACCENT_GREEN = "#4CAF50"
C_ACCENT_RED = "#F44336"
C_TEXT = "#CCCCCC"
C_TEXT_BRIGHT = "#F0F0F0"
C_TEXT_DIM = "#808080"
C_BORDER = "#474747"

# ── Icons (embedded SVG for custom checkbox/radio) ──
# We use Unicode characters where possible, SVG for check/radio states

# ── QSS Stylesheet ──

QSS = f"""
/* ===== GLOBAL ===== */
QWidget {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-family: "Segoe UI", "SF Pro Text", "Roboto", sans-serif;
    font-size: 13px;
}}

/* ===== WINDOW ===== */
QMainWindow {{
    background-color: {C_BG};
}}

/* ===== TAB WIDGET ===== */
QTabWidget::pane {{
    background-color: {C_BG};
    border: none;
    border-top: 1px solid {C_BORDER};
}}

QTabBar::tab {{
    background-color: {C_SURFACE};
    color: {C_TEXT};
    padding: 6px 18px;
    border: none;
    border-bottom: 1px solid {C_BORDER};
    min-width: 120px;
}}

QTabBar::tab:hover {{
    background-color: {C_SURFACE2};
    border-bottom: 1px solid {C_ACCENT_ORANGE};
}}

QTabBar::tab:selected {{
    background-color: {C_BG};
    color: {C_TEXT_BRIGHT};
    border-bottom: 2px solid {C_ACCENT};
}}

/* ===== BUTTONS ===== */
QPushButton {{
    background-color: {C_PANEL};
    color: {C_TEXT_BRIGHT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 5px 14px;
    min-height: 22px;
}}

QPushButton:hover {{
    background-color: {C_PANEL_LIGHT};
    border-color: {C_ACCENT};
}}

QPushButton:pressed {{
    background-color: {C_ACCENT};
    border-color: {C_ACCENT};
}}

QPushButton:disabled {{
    background-color: {C_SURFACE};
    color: {C_TEXT_DIM};
    border-color: #333333;
}}

QPushButton:checked {{
    background-color: {C_ACCENT};
    border-color: {C_ACCENT};
    color: {C_TEXT_BRIGHT};
}}

/* ===== COMBO BOX ===== */
QComboBox {{
    background-color: {C_PANEL};
    color: {C_TEXT_BRIGHT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 22px;
}}

QComboBox:hover {{
    border-color: {C_ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {C_TEXT};
    margin-right: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: {C_SURFACE2};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    selection-background-color: {C_ACCENT}26;
    selection-color: {C_TEXT_BRIGHT};
    outline: none;
}}

/* ===== LINE EDIT ===== */
QLineEdit {{
    background-color: {C_SURFACE2};
    color: {C_TEXT_BRIGHT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    min-height: 22px;
}}

QLineEdit:focus {{
    border-color: {C_ACCENT};
}}

QLineEdit::placeholder {{
    color: {C_TEXT_DIM};
}}

/* ===== TEXT EDIT / PLAIN TEXT EDIT ===== */
QPlainTextEdit {{
    background-color: {C_SURFACE2};
    color: {C_TEXT_BRIGHT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 4px;
}}

QPlainTextEdit:focus {{
    border-color: {C_ACCENT};
}}

/* ===== TREE / TABLE / LIST VIEWS ===== */
QTreeView, QTableView, QListView {{
    background-color: {C_SURFACE2};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    alternate-background-color: #303030;
    selection-background-color: {C_ACCENT}26;
    selection-color: {C_TEXT_BRIGHT};
    outline: none;
}}

QTreeView::item, QTableView::item, QListView::item {{
    padding: 3px 6px;
    border-bottom: 1px solid #2A2A2A;
}}

QTreeView::item:hover, QTableView::item:hover {{
    background-color: #3A3A3A;
}}

QTreeView::item:selected, QTableView::item:selected {{
    background-color: {C_ACCENT}26;
}}

/* Header */
QHeaderView::section {{
    background-color: {C_SURFACE};
    color: {C_TEXT};
    padding: 5px 8px;
    border: none;
    border-bottom: 1px solid {C_BORDER};
    border-right: 1px solid {C_BORDER};
    font-weight: 600;
}}

QHeaderView::section:hover {{
    background-color: {C_SURFACE2};
}}

/* ===== PROGRESS BAR ===== */
QProgressBar {{
    background-color: {C_SURFACE};
    border: none;
    border-radius: 3px;
    text-align: center;
    color: {C_TEXT_BRIGHT};
    min-height: 16px;
}}

QProgressBar::chunk {{
    background-color: {C_ACCENT};
    border-radius: 3px;
}}

/* ===== SCROLL BARS ===== */
QScrollBar:vertical {{
    background-color: {C_BG};
    width: 10px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {C_BORDER};
    border-radius: 5px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {C_TEXT_DIM};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {C_BG};
    height: 10px;
}}

QScrollBar::handle:horizontal {{
    background-color: {C_BORDER};
    border-radius: 5px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {C_TEXT_DIM};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ===== CHECKBOX ===== */
QCheckBox {{
    spacing: 6px;
    color: {C_TEXT};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {C_BORDER};
    border-radius: 3px;
    background-color: {C_SURFACE2};
}}

QCheckBox::indicator:checked {{
    background-color: {C_ACCENT};
    border-color: {C_ACCENT};
}}

QCheckBox::indicator:hover {{
    border-color: {C_ACCENT};
}}

/* ===== LABEL ===== */
QLabel {{
    color: {C_TEXT};
}}

/* ===== SPLITTER ===== */
QSplitter::handle {{
    background-color: {C_BORDER};
}}

/* ===== TOOLTIP ===== */
QToolTip {{
    background-color: {C_SURFACE2};
    color: {C_TEXT_BRIGHT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 4px 8px;
}}

/* ===== MENU ===== */
QMenu {{
    background-color: {C_SURFACE2};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 4px;
}}

QMenu::item {{
    padding: 5px 24px;
    border-radius: 3px;
}}

QMenu::item:selected {{
    background-color: {C_ACCENT}26;
    color: {C_TEXT_BRIGHT};
}}

QMenu::separator {{
    height: 1px;
    background-color: {C_BORDER};
    margin: 4px 8px;
}}

/* ===== DIALOG ===== */
QDialog {{
    background-color: {C_BG};
}}

/* ===== GROUP BOX ===== */
QGroupBox {{
    color: {C_TEXT_BRIGHT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {C_TEXT_BRIGHT};
}}
"""


def apply_theme(app):
    """Apply the UE5 dark theme to a QApplication."""
    app.setStyleSheet(QSS)
