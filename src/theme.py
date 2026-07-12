"""UE5 Editor-inspired dark theme QSS stylesheet.

Color palette and visual language mirroring Unreal Engine 5's editor:
  - Deep charcoal backgrounds (#1a1a1a)
  - Subtle layered surfaces (#252525 → #2d2d2d → #333333)
  - Bright blue accent (#1998FF) for selection highlights, borders on focus
  - Clean flat buttons with hover/pressed states
  - Card-style panel containers with subtle border differentiation
"""

# ── Color Palette ──
C_BG = "#1a1a1a"
C_SURFACE = "#252525"
C_SURFACE2 = "#2d2d2d"
C_PANEL = "#323232"
C_PANEL_LIGHT = "#3a3a3a"
C_CARD = "#282828"
C_CARD_BORDER = "#3c3c3c"
C_ACCENT = "#1998FF"
C_ACCENT_HOVER = "#3aabff"
C_ACCENT_ORANGE = "#FF6B35"
C_ACCENT_GREEN = "#4CAF50"
C_ACCENT_RED = "#F44336"
C_TEXT = "#cccccc"
C_TEXT_BRIGHT = "#f0f0f0"
C_TEXT_DIM = "#808080"
C_BORDER = "#474747"
C_BORDER_SUBTLE = "#333333"
C_TOGGLE_BG = "#505050"

_Q = '"'  # QSS needs careful quoting — avoid nested f-string conflicts

# ── QSS Stylesheet ──

