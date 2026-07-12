#!/usr/bin/env python3
"""Unreal Engine Tool — Plugin Manager + Patcher

A desktop application for managing Unreal Engine plugins and custom engine versions.
Built with PySide6.

Usage:
    python src/main.py
"""

import sys
import os

# Ensure the src directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QLabel, QStatusBar,
    QVBoxLayout, QWidget, QSizePolicy,
)
from PySide6.QtGui import QIcon

from theme import apply_theme, C_BG, C_SURFACE, C_BORDER, C_TEXT, C_TEXT_BRIGHT, C_ACCENT
from plugin_manager_tab import PluginManagerTab
from patcher_tab import PatcherTab


class MainWindow(QMainWindow):
    """Main application window with tabbed UI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unreal Engine Tool")
        self.setMinimumSize(1024, 680)
        self.resize(1300, 820)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab container
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.North)
        self._tabs.setDocumentMode(True)
        self._tabs.setMovable(False)

        # Apply tab bar styling programmatically (in addition to QSS)
        self._tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {C_BG};
                border: none;
                border-top: 1px solid {C_BORDER};
            }}
            QTabBar::tab {{
                background-color: {C_SURFACE};
                color: {C_TEXT};
                padding: 7px 22px;
                border: none;
                border-bottom: 1px solid {C_BORDER};
                min-width: 140px;
                font-size: 13px;
            }}
            QTabBar::tab:hover {{
                background-color: {C_SURFACE};
                border-bottom: 1px solid {C_ACCENT};
            }}
            QTabBar::tab:selected {{
                background-color: {C_BG};
                color: {C_TEXT_BRIGHT};
                border-bottom: 2px solid {C_ACCENT};
                font-weight: 600;
            }}
        """)

        # Create tabs
        self._plugin_tab = PluginManagerTab()
        self._patcher_tab = PatcherTab()

        self._tabs.addTab(self._plugin_tab, "Plugin Manager")
        self._tabs.addTab(self._patcher_tab, "Patcher")

        layout.addWidget(self._tabs, 1)

        # Status bar
        self._status_bar = QStatusBar()
        self._status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {C_SURFACE};
                color: {C_TEXT};
                border-top: 1px solid {C_BORDER};
                padding: 2px 8px;
            }}
        """)
        self._status_bar.showMessage("Ready")
        self.setStatusBar(self._status_bar)

        # Tab switch handler
        self._tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index: int):
        text = self._tabs.tabText(index)
        self._status_bar.showMessage(f"Tab: {text}")


def main():
    app = QApplication(sys.argv)

    # Apply UE5 dark theme
    apply_theme(app)

    # Also set app-level palette overrides for widget types that QSS can't fully style
    app.setStyle("Fusion")  # Fusion is the most QSS-compatible style

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
