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
from theme import C_ACCENT_ORANGE, C_ACCENT, C_ACCENT_GREEN, C_TEXT_DIM, C_TEXT_BRIGHT
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
    def __lt__(self, other):
        col = self.treeWidget().sortColumn() if self.treeWidget() else 0
        if col == 0:
            a, b = self.checkState(col).value, other.checkState(col).value
            if a != b:
                return b < a  # descending: checked (2) before unchecked (0)
            # Same checkbox state — secondary sort by name
            return self.text(self.treeWidget().COL_NAME).lower() < other.text(self.treeWidget().COL_NAME).lower()
        return self.text(col).lower() < other.text(col).lower()


class PluginManagerTab(QWidget):
    """Plugin Manager tab with tree, search, filter, and actions."""

    # Tree columns
    COL_ENABLED = 0
    COL_NAME = 1
    COL_CATEGORY = 2
    COL_DESCRIPTION = 3

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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(6)

        # ── Section 1: UE Folder Selector ──
        layout.addWidget(self._make_section_label("Unreal Engine Installation"))

        folder_row = QHBoxLayout()
        self._ue_folder_combo = QComboBox()
        self._ue_folder_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # Hide the dropdown arrow — selection happens via Browse button
        self._ue_folder_combo.setStyleSheet(
            "QComboBox { padding-right: 0px; }"
            "QComboBox::drop-down { "
            "  subcontrol-origin: padding;"
            "  subcontrol-position: top right;"
            "  width: 0px; border: none; background: transparent;"
            "}"
            "QComboBox::down-arrow { image: none; border: none; }"
        )
        self._ue_folder_combo.currentIndexChanged.connect(self._on_folder_selected)
        folder_row.addWidget(self._ue_folder_combo)

        self._browse_btn = QPushButton("Browse\u2026")
        self._browse_btn.clicked.connect(self._on_browse)
        folder_row.addWidget(self._browse_btn)

        layout.addLayout(folder_row)

        # Scanning overlay
        scan_row = QHBoxLayout()
        self._scanning_label = QLabel("Scanning plugins...")
        self._scanning_label.setVisible(False)
        scan_row.addWidget(self._scanning_label)

        self._scan_progress = QProgressBar()
        self._scan_progress.setVisible(False)
        self._scan_progress.setMaximum(0)  # Indeterminate
        self._scan_progress.setTextVisible(False)
        self._scan_progress.setFixedHeight(8)
        scan_row.addWidget(self._scan_progress, 1)
        layout.addLayout(scan_row)

        # ── Section 2: Toolbar ──
        toolbar1 = QHBoxLayout()

        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.clicked.connect(lambda: self._bulk_toggle(True))
        toolbar1.addWidget(self._select_all_btn)

        self._deselect_all_btn = QPushButton("Deselect All")
        self._deselect_all_btn.clicked.connect(lambda: self._bulk_toggle(False))
        toolbar1.addWidget(self._deselect_all_btn)

        toolbar1.addWidget(self._make_vsep())

        self._save_backup_btn = QPushButton("Save Backup")
        self._save_backup_btn.clicked.connect(self._on_save_backup)
        toolbar1.addWidget(self._save_backup_btn)

        self._load_backup_btn = QPushButton("Load Backup")
        self._load_backup_btn.clicked.connect(self._on_load_backup)
        toolbar1.addWidget(self._load_backup_btn)

        toolbar1.addWidget(self._make_vsep())

        self._save_template_btn = QPushButton("Save Template")
        self._save_template_btn.clicked.connect(self._on_save_template)
        toolbar1.addWidget(self._save_template_btn)

        self._load_template_btn = QPushButton("Load Template")
        self._load_template_btn.clicked.connect(self._on_load_template)
        toolbar1.addWidget(self._load_template_btn)

        toolbar1.addWidget(self._make_vsep())

        self._minimal_btn = QPushButton("Minimal Preset")
        self._minimal_btn.clicked.connect(self._on_minimal_preset)
        toolbar1.addWidget(self._minimal_btn)

        toolbar1.addStretch(1)

        self._revert_btn = QPushButton("Revert Changes")
        self._revert_btn.setEnabled(False)
        self._revert_btn.clicked.connect(self._on_revert_changes)
        toolbar1.addWidget(self._revert_btn)

        self._apply_btn = QPushButton("Apply Changes")
        self._apply_btn.setEnabled(False)
        self._apply_btn.setFixedWidth(140)
        self._apply_btn.clicked.connect(self._on_apply_changes)
        toolbar1.addWidget(self._apply_btn)

        self._apply_badge = QLabel("")
        self._apply_badge.setFixedWidth(30)
        toolbar1.addWidget(self._apply_badge)

        layout.addLayout(toolbar1)

        # Toolbar row 2: search
        toolbar2 = QHBoxLayout()

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search by name, friendly name, or description...")
        self._search_box.textChanged.connect(self._on_search_changed)
        toolbar2.addWidget(self._search_box, 1)

        self._clear_search_btn = QPushButton("Clear")
        self._clear_search_btn.clicked.connect(self._on_clear_search)
        toolbar2.addWidget(self._clear_search_btn)

        layout.addLayout(toolbar2)

        # ── Section 3: Plugin Tree ──
        self._tree = QTreeWidget()
        self._tree.setColumnCount(4)
        self._tree.setHeaderLabels(["Enabled", "Name", "Category", "Description"])
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QTreeWidget.NoSelection)
        self._tree.setAnimated(True)
        self._tree.setSortingEnabled(True)
        self._tree.itemChanged.connect(self._on_item_changed)

        # Columns: Enabled sizes to content, description fills remaining space
        header = self._tree.header()
        header.setStretchLastSection(False)
        header.setSortIndicator(self.COL_ENABLED, Qt.DescendingOrder)
        header.setSectionResizeMode(self.COL_ENABLED, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.COL_DESCRIPTION, QHeaderView.Stretch)
        header.resizeSection(self.COL_NAME, 220)
        header.resizeSection(self.COL_CATEGORY, 150)
        # User can drag column borders to resize; horizontal scrollbar appears when content exceeds width

        layout.addWidget(self._tree, 1)

        # ── Section 4: Status bar ──
        status_row = QHBoxLayout()
        self._stats_label = QLabel("")
        self._stats_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        status_row.addWidget(self._stats_label)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        status_row.addWidget(self._status_label)

        layout.addLayout(status_row)

        # Initial state
        self._set_action_buttons_enabled(False)
        self._update_stats()

    # ── Helpers ──

    @staticmethod
    def _make_section_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 600;
            color: {C_TEXT_BRIGHT};
            padding: 4px 0 2px 0;
        """)
        return label

    @staticmethod
    def _make_vsep() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFrameShadow(QFrame.Sunken)
        sep.setStyleSheet(f"color: {C_TEXT_DIM};")
        return sep

    def _update_stats(self):
        total = len(self._plugins)
        enabled = sum(1 for p in self._plugins if p.enabled_by_default)
        modified = sum(1 for p in self._plugins if p.is_modified)
        filtered = self._count_filtered()

        if total == 0:
            self._stats_label.setText("")
            return

        filter_info = f" (showing {filtered})" if filtered != total else ""
        self._stats_label.setText(f"{enabled} enabled  \u00b7  {total} total{filter_info}")

        if modified > 0:
            self._apply_badge.setText(f"  {modified} modified")
            self._apply_badge.setStyleSheet(f"color: {C_ACCENT_ORANGE}; font-weight: 600;")
        else:
            self._apply_badge.setText("")

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
        self._minimal_btn.setEnabled(enabled)
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
            self._ue_folder_combo.setItemData(idx, p, Qt.UserRole)
            self._ue_folder_combo.setItemData(idx, p, Qt.ToolTipRole)

        self._ue_folder_combo.blockSignals(False)

        # Auto-select and scan the first discovered installation
        if paths:
            self._ue_folder_combo.setCurrentIndex(0)
            self._on_folder_selected(0)

    # ── Event Handlers ──

    def _on_folder_selected(self, index: int):
        if index < 0:
            return
        self._current_ue_root = self._ue_folder_combo.itemData(index, Qt.UserRole) or self._ue_folder_combo.currentText()
        self._start_scan()

    def _on_browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Unreal Engine Directory")
        if not path:
            return

        # Validate
        test_file = os.path.join(path, "Engine", "Binaries", "Win64", "UnrealEditor-Engine.dll")
        if not os.path.isfile(test_file):
            self._status_label.setStyleSheet(f"color: {C_ACCENT_ORANGE};")
            self._status_label.setText("Warning: selected directory does not look like a UE installation.")

        # Check if already in combo (match on stored path)
        norm_path = os.path.normpath(path).lower()
        for i in range(self._ue_folder_combo.count()):
            stored = self._ue_folder_combo.itemData(i, Qt.UserRole)
            if stored and os.path.normpath(stored).lower() == norm_path:
                self._ue_folder_combo.setCurrentIndex(i)
                return

        self._ue_folder_combo.addItem(path)
        idx = self._ue_folder_combo.count() - 1
        self._ue_folder_combo.setItemData(idx, path, Qt.UserRole)
        self._ue_folder_combo.setItemData(idx, path, Qt.ToolTipRole)
        self._ue_folder_combo.setCurrentIndex(idx)

    def _start_scan(self):
        self._is_scanning = True
        self._set_action_buttons_enabled(False)
        self._scanning_label.setText(f"Scanning {self._current_ue_root}...")
        self._scanning_label.setVisible(True)
        self._scan_progress.setVisible(True)
        self._status_label.setText("")
        self._plugins.clear()
        self._tree.clear()

        # Background scan
        self._scanning_label.setText(f"Scanning {self._current_ue_root}...")
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
        """Save an automatic timestamped backup after a fresh scan."""
        if not self._current_ue_root or not self._plugins:
            return
        backup_dir = self._backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        version = os.path.basename(self._current_ue_root.rstrip("/\\"))
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(backup_dir, f"auto_{version}_{ts}.backup")
        self._backup.save_backup(path, self._plugins, self._current_ue_root)
        self._status_label.setText(f"Auto-backup saved: {os.path.basename(path)}")

    def _on_scan_error(self, error_msg: str):
        self._scanning_label.setVisible(False)
        self._scan_progress.setVisible(False)
        self._is_scanning = False
        self._status_label.setStyleSheet(f"color: {C_ACCENT_ORANGE};")
        self._status_label.setText(f"Scan error: {error_msg}")

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
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(self.COL_ENABLED, Qt.Checked if plugin.enabled_by_default else Qt.Unchecked)

            item.setText(self.COL_NAME, plugin.name)
            item.setToolTip(self.COL_NAME, plugin.friendly_name)
            item.setText(self.COL_CATEGORY, plugin.category)

            item.setText(self.COL_DESCRIPTION, plugin.description)

            # Store reference so itemChanged handler can find the PluginData
            item.setData(0, Qt.UserRole, id(plugin))
            self._item_plugins[id(plugin)] = plugin

            self._tree.addTopLevelItem(item)

        self._tree.blockSignals(False)
        self._update_stats()

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        if column != self.COL_ENABLED:
            return
        plugin_id = item.data(0, Qt.UserRole)
        plugin = self._item_plugins.get(plugin_id)
        if plugin is None:
            return
        checked = item.checkState(self.COL_ENABLED) == Qt.Checked
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
            PluginData(name=p.name, friendly_name=p.friendly_name,
                       description=p.description, category=p.category,
                       version_name=p.version_name,
                       enabled_by_default=p.enabled_by_default,
                       installed=p.installed, relative_path=p.relative_path,
                       full_path=p.full_path, icon_path=p.icon_path)
            for p in self._plugins
        ]
        self._update_stats()

    def _backup_dir(self) -> str:
        """Return the auto backup directory path."""
        return os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "UnrealEngineTool", "backups",
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
        self._status_label.setStyleSheet("")
        self._status_label.setText("Changes reverted to original state.")

    def _on_save_template(self):
        backup_dir = self._backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(self, "Save Template", backup_dir, "Template Files (*.template);;All Files (*)")
        if not path:
            return
        self._backup.save_template(path, self._plugins)
        QMessageBox.information(self, "Template Saved", f"Template saved to:\n{path}")

    def _on_load_template(self):
        backup_dir = self._backup_dir()
        os.makedirs(backup_dir, exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(self, "Load Template", backup_dir, "Template Files (*.template);;All Files (*)")
        if not path:
            return
        count = self._backup.load_template(path, self._plugins)
        self._refresh_view()
        QMessageBox.information(self, "Template Loaded", f"Applied template: {count} plugins enabled.")

    def _on_minimal_preset(self):
        reply = QMessageBox.question(
            self, "Apply Minimal Preset",
            "This will disable all plugins except essential engine plugins. Continue?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._backup.apply_minimal(self._plugins)
        self._refresh_view()
