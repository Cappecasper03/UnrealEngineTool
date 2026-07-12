"""Plugin Manager tab UI — scan, filter, toggle, backup UE plugins."""

import os
import threading
from datetime import datetime
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, QObject, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLineEdit, QTreeWidget, QTreeWidgetItem, QLabel, QProgressBar,
    QFileDialog, QMessageBox, QFrame, QSizePolicy, QHeaderView,
)

from models import PluginData
from registry_helper import discover_ue_installations
from theme import C_ACCENT_ORANGE, C_TEXT_DIM, C_TEXT_BRIGHT, C_CARD, C_CARD_BORDER
from plugin_manager.scanner import UPluginScanner
from plugin_manager.patcher import UPluginPatcher
from plugin_manager.backup_manager import BackupManager


class ScanWorker(QObject):
    """Background worker for scanning plugins without blocking the UI."""
    finished = Signal(list)
    progress = Signal(str)
    error = Signal(str)

    def __init__(self, ue_root: str):
        super().__init__()
        self.ue_root = ue_root
        self.scanner = UPluginScanner()

    def run(self):
        try:
            plugins = self.scanner.scan(self.ue_root, self.progress.emit)
            self.finished.emit(plugins)
        except Exception as e:
            self.error.emit(str(e))


class SortableTreeItem(QTreeWidgetItem):
    """QTreeWidgetItem that sorts Enabled column by checkbox state, with name as tie-breaker."""
    COL_NAME = 1

    def __lt__(self, other):
        tw = self.treeWidget()
        col = tw.sortColumn() if tw else 0
        if col == 0:
            a, b = self.checkState(col).value, other.checkState(col).value
            if a != b:
                return a < b  # ascending definition (Qt negates for descending)
            # Same checkbox state — name a-z regardless of sort direction
            n1, n2 = self.text(self.COL_NAME).lower(), other.text(self.COL_NAME).lower()
            order = tw.header().sortIndicatorOrder()
            if order == Qt.SortOrder.DescendingOrder:
                return n2 < n1  # reversed so Qt's negation turns it back to a-z
            return n1 < n2      # ascending: a-z directly
        return self.text(col).lower() < other.text(col).lower()


# ── Helpers ──

def _make_section_card(title: str) -> tuple:
    """Create a styled section card with header.

    Returns (card_frame, inner_layout) for adding widgets to.
    The card_frame is a QFrame with class='card' styling.
    """
    card = QFrame()
    card.setObjectName("sectionCard")
    card.setStyleSheet(f"""
        QFrame#sectionCard {{
            background-color: {C_CARD};
            border: 1px solid {C_CARD_BORDER};
            border-radius: 6px;
        }}
    """)

    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(12, 8, 12, 10)
    card_layout.setSpacing(6)

    # Header label
    header = QLabel(title)
    header.setStyleSheet(f"""
        font-size: 11px;
        font-weight: 700;
        color: {C_TEXT_DIM};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 0;
        background: transparent;
    """)
    card_layout.addWidget(header)

    return card, card_layout


