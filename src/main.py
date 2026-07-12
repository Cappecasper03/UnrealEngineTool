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

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget,
    QVBoxLayout, QWidget,
)

from theme import apply_theme
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
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        self._tabs.setDocumentMode(True)
        self._tabs.setMovable(False)

        # Create tabs
        self._plugin_tab = PluginManagerTab()
        self._patcher_tab = PatcherTab()

        self._tabs.addTab(self._plugin_tab, "  Plugin Manager  ")
        self._tabs.addTab(self._patcher_tab, "  Patcher  ")

        layout.addWidget(self._tabs, 1)


def main():
    app = QApplication(sys.argv)

    # Apply UE5 Editor dark theme
    apply_theme(app)

    # Fusion is the most QSS-compatible style
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