QSS = f"""
/* ═══════════════════════════════════════════════
   UE5 EDITOR DARK THEME
   ═══════════════════════════════════════════════ */

/* ===== GLOBAL ===== */
QWidget {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-family: "Segoe UI", "Roboto", "SF Pro Text", sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {C_BG};
}}

/* ===== TAB WIDGET (main window) ===== */
QTabWidget::pane {{
    background-color: {C_BG};
    border: none;
    border-top: 1px solid {C_BORDER};
}}

QTabBar::tab {{
    background-color: {C_SURFACE};
    color: {C_TEXT};
    padding: 8px 24px;
    border: none;
    border-bottom: 1px solid {C_BORDER};
    min-width: 140px;
    font-size: 13px;
}}

QTabBar::tab:hover {{
    background-color: {C_SURFACE2};
    border-bottom: 1px solid {C_TEXT_DIM};
}}

QTabBar::tab:selected {{
    background-color: {C_BG};
    color: {C_TEXT_BRIGHT};
    border-bottom: 2px solid {C_ACCENT};
    font-weight: 600;
}}

/* ===== LABEL ===== */
QLabel {{
    color: {C_TEXT};
    background: transparent;
}}

/* ===== CARD / PANEL ===== */
/* Use on QFrame with class="card" via setProperty("class","card") */
QFrame[class="card"] {{
    background-color: {C_CARD};
    border: 1px solid {C_CARD_BORDER};
    border-radius: 6px;
    padding: 12px;
}}

/* ===== SECTION LABEL (used programmatically via setStyleSheet) ===== */
/* Inline style in code — not duplicated here as a generic rule */

/* ===== BUTTONS ===== */
QPushButton {{
    background-color: {C_PANEL};
    color: {C_TEXT_BRIGHT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 5px 16px;
    min-height: 24px;
    font-size: 13px;
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
    border-color: {C_BORDER_SUBTLE};
}}

QPushButton:checked {{
    background-color: {C_ACCENT};
    border-color: {C_ACCENT};
    color: {C_TEXT_BRIGHT};
}}

/* Primary action buttons (Apply, Save) */
QPushButton[class="primary"] {{
    background-color: {C_ACCENT};
    border-color: {C_ACCENT};
    color: {C_TEXT_BRIGHT};
    font-weight: 600;
}}

QPushButton[class="primary"]:hover {{
    background-color: {C_ACCENT_HOVER};
    border-color: {C_ACCENT_HOVER};
}}

QPushButton[class="primary"]:disabled {{
    background-color: {C_SURFACE};
    color: {C_TEXT_DIM};
    border-color: {C_BORDER_SUBTLE};
}}

/* Danger buttons (Delete, Remove) */
QPushButton[class="danger"] {{
    color: {C_ACCENT_RED};
}}

QPushButton[class="danger"]:hover {{
    background-color: #3d2222;
    border-color: {C_ACCENT_RED};
}}

QPushButton[class="danger"]:disabled {{
    color: {C_TEXT_DIM};
}}

/* Toolbar button — compact */
QPushButton[class="toolbar"] {{
    padding: 4px 12px;
    min-height: 22px;
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

QComboBox:focus {{
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

QLineEdit:disabled {{
    background-color: {C_SURFACE};
    color: {C_TEXT_DIM};
}}

/* ===== PLAIN TEXT EDIT ===== */
QPlainTextEdit {{
    background-color: {C_SURFACE2};
    color: {C_TEXT_BRIGHT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    padding: 6px 8px;
}}

QPlainTextEdit:focus {{
    border-color: {C_ACCENT};
}}

/* ===== TREE / TABLE / LIST VIEWS ===== */
QTreeView, QTableView, QListView, QTableWidget {{
    background-color: {C_SURFACE2};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: 4px;
    alternate-background-color: #303030;
    selection-background-color: {C_ACCENT}26;
    selection-color: {C_TEXT_BRIGHT};
    outline: none;
}}

QTreeView::item, QTableView::item, QTableWidget::item {{
    padding: 4px 8px;
    border-bottom: 1px solid #2a2a2a;
    min-height: 24px;
}}

QTreeView::item:hover, QTableView::item:hover {{
    background-color: {C_PANEL_LIGHT};
}}

QTreeView::item:selected, QTableView::item:selected {{
    background-color: {C_ACCENT}26;
}}

/* Table header */
QHeaderView::section {{
    background-color: {C_SURFACE};
    color: {C_TEXT};
    padding: 5px 10px;
    border: none;
    border-bottom: 1px solid {C_BORDER};
    border-right: 1px solid {C_BORDER_SUBTLE};
    font-weight: 600;
    font-size: 12px;
}}

QHeaderView::section:hover {{
    background-color: {C_SURFACE2};
}}

/* List widget items (used in the version dialog list) */
QListWidget {{
    border: 1px solid {C_BORDER};
    border-radius: 4px;
}}

QListWidget::item {{
    padding: 5px 10px;
    min-height: 22px;
}}

QListWidget::item:hover {{
    background-color: {C_PANEL_LIGHT};
}}

QListWidget::item:selected {{
    background-color: {C_ACCENT}33;
    color: {C_TEXT_BRIGHT};
}}

/* ===== PROGRESS BAR ===== */
QProgressBar {{
    background-color: {C_SURFACE};
    border: 1px solid {C_BORDER};
    border-radius: 3px;
    text-align: center;
    color: {C_TEXT_BRIGHT};
    min-height: 14px;
    font-size: 11px;
}}

QProgressBar::chunk {{
    background-color: {C_ACCENT};
    border-radius: 2px;
}}

/* ===== SCROLLBARS ===== */
QScrollBar:vertical {{
    background-color: {C_BG};
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: #555555;
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #777777;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {C_BG};
    height: 8px;
}}

QScrollBar::handle:horizontal {{
    background-color: #555555;
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #777777;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ===== CHECKBOX (toggle-style) ===== */
QCheckBox {{
    spacing: 8px;
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

/* ===== GROUP BOX ===== */
QGroupBox {{
    color: {C_TEXT_BRIGHT};
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    margin-top: 14px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
    font-size: 13px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    color: {C_TEXT_BRIGHT};
    background-color: {C_BG};
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
    padding: 6px 10px;
    font-size: 12px;
}}

/* ===== MENUBAR / MENU ===== */
QMenuBar {{
    background-color: {C_SURFACE};
    color: {C_TEXT};
    border-bottom: 1px solid {C_BORDER};
    padding: 2px 0;
}}

QMenuBar::item {{
    padding: 4px 12px;
    border-radius: 3px;
}}

QMenuBar::item:selected {{
    background-color: {C_SURFACE2};
}}

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
    margin: 4px 10px;
}}

/* ===== DIALOG ===== */
QDialog {{
    background-color: {C_BG};
}}

/* ===== STATUS BAR ===== */
QStatusBar {{
    background-color: {C_SURFACE};
    color: {C_TEXT_DIM};
    border-top: 1px solid {C_BORDER};
    padding: 2px 10px;
    font-size: 12px;
}}

QStatusBar::item {{
    border: none;
}}

/* ===== FRAME (VSeparator) ===== */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {C_BORDER};
    background-color: {C_BORDER};
}}

/* ===== INPUT DIALOG (QInputDialog internals) ===== */
QInputDialog QLineEdit {{
    margin: 4px 0;
}}

/* ===== MESSAGE BOX ===== */
QMessageBox QPushButton {{
    min-width: 80px;
}}

/* ===== BUTTON BOX (QDialogButtonBox) ===== */
QDialogButtonBox QPushButton {{
    min-width: 80px;
}}
"""


def apply_theme(app):
    """Apply the UE5 Editor dark theme to a QApplication."""
    app.setStyleSheet(QSS)
