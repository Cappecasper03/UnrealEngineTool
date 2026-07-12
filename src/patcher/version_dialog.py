"""Dialogs for creating, editing, and deleting engine versions and their file entries."""

import os
import shutil
from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QLineEdit, QLabel, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QHeaderView, QWidget, QSizePolicy,
    QGridLayout, QComboBox, QDialogButtonBox, QFrame,
)

from models import EngineInfo, EngineFile
from patcher.version_io import read_info, write_info, create_version, delete_version, discover_versions
from theme import C_ACCENT, C_ACCENT_GREEN, C_ACCENT_RED, C_TEXT_DIM, C_TEXT_BRIGHT, C_BORDER, C_BG, C_SURFACE2


# ── File Entry Edit Sub-Dialog ──

class FileEntryDialog(QDialog):
    """Dialog for adding or editing a single EngineFile entry."""

    def __init__(self, parent=None, entry: Optional[EngineFile] = None,
                 version_dir: str = ""):
        super().__init__(parent)
        self.setWindowTitle("File Entry" if not entry else "Edit File Entry")
        self.setMinimumWidth(520)
        self._version_dir = version_dir
        self._custom_abs = ""  # Absolute path the user picked (for copy into version dir)

        self._build_ui()

        if entry:
            self._custom_path.setText(entry.path_custom)
            self._default_path.setText(entry.path_default)
            self._target_path.setText(entry.path_target)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        grid = QGridLayout()
        grid.setSpacing(6)

        grid.addWidget(QLabel("Custom File:"), 0, 0)
        self._custom_path = QLineEdit()
        self._custom_path.setPlaceholderText("Relative path in version directory (e.g. Engine/Src/foo.h)")
        grid.addWidget(self._custom_path, 0, 1)
        self._custom_btn = QPushButton("Browse\u2026")
        self._custom_btn.clicked.connect(self._on_browse_custom)
        grid.addWidget(self._custom_btn, 0, 2)

        grid.addWidget(QLabel("Default File:"), 1, 0)
        self._default_path = QLineEdit()
        self._default_path.setPlaceholderText("Optional default/original file path")
        grid.addWidget(self._default_path, 1, 1)
        self._default_btn = QPushButton("Browse\u2026")
        self._default_btn.clicked.connect(self._on_browse_default)
        grid.addWidget(self._default_btn, 1, 2)

        grid.addWidget(QLabel("Target Path:"), 2, 0)
        self._target_path = QLineEdit()
        self._target_path.setPlaceholderText("Path relative to UE root (e.g. Engine/Source/.../foo.h)")
        grid.addWidget(self._target_path, 2, 1, 1, 2)

        layout.addLayout(grid)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self._save_btn = QPushButton("OK")
        self._save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self._save_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._cancel_btn)

        layout.addLayout(btn_row)

    def _on_browse_custom(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Custom File")
        if path:
            self._custom_abs = path
            # If inside version dir, store relative; otherwise just store the abs path
            if self._version_dir and path.startswith(self._version_dir):
                rel = os.path.relpath(path, self._version_dir).replace("\\", "/")
                self._custom_path.setText(rel)
            else:
                # Store absolute; user can set relative manually
                self._custom_path.setText(path)

    def _on_browse_default(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Default File")
        if path:
            if self._version_dir and path.startswith(self._version_dir):
                rel = os.path.relpath(path, self._version_dir).replace("\\", "/")
                self._default_path.setText(rel)
            else:
                self._default_path.setText(path)

    def _on_save(self):
        if not self._custom_path.text().strip() and not self._default_path.text().strip():
            QMessageBox.warning(self, "Missing Data", "At least one of Custom or Default file must be set.")
            return
        if not self._target_path.text().strip():
            QMessageBox.warning(self, "Missing Data", "Target path is required.")
            return
        self.accept()

    def get_entry(self) -> EngineFile:
        return EngineFile(
            path_custom=self._custom_path.text().strip(),
            path_default=self._default_path.text().strip(),
            path_target=self._target_path.text().strip(),
            local_name=os.path.basename(self._custom_path.text().strip() or self._default_path.text().strip()),
        )

    @property
    def custom_abs_path(self) -> str:
        return self._custom_abs


# ── Version Manager Dialog ──

_COMBO_QSS = (
    "QComboBox { padding-right: 0px; }"
    "QComboBox::drop-down { "
    "  subcontrol-origin: padding;"
    "  subcontrol-position: top right;"
    "  width: 0px; border: none; background: transparent;"
    "}"
    "QComboBox::down-arrow { image: none; border: none; }"
)


class VersionManagerDialog(QDialog):
    """Dialog for creating, editing, and deleting engine versions and their file entries."""

    def __init__(self, parent=None, versions_root: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Version Manager")
        self.setMinimumSize(800, 560)
        self.resize(900, 620)

        self._versions_root = versions_root
        self._versions: List[EngineInfo] = []
        self._dirty = False  # Track whether any changes were made

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(8)

        # ── Top: version list (left) + details (right) ──
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        # Left: version list
        left_panel = QVBoxLayout()
        left_panel.setSpacing(4)

        left_panel.addWidget(QLabel("Versions"))

        self._version_list = QListWidget()
        self._version_list.setMinimumWidth(160)
        self._version_list.currentRowChanged.connect(self._on_selection_changed)
        left_panel.addWidget(self._version_list, 1)

        list_btn_row = QHBoxLayout()
        self._new_btn = QPushButton("New")
        self._new_btn.clicked.connect(self._on_new)
        list_btn_row.addWidget(self._new_btn)

        self._clone_btn = QPushButton("Clone")
        self._clone_btn.setEnabled(False)
        self._clone_btn.clicked.connect(self._on_clone)
        list_btn_row.addWidget(self._clone_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete)
        list_btn_row.addWidget(self._delete_btn)

        left_panel.addLayout(list_btn_row)
        top_row.addLayout(left_panel)

        # Right: version details
        right_panel = QVBoxLayout()
        right_panel.setSpacing(6)

        right_panel.addWidget(QLabel("Version Details"))

        det_grid = QGridLayout()
        det_grid.setSpacing(5)

        det_grid.addWidget(QLabel("Engine Version:"), 0, 0)
        self._ver_name = QLineEdit()
        self._ver_name.setPlaceholderText("e.g. v1.0")
        det_grid.addWidget(self._ver_name, 0, 1)

        det_grid.addWidget(QLabel("UE Version:"), 1, 0)
        self._ue_ver = QLineEdit()
        self._ue_ver.setPlaceholderText("e.g. 5.4")
        det_grid.addWidget(self._ue_ver, 1, 1)

        det_grid.addWidget(QLabel("Parent:"), 2, 0)
        self._parent_combo = QComboBox()
        self._parent_combo.setStyleSheet(_COMBO_QSS)
        self._parent_combo.addItem("(none)", "")
        det_grid.addWidget(self._parent_combo, 2, 1)

        det_grid.addWidget(QLabel("Changelog:"), 3, 0, Qt.AlignTop)
        self._changelog = QPlainTextEdit()
        self._changelog.setPlaceholderText("Describe what changed in this version...")
        self._changelog.setMinimumHeight(70)
        det_grid.addWidget(self._changelog, 3, 1)

        right_panel.addLayout(det_grid)

        right_panel.addStretch(1)
        top_row.addLayout(right_panel, 1)

        layout.addLayout(top_row, 1)

        # ── File entries table ──
        layout.addWidget(QLabel("File Entries"))

        self._file_table = QTableWidget(0, 4)
        self._file_table.setHorizontalHeaderLabels(["#", "Custom Path", "Default Path", "Target Path"])
        self._file_table.horizontalHeader().setStretchLastSection(True)
        self._file_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._file_table.horizontalHeader().resizeSection(0, 30)
        self._file_table.verticalHeader().setVisible(False)
        self._file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._file_table.setSelectionMode(QTableWidget.SingleSelection)
        self._file_table.setMinimumHeight(120)
        layout.addWidget(self._file_table, 1)

        file_btn_row = QHBoxLayout()
        self._file_add_btn = QPushButton("Add File\u2026")
        self._file_add_btn.setEnabled(False)
        self._file_add_btn.clicked.connect(self._on_add_file)
        file_btn_row.addWidget(self._file_add_btn)

        self._file_edit_btn = QPushButton("Edit")
        self._file_edit_btn.setEnabled(False)
        self._file_edit_btn.clicked.connect(self._on_edit_file)
        file_btn_row.addWidget(self._file_edit_btn)

        self._file_remove_btn = QPushButton("Remove")
        self._file_remove_btn.setEnabled(False)
        self._file_remove_btn.clicked.connect(self._on_remove_file)
        file_btn_row.addWidget(self._file_remove_btn)

        file_btn_row.addStretch(1)
        layout.addLayout(file_btn_row)

        # ── Bottom buttons ──
        btn_row = QHBoxLayout()

        self._save_all_btn = QPushButton("Save All Changes")
        self._save_all_btn.clicked.connect(self._on_save_all)
        btn_row.addWidget(self._save_all_btn)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._refresh_list)
        btn_row.addWidget(self._refresh_btn)

        btn_row.addStretch(1)

        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self._on_close)
        btn_row.addWidget(self._close_btn)

        layout.addLayout(btn_row)

    # ── List management ──

    def _refresh_list(self):
        self._versions = discover_versions(self._versions_root)

        # Update parent combo items
        self._parent_combo.blockSignals(True)
        current_parent = self._parent_combo.currentData()
        self._parent_combo.clear()
        self._parent_combo.addItem("(none)", "")
        for v in self._versions:
            self._parent_combo.addItem(v.engine_version, v.engine_version)
        # Restore selection if possible
        idx = self._parent_combo.findData(current_parent)
        if idx >= 0:
            self._parent_combo.setCurrentIndex(idx)
        self._parent_combo.blockSignals(False)

        # Rebuild list
        self._version_list.blockSignals(True)
        self._version_list.clear()
        for v in self._versions:
            self._version_list.addItem(v.engine_version)
        self._version_list.blockSignals(False)

        if self._versions:
            self._version_list.setCurrentRow(0)
        else:
            self._clear_details()
            self._file_add_btn.setEnabled(False)

    def _on_selection_changed(self, row: int):
        if row < 0 or row >= len(self._versions):
            self._clear_details()
            self._clone_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)
            self._file_add_btn.setEnabled(False)
            self._file_edit_btn.setEnabled(False)
            self._file_remove_btn.setEnabled(False)
            return

        version = self._versions[row]
        self._ver_name.setText(version.engine_version)
        self._ue_ver.setText(version.unreal_version)

        idx = self._parent_combo.findData(version.parent_version)
        self._parent_combo.setCurrentIndex(max(idx, 0))

        self._changelog.setPlainText(version.changelog)

        self._populate_file_table(version.files)

        self._clone_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)
        self._file_add_btn.setEnabled(True)
        self._file_edit_btn.setEnabled(False)
        self._file_remove_btn.setEnabled(False)

    def _clear_details(self):
        self._ver_name.clear()
        self._ue_ver.clear()
        self._parent_combo.setCurrentIndex(0)
        self._changelog.clear()
        self._file_table.setRowCount(0)

    def _populate_file_table(self, files: List[EngineFile]):
        self._file_table.setRowCount(len(files))
        for i, f in enumerate(files):
            self._file_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self._file_table.setItem(i, 1, QTableWidgetItem(f.path_custom))
            self._file_table.setItem(i, 2, QTableWidgetItem(f.path_default))
            self._file_table.setItem(i, 3, QTableWidgetItem(f.path_target))
            for c in range(4):
                item = self._file_table.item(i, c)
                if item:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)

    # ── Version CRUD ──

    def _on_new(self):
        name, ok = self._ask_name("New Version", "Engine version name:")
        if not ok or not name.strip():
            return

        try:
            new_ver = create_version(self._versions_root, name.strip())
            self._versions.append(new_ver)
            self._dirty = True
            self._refresh_list()
            # Select the new version
            for i, v in enumerate(self._versions):
                if v.engine_version == name.strip():
                    self._version_list.setCurrentRow(i)
                    break
        except FileExistsError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _on_clone(self):
        row = self._version_list.currentRow()
        if row < 0 or row >= len(self._versions):
            return
        source = self._versions[row]

        name, ok = self._ask_name("Clone Version", f"New name (cloned from {source.engine_version}):")
        if not ok or not name.strip():
            return

        try:
            new_ver = create_version(
                self._versions_root, name.strip(),
                unreal_version=source.unreal_version,
                parent_version=source.parent_version,
                clone_from=source,
            )
            # Also copy the actual files from the source version directory
            src_dir = os.path.dirname(source.info_dir)
            dst_dir = os.path.dirname(new_ver.info_dir)
            if os.path.isdir(src_dir):
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

            self._versions.append(new_ver)
            self._dirty = True
            self._refresh_list()
            for i, v in enumerate(self._versions):
                if v.engine_version == name.strip():
                    self._version_list.setCurrentRow(i)
                    break
        except FileExistsError as e:
            QMessageBox.warning(self, "Error", str(e))

    def _on_delete(self):
        row = self._version_list.currentRow()
        if row < 0 or row >= len(self._versions):
            return
        version = self._versions[row]

        reply = QMessageBox.question(
            self, "Delete Version",
            f"Delete version '{version.engine_version}' and ALL its files?\n"
            f"Location: {os.path.dirname(version.info_dir)}\n\n"
            "This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        try:
            delete_version(version)
            self._versions.pop(row)
            self._dirty = True
            self._refresh_list()
        except (FileNotFoundError, OSError) as e:
            QMessageBox.warning(self, "Error", f"Failed to delete version: {e}")

    # ── File entry management ──

    def _on_add_file(self):
        row = self._version_list.currentRow()
        if row < 0 or row >= len(self._versions):
            return
        version = self._versions[row]
        ver_dir = os.path.dirname(version.info_dir)

        dlg = FileEntryDialog(self, version_dir=ver_dir)
        if dlg.exec() == QDialog.Accepted:
            entry = dlg.get_entry()
            version.files.append(entry)

            # Copy custom file into version directory if it was an external absolute path
            abs_path = dlg.custom_abs_path
            if abs_path and not abs_path.startswith(ver_dir):
                # User picked an external file — copy it into the version dir
                rel_target = entry.path_custom
                if os.path.isabs(rel_target):
                    # Use just the filename relative to version dir
                    rel_target = os.path.basename(rel_target)
                    entry.path_custom = rel_target
                dest = os.path.join(ver_dir, rel_target)
                dest_dir = os.path.dirname(dest)
                if dest_dir and not os.path.isdir(dest_dir):
                    os.makedirs(dest_dir, exist_ok=True)
                try:
                    shutil.copy2(abs_path, dest)
                except OSError as e:
                    QMessageBox.warning(self, "Warning",
                                        f"Could not copy file to version directory:\n{e}")

            self._dirty = True
            self._populate_file_table(version.files)

    def _on_edit_file(self):
        row = self._version_list.currentRow()
        if row < 0 or row >= len(self._versions):
            return
        version = self._versions[row]
        sel = self._file_table.currentRow()
        if sel < 0 or sel >= len(version.files):
            return
        ver_dir = os.path.dirname(version.info_dir)

        dlg = FileEntryDialog(self, entry=version.files[sel], version_dir=ver_dir)
        if dlg.exec() == QDialog.Accepted:
            version.files[sel] = dlg.get_entry()
            self._dirty = True
            self._populate_file_table(version.files)

    def _on_remove_file(self):
        row = self._version_list.currentRow()
        if row < 0 or row >= len(self._versions):
            return
        version = self._versions[row]
        sel = self._file_table.currentRow()
        if sel < 0 or sel >= len(version.files):
            return

        version.files.pop(sel)
        self._dirty = True
        self._populate_file_table(version.files)

    # ── Save / Close ──

    def _on_save_all(self):
        """Write all version metadata back to disk."""
        for version in self._versions:
            # Update from UI fields if this version is currently selected
            row = self._version_list.currentRow()
            if row >= 0 and row < len(self._versions) and self._versions[row] is version:
                version.engine_version = self._ver_name.text().strip()
                version.unreal_version = self._ue_ver.text().strip()
                version.parent_version = self._parent_combo.currentData() or ""
                version.changelog = self._changelog.toPlainText().strip()

            try:
                write_info(version)
            except OSError as e:
                QMessageBox.warning(self, "Save Error",
                                    f"Failed to save '{version.engine_version}': {e}")

        self._dirty = False
        self._refresh_list()
        QMessageBox.information(self, "Saved",
                                f"{len(self._versions)} version(s) saved.")

    def _on_close(self):
        if self._dirty:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Save before closing?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            )
            if reply == QMessageBox.Save:
                self._on_save_all()
            elif reply == QMessageBox.Cancel:
                return
        self.accept()

    # ── Helpers ──

    def _ask_name(self, title: str, prompt: str) -> tuple:
        """Show a small input dialog and return (text, accepted)."""
        from PySide6.QtWidgets import QInputDialog
        dlg = QInputDialog(self)
        dlg.setWindowTitle(title)
        dlg.setLabelText(prompt)
        dlg.setInputMode(QInputDialog.TextInput)
        ok = dlg.exec() == QDialog.Accepted
        return dlg.textValue(), ok

    def versions_changed(self) -> bool:
        """Return True if the version list was modified in any way."""
        return self._dirty