class PluginManagerTab(QWidget):
    """Plugin Manager tab with tree, search, filter, and actions."""

    # Tree columns
    COL_ENABLED = 0
    COL_NAME = 1
    COL_CATEGORY = 2
    COL_DESCRIPTION = 3

    # Hidden style for combo (no dropdown arrow — selection via Browse)
    _COMBO_QSS = (
        "QComboBox { padding-right: 0px; }"
        "QComboBox::drop-down { "
        "  subcontrol-origin: padding;"
        "  subcontrol-position: top right;"
        "  width: 0px; border: none; background: transparent;"
        "}"
        "QComboBox::down-arrow { image: none; border: none; }"
    )

    def __init__(self):
        super().__init__()
        self._scanner = UPluginScanner()
        self._patcher = UPluginPatcher()
        self._backup = BackupManager()

        self._plugins: List[PluginData] = []
        self._original_plugins: List[PluginData] = []
        self._current_ue_root = ""
        self._search_filter = ""
        self._is_scanning = False
        self._item_plugins: dict = {}

        self._build_ui()
        self._discover_paths()

    def _build_ui(self):
        """Build the full tab layout with card-based sections."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(10)

        # ════════════════════════════════════════════
        # CARD 1: Unreal Engine Installation
        # ════════════════════════════════════════════
        card1, c1 = _make_section_card("Installation")

        folder_row = QHBoxLayout()
        folder_row.setSpacing(6)

        self._ue_folder_combo = QComboBox()
        self._ue_folder_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._ue_folder_combo.setStyleSheet(self._COMBO_QSS)
        self._ue_folder_combo.currentIndexChanged.connect(self._on_folder_selected)
        folder_row.addWidget(self._ue_folder_combo)

        self._browse_btn = QPushButton("Browse\u2026")
        self._browse_btn.clicked.connect(self._on_browse)
        folder_row.addWidget(self._browse_btn)

        c1.addLayout(folder_row)

        # Scanning progress (hidden until active)
        scan_row = QHBoxLayout()
        self._scanning_label = QLabel("Scanning plugins\u2026")
        self._scanning_label.setVisible(False)
        self._scanning_label.setStyleSheet(f"color: {C_TEXT_DIM}; background: transparent;")
        scan_row.addWidget(self._scanning_label)

        self._scan_progress = QProgressBar()
        self._scan_progress.setVisible(False)
        self._scan_progress.setMaximum(0)  # Indeterminate
        self._scan_progress.setTextVisible(False)
        self._scan_progress.setFixedHeight(6)
        scan_row.addWidget(self._scan_progress, 1)
        c1.addLayout(scan_row)

        layout.addWidget(card1)

        # ════════════════════════════════════════════
        # CARD 2: Tools & Actions
        # ════════════════════════════════════════════
        card2, c2 = _make_section_card("Actions")

        # Toolbar row 1: bulk operations
        tool_row1 = QHBoxLayout()
        tool_row1.setSpacing(4)

        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.setObjectName("toolBtn")
        self._select_all_btn.clicked.connect(lambda: self._bulk_toggle(True))
        tool_row1.addWidget(self._select_all_btn)

        self._deselect_all_btn = QPushButton("Deselect All")
        self._deselect_all_btn.setObjectName("toolBtn")
        self._deselect_all_btn.clicked.connect(lambda: self._bulk_toggle(False))
        tool_row1.addWidget(self._deselect_all_btn)

        tool_row1.addSpacing(8)

        # Backup section
        self._save_backup_btn = QPushButton("Save Backup")
        self._save_backup_btn.setObjectName("toolBtn")
        self._save_backup_btn.clicked.connect(self._on_save_backup)
        tool_row1.addWidget(self._save_backup_btn)

        self._load_backup_btn = QPushButton("Load Backup")
        self._load_backup_btn.setObjectName("toolBtn")
        self._load_backup_btn.clicked.connect(self._on_load_backup)
        tool_row1.addWidget(self._load_backup_btn)

        tool_row1.addSpacing(8)

        # Template section
        self._save_template_btn = QPushButton("Save Template")
        self._save_template_btn.setObjectName("toolBtn")
        self._save_template_btn.clicked.connect(self._on_save_template)
        tool_row1.addWidget(self._save_template_btn)

        self._load_template_btn = QPushButton("Load Template")
        self._load_template_btn.setObjectName("toolBtn")
        self._load_template_btn.clicked.connect(self._on_load_template)
        tool_row1.addWidget(self._load_template_btn)

        tool_row1.addStretch(1)

        # Right-aligned: Revert + Apply
        self._revert_btn = QPushButton("Revert Changes")
        self._revert_btn.setObjectName("toolBtn")
        self._revert_btn.setEnabled(False)
        self._revert_btn.clicked.connect(self._on_revert_changes)
        tool_row1.addWidget(self._revert_btn)

        self._apply_btn = QPushButton("Apply Changes")
        self._apply_btn.setProperty("class", "primary")
        self._apply_btn.setEnabled(False)
        self._apply_btn.setFixedWidth(140)
        self._apply_btn.clicked.connect(self._on_apply_changes)
        tool_row1.addWidget(self._apply_btn)

        c2.addLayout(tool_row1)

        # Toolbar row 2: search
        search_row = QHBoxLayout()
        search_row.setSpacing(4)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search plugins by name, friendly name, or description\u2026")
        self._search_box.textChanged.connect(self._on_search_changed)
        search_row.addWidget(self._search_box, 1)

        self._clear_search_btn = QPushButton("Clear")
        self._clear_search_btn.setObjectName("toolBtn")
        self._clear_search_btn.clicked.connect(self._on_clear_search)
        search_row.addWidget(self._clear_search_btn)

        c2.addLayout(search_row)

        layout.addWidget(card2)

        # ════════════════════════════════════════════
        # CARD 3: Plugin List
        # ════════════════════════════════════════════
        card3, c3 = _make_section_card("Plugins")
        c3.setContentsMargins(4, 4, 0, 0)
        c3.setSpacing(0)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(4)
        self._tree.setHeaderLabels(["Enabled", "Name", "Category", "Description"])
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.NoSelection)
        self._tree.setAnimated(True)
        self._tree.setSortingEnabled(True)
        self._tree.itemChanged.connect(self._on_item_changed)

        # Columns: Enabled sizes to content, description fills remaining space
        header = self._tree.header()
        header.setStretchLastSection(False)
        header.setSortIndicator(self.COL_ENABLED, Qt.SortOrder.DescendingOrder)
        header.setSectionResizeMode(self.COL_ENABLED, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COL_DESCRIPTION, QHeaderView.ResizeMode.Stretch)
        header.resizeSection(self.COL_NAME, 220)
        header.resizeSection(self.COL_CATEGORY, 150)

        c3.addWidget(self._tree, 1)

        layout.addWidget(card3, 1)

        # ════════════════════════════════════════════
        # Stats bar (below the cards, no card wrapper)
        # ════════════════════════════════════════════
        self._stats_label = QLabel("")
        self._stats_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._stats_label.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 12px; padding: 2px 4px; background: transparent;")
        layout.addWidget(self._stats_label)

        # Initial state
        self._set_action_buttons_enabled(False)
        self._update_stats()

    # ── Helpers ──

    def _update_stats(self):
        total = len(self._plugins)
        enabled = sum(1 for p in self._plugins if p.enabled_by_default)
        modified = sum(1 for p in self._plugins if p.is_modified)
        filtered = self._count_filtered()

        if total == 0:
            self._stats_label.setText("")
            return

        filter_info = f" (showing {filtered})" if filtered != total else ""
        stats_text = f"\u2022  {enabled} enabled  \u00b7  {total} total{filter_info}"
        if modified > 0:
            stats_text += f"  \u00b7  <span style='color: {C_ACCENT_ORANGE}; font-weight: 600;'>{modified} modified</span>"
        self._stats_label.setText(stats_text)

    def _count_filtered(self) -> int:
        filtered = self._plugins
        if self._search_filter:
            s = self._search_filter.lower()
            filtered = [
                p for p in filtered
                if s in p.name.lower() or s in p.friendly_name.lower() or s in p.description.lower()
            ]
        return len(filtered)

    def _set_action_buttons_enabled(self, enabled: bool):
        self._apply_btn.setEnabled(enabled)
        self._select_all_btn.setEnabled(enabled)
        self._deselect_all_btn.setEnabled(enabled)
        self._save_backup_btn.setEnabled(enabled)
        self._load_backup_btn.setEnabled(enabled)
        self._save_template_btn.setEnabled(enabled)
        self._load_template_btn.setEnabled(enabled)
        self._revert_btn.setEnabled(enabled)
        self._search_box.setEnabled(enabled)
        self._clear_search_btn.setEnabled(enabled)

    # ── Discovery ──

    def _discover_paths(self):
        self._ue_folder_combo.blockSignals(True)
        self._ue_folder_combo.clear()

        # Auto-discover from registry + common filesystem locations
        paths = discover_ue_installations()
        for p in paths:
            self._ue_folder_combo.addItem(p)
            idx = self._ue_folder_combo.count() - 1
            self._ue_folder_combo.setItemData(idx, p, Qt.ItemDataRole.UserRole)
            self._ue_folder_combo.setItemData(idx, p, Qt.ItemDataRole.ToolTipRole)

        self._ue_folder_combo.blockSignals(False)

        # Auto-select and scan the first discovered installation
        if paths:
            self._ue_folder_combo.setCurrentIndex(0)
            self._on_folder_selected(0)

    # ── Event Handlers ──

    def _on_folder_selected(self, index: int):
        if index < 0:
            return
        self._current_ue_root = self._ue_folder_combo.itemData(index, Qt.ItemDataRole.UserRole) or self._ue_folder_combo.currentText()
        self._start_scan()

    def _on_browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Unreal Engine Directory")
        if not path:
            return

        # Check if already in combo (match on stored path)
        norm_path = os.path.normpath(path).lower()
        for i in range(self._ue_folder_combo.count()):
            stored = self._ue_folder_combo.itemData(i, Qt.ItemDataRole.UserRole)
            if stored and os.path.normpath(stored).lower() == norm_path:
                self._ue_folder_combo.setCurrentIndex(i)
                return

        self._ue_folder_combo.addItem(path)
        idx = self._ue_folder_combo.count() - 1
        self._ue_folder_combo.setItemData(idx, path, Qt.ItemDataRole.UserRole)
        self._ue_folder_combo.setItemData(idx, path, Qt.ItemDataRole.ToolTipRole)
        self._ue_folder_combo.setCurrentIndex(idx)

    def _start_scan(self):
        self._is_scanning = True
        self._set_action_buttons_enabled(False)
        self._scanning_label.setText(f"Scanning {self._current_ue_root}\u2026")
        self._scanning_label.setVisible(True)
        self._scan_progress.setVisible(True)
        self._plugins.clear()
        self._tree.clear()

        # Background scan
        self._scanning_label.setText(f"Scanning {self._current_ue_root}\u2026")
        self._scan_progress.setMaximum(0)  # Indeterminate

        self._thread = QThread()
        self._worker = ScanWorker(self._current_ue_root)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.error.connect(self._on_scan_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _on_scan_finished(self, plugins: List[PluginData]):
        self._plugins = plugins
        self._original_plugins = [
            PluginData(
                name=p.name, friendly_name=p.friendly_name,
                description=p.description, category=p.category,
                version_name=p.version_name,
                enabled_by_default=p.enabled_by_default,
                installed=p.installed, relative_path=p.relative_path,
                full_path=p.full_path, icon_path=p.icon_path,
            )
            for p in plugins
        ]

        for p in self._plugins:
            p.snapshot_original()

        self._scanning_label.setVisible(False)
        self._scan_progress.setVisible(False)
        self._is_scanning = False
        self._set_action_buttons_enabled(True)
        self._refresh_view()
        self._update_stats()
        self._auto_save_backup()

    def _auto_save_backup(self):
        """Save an automatic timestamped backup after a fresh scan (always enabled, keep 10)."""
        if not self._current_ue_root or not self._plugins:
            return
        backup_dir = self._backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        version = os.path.basename(self._current_ue_root.rstrip("/\\"))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(backup_dir, f"auto_{version}_{ts}.backup")
        self._backup.save_backup(path, self._plugins, self._current_ue_root)

        # Prune old backups — keep at most 10 per engine version
        keep = 10
        backups = sorted(
            f for f in os.listdir(backup_dir)
            if f.startswith(f"auto_{version}_") and f.endswith(".backup")
        )
        while len(backups) > keep:
            os.remove(os.path.join(backup_dir, backups.pop(0)))

    def _on_scan_error(self, error_msg: str):
        self._scanning_label.setVisible(False)
        self._scan_progress.setVisible(False)
        self._is_scanning = False

    def _on_search_changed(self, text: str):
        self._search_filter = text
        self._refresh_view()

    def _on_clear_search(self):
        self._search_box.clear()
        self._search_filter = ""
        self._refresh_view()

    def _refresh_view(self):
        self._tree.blockSignals(True)
        self._tree.clear()

        filtered = self._plugins
        if self._search_filter:
            s = self._search_filter.lower()
            filtered = [
                p for p in filtered
                if s in p.name.lower() or s in p.friendly_name.lower() or s in p.description.lower()
            ]
            # Prioritize: friendly name matches first, then name matches, then description-only
            def _search_rank(p) -> tuple:
                lower = p.friendly_name.lower() if p.friendly_name else ""
                if s in lower:
                    return 0
                if s in p.name.lower():
                    return 1
                return 2
            filtered.sort(key=_search_rank)

        self._item_plugins.clear()

        for plugin in filtered:
            item = SortableTreeItem()

            # Native tree-item checkboxes — reliable with sorting enabled
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(self.COL_ENABLED, Qt.CheckState.Checked if plugin.enabled_by_default else Qt.CheckState.Unchecked)

            item.setText(self.COL_NAME, plugin.name)
            item.setToolTip(self.COL_NAME, plugin.friendly_name)
            item.setText(self.COL_CATEGORY, plugin.category)

            item.setText(self.COL_DESCRIPTION, plugin.description)

            # Store reference so itemChanged handler can find the PluginData
            item.setData(0, Qt.ItemDataRole.UserRole, id(plugin))
            self._item_plugins[id(plugin)] = plugin

            self._tree.addTopLevelItem(item)

        self._tree.blockSignals(False)
        self._update_stats()

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        if column != self.COL_ENABLED:
            return
        plugin_id = item.data(0, Qt.ItemDataRole.UserRole)
        plugin = self._item_plugins.get(plugin_id)
        if plugin is None:
            return
        checked = item.checkState(self.COL_ENABLED) == Qt.CheckState.Checked
        plugin.enabled_by_default = checked
        self._update_stats()

    def _bulk_toggle(self, enabled: bool):
        for p in self._plugins:
            p.enabled_by_default = enabled
        self._refresh_view()

    def _update_toggle_buttons(self):
        pass  # Handled by Qt signals

    def _on_apply_changes(self):
        if not self._current_ue_root:
            return

        plugins_root = os.path.join(self._current_ue_root, "Engine", "Plugins")
        result = self._patcher.apply_changes(self._plugins, self._original_plugins, plugins_root)

        if result.error_count > 0:
            msg = f"Applied {result.modified_count} changes with {result.error_count} errors:\n"
            msg += "\n".join(result.errors)
            QMessageBox.warning(self, "Apply Results", msg)
        else:
            QMessageBox.information(self, "Apply Complete", f"Successfully applied {result.modified_count} change(s).")

        # Update original snapshots
        for p in self._plugins:
            p.snapshot_original()
        self._original_plugins = [
            PluginData(
                name=p.name, friendly_name=p.friendly_name,
                description=p.description, category=p.category,
                version_name=p.version_name,
                enabled_by_default=p.enabled_by_default,
                installed=p.installed, relative_path=p.relative_path,
                full_path=p.full_path, icon_path=p.icon_path,
            )
            for p in self._plugins
        ]
        self._update_stats()

    def _backup_dir(self) -> str:
        """Return the auto backup directory path."""
        return os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "UnrealEngineTool", "backups",
        )

    @staticmethod
    def _template_dir() -> str:
        """Return the template directory path."""
        return os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "UnrealEngineTool", "templates",
        )

    def _on_save_backup(self):
        backup_dir = self._backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "Save Backup", backup_dir, "Backup Files (*.backup);;All Files (*)")
        if not path:
            return
        self._backup.save_backup(path, self._plugins, self._current_ue_root)
        QMessageBox.information(self, "Backup Saved", f"Backup saved to:\n{path}")

    def _on_load_backup(self):
        backup_dir = self._backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(self, "Load Backup", backup_dir, "Backup Files (*.backup);;All Files (*)")
        if not path:
            return
        count = self._backup.load_backup(path, self._plugins, self._current_ue_root)
        self._refresh_view()
        QMessageBox.information(self, "Backup Loaded", f"Restored {count} plugin states from backup.")

    def _on_revert_changes(self):
        """Reset all plugins back to their original enabled states before any edits."""
        if not self._original_plugins or not self._plugins:
            return
        for p, orig in zip(self._plugins, self._original_plugins):
            p.enabled_by_default = orig.enabled_by_default
            p.snapshot_original()
        self._refresh_view()
        self._update_stats()

    def _on_save_template(self):
        template_dir = self._template_dir()
        os.makedirs(template_dir, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "Save Template", template_dir, "Template Files (*.template);;All Files (*)")
        if not path:
            return
        self._backup.save_template(path, self._plugins)
        QMessageBox.information(self, "Template Saved", f"Template saved to:\n{path}")

    def _on_load_template(self):
        template_dir = self._template_dir()
        os.makedirs(template_dir, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(self, "Load Template", template_dir, "Template Files (*.template);;All Files (*)")
        if not path:
            return
        count = self._backup.load_template(path, self._plugins)
        self._refresh_view()
        QMessageBox.information(self, "Template Loaded", f"Applied template: {count} plugins enabled.")
