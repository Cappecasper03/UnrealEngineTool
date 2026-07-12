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


# ── File Entry Adder (multi-file selection + auto binary detection) ──

def _relativise(path: str, version_dir: str = "") -> str:
    """Convert an absolute file path to an engine-relative path."""
    if version_dir and path.startswith(version_dir):
        return os.path.relpath(path, version_dir).replace("\\", "/")
    norm = path.replace("\\", "/")
    idx = norm.lower().find("/engine/")
    if idx >= 0:
        return norm[idx + 1:]
    return os.path.basename(path)


def _find_engine_root(path: str) -> str:
    """Walk up from a file path to find the UE installation root (parent of Engine/)."""
    norm = os.path.normpath(path).replace("\\", "/")
    idx = norm.lower().find("/engine/")
    if idx < 0:
        return ""
    return norm[:idx]  # Everything before /Engine/


def _module_name_from_path(rel_path: str) -> str:
    """Extract the UE module name from an engine-relative source path.

    Engine/Source/{Category}/{ModuleName}/...  →  ModuleName
    Returns empty string if the path isn't under Engine/Source/.
    """
    # Normalise and split
    parts = rel_path.replace("\\", "/").split("/")
    # Expect: Engine, Source, <Category>, <ModuleName>, ...
    if len(parts) >= 4 and parts[0].lower() == "engine" and parts[1].lower() == "source":
        return parts[3]  # The module name
    return ""


def _discover_binaries(ue_root: str, source_modules: set) -> List[tuple]:
    """Scan Engine/Binaries/Win64 for .dll, .exe, .pdb, .lib, .target files matching the given module names.

    Binary naming pattern: UnrealEditor-{ModuleName}.dll / .pdb / .lib / .target
    Only files for modules present in *source_modules* are returned.
    Returns list of (relative_path, abs_path) tuples.
    """
    bin_dir = os.path.join(ue_root, "Engine", "Binaries", "Win64")
    if not os.path.isdir(bin_dir) or not source_modules:
        return []

    # Build set of expected prefixes: UnrealEditor-<Module>.
    prefixes = {f"UnrealEditor-{m}." for m in source_modules if m}

    intermediate_exts = {".dll", ".exe", ".pdb", ".lib", ".target"}

    results = []
    for fn in sorted(os.listdir(bin_dir)):
        ext = os.path.splitext(fn)[1].lower()
        if ext not in intermediate_exts:
            continue
        # Check if filename starts with any of the expected prefixes
        for prefix in prefixes:
            if fn.lower().startswith(prefix.lower()):
                rel = f"Engine/Binaries/Win64/{fn}"
                results.append((rel, os.path.join(bin_dir, fn)))
                break  # One match per file is enough

    return results


def _discover_module_intermediates(ue_root: str, source_modules: set,
                                   source_stems: set = set()) -> List[tuple]:
    """Scan Engine/Intermediate/Build/Win64/ for generated and precompiled files.

    Actual UE path structure:
      Win64/{Target}/
        Inc/{Module}/.../{File}.generated.h
        Development/{Module}/{File}.cpp.obj / .h.obj / .precompiled
        Shipping/{Module}/{File}.cpp.obj / .h.obj / .precompiled

    *source_stems* are base names of selected source files (e.g. "HomeScreenSettings").
    Only .generated.h files whose stem (base.generated.h  →  base) matches one of
    *source_stems* are returned.

    Returns list of (relative_path, abs_path) tuples.
    """
    if not source_modules:
        return []

    base = os.path.join(ue_root, "Engine", "Intermediate", "Build", "Win64")
    if not os.path.isdir(base):
        return []

    # Normalise module names for case-insensitive comparison
    module_lower = {m.lower() for m in source_modules if m}
    stem_lower = {s.lower() for s in source_stems if s}

    results = []
    precompiled_exts = {".cpp.obj", ".h.obj", ".precompiled"}

    # Iterate over target directories (UnrealEditor, UnrealGame, etc.)
    for target in sorted(os.listdir(base)):
        target_dir = os.path.join(base, target)
        if not os.path.isdir(target_dir):
            continue

        # --- Generated files: Inc/{Module}/.../*.generated.h ---
        inc_dir = os.path.join(target_dir, "Inc")
        if os.path.isdir(inc_dir):
            for root, _dirs, files in os.walk(inc_dir):
                for fn in files:
                    if not fn.lower().endswith(".generated.h"):
                        continue
                    # Check module name is part of the relative path under Inc/
                    rel_under_inc = os.path.relpath(root, inc_dir).replace("\\", "/")
                    path_parts = rel_under_inc.split("/")
                    if not path_parts or path_parts[0].lower() not in module_lower:
                        continue
                    # Only include .generated.h whose stem matches a selected source file
                    if stem_lower:
                        file_stem = fn[:-len(".generated.h")]
                        if file_stem.lower() not in stem_lower:
                            continue
                    full_rel = f"Engine/Intermediate/Build/Win64/{target}/Inc/{rel_under_inc}/{fn}"
                    results.append((full_rel, os.path.join(root, fn)))

        # --- Precompiled files per config ---
        for config in ("Development", "Shipping"):
            cfg_dir = os.path.join(target_dir, config)
            if not os.path.isdir(cfg_dir):
                continue
            for root, _dirs, files in os.walk(cfg_dir):
                for fn in files:
                    full_lower = fn.lower()
                    if not any(full_lower.endswith(e) for e in precompiled_exts):
                        continue
                    # Check module name is part of the relative path under config/
                    rel_under_cfg = os.path.relpath(root, cfg_dir).replace("\\", "/")
                    path_parts = rel_under_cfg.split("/")
                    if not path_parts or path_parts[0].lower() not in module_lower:
                        continue
                    full_rel = f"Engine/Intermediate/Build/Win64/{target}/{config}/{rel_under_cfg}/{fn}"
                    results.append((full_rel, os.path.join(root, fn)))

    return results


class FileEntryDialog(QDialog):
    """Dialog for selecting one or more files and returning EngineFile entries.

    Each selected file gets its engine-relative path auto-extracted.
    If files come from a recognised UE installation, binaries from
    Engine/Binaries/Win64 are auto-discovered and included.
    """

    def __init__(self, parent=None, version_dir: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Add Files")
        self.setMinimumWidth(520)
        self.setMinimumHeight(350)
        self.resize(560, 420)
        self._version_dir = version_dir
        self._entries: List[EngineFile] = []  # Populated after OK
        self._copied_abs: List[str] = []      # Absolute paths of files to copy in

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Instructions
        layout.addWidget(QLabel("Select one or more files to add as patch entries."))
        layout.addWidget(QLabel("Module binaries and intermediates are auto-included based on selected source files."))

        # Browse button
        browse_row = QHBoxLayout()
        self._browse_btn = QPushButton("Browse Files\u2026")
        self._browse_btn.clicked.connect(self._on_browse)
        browse_row.addWidget(self._browse_btn)
        browse_row.addStretch(1)
        layout.addLayout(browse_row)

        # File list
        self._file_list = QListWidget()
        self._file_list.setMinimumHeight(120)
        self._file_list.setAlternatingRowColors(True)
        layout.addWidget(self._file_list, 1)

        # Selected files count / binary info
        self._info_label = QLabel("")
        self._info_label.setStyleSheet("color: #808080; font-size: 11px;")
        layout.addWidget(self._info_label)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self._add_btn = QPushButton("Add Files")
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add)
        btn_row.addWidget(self._add_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._cancel_btn)

        layout.addLayout(btn_row)

    def _on_browse(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Add as Patch Entries"
        )
        if not paths:
            return

        self._entries.clear()
        self._copied_abs.clear()
        self._file_list.clear()

        all_ue_roots = set()

        for path in sorted(paths):
            self._copied_abs.append(path)
            rel = _relativise(path, self._version_dir)
            entry = EngineFile(
                path_custom=rel,
                path_default="",
                path_target=rel,
                local_name=os.path.basename(rel),
            )
            self._entries.append(entry)
            self._file_list.addItem(rel)

            ue_root = _find_engine_root(path)
            if ue_root:
                all_ue_roots.add(ue_root)

        # Collect module names and source file stems from user-picked files
        source_modules = set()
        source_stems = set()
        for entry in self._entries:
            rel = entry.path_custom
            mod = _module_name_from_path(rel)
            if mod:
                source_modules.add(mod)
            # Collect base name of source files (without extension) for .generated.h matching
            if rel.lower().startswith("engine/source/"):
                stem = os.path.splitext(os.path.basename(rel))[0]
                if stem:
                    source_stems.add(stem)

        # Auto-discover matching module binaries from any detected UE roots
        binary_count_total = 0
        intermediate_count_total = 0
        
        def _add_discovered(rel_path: str, abs_path: str, tag: str, counter: int) -> int:
            """Add a discovered file entry, skipping duplicates. Returns new count."""
            if any(e.path_custom == rel_path for e in self._entries):
                return counter
            entry = EngineFile(
                path_custom=rel_path,
                path_default="",
                path_target=rel_path,
                local_name=os.path.basename(rel_path),
            )
            self._entries.append(entry)
            self._copied_abs.append(abs_path)
            self._file_list.addItem(f"[{tag}] {rel_path}")
            return counter + 1

        for ue_root in all_ue_roots:
            for rel_path, abs_path in _discover_binaries(ue_root, source_modules):
                binary_count_total = _add_discovered(rel_path, abs_path, "bin", binary_count_total)
            for rel_path, abs_path in _discover_module_intermediates(ue_root, source_modules, source_stems):
                intermediate_count_total = _add_discovered(rel_path, abs_path, "int", intermediate_count_total)

        info_parts = [f"{len([e for e in self._entries if '[bin]' not in e.path_custom and '[int]' not in e.path_custom])} file(s) selected"]
        if binary_count_total > 0:
            info_parts.append(f"{binary_count_total} binary(ies) auto-discovered")
        if intermediate_count_total > 0:
            info_parts.append(f"{intermediate_count_total} intermediate(s) auto-discovered")
        self._info_label.setText("  \u00b7  ".join(info_parts))
        self._add_btn.setEnabled(len(self._entries) > 0)

    def _on_add(self):
        if not self._entries:
            self.reject()
        else:
            self.accept()

    def get_entries(self) -> List[EngineFile]:
        return self._entries

    def get_copied_paths(self) -> List[str]:
        """Absolute paths of browsed files (for copying into version dir)."""
        return self._copied_abs


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

        self._file_table = QTableWidget(0, 2)
        self._file_table.setHorizontalHeaderLabels(["#", "Engine Path"])
        self._file_table.horizontalHeader().setStretchLastSection(True)
        self._file_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._file_table.horizontalHeader().resizeSection(0, 30)
        self._file_table.verticalHeader().setVisible(False)
        self._file_table.setSelectionBehavior(QTableWidget.SelectRows)
        self._file_table.setSelectionMode(QTableWidget.SingleSelection)
        self._file_table.setMinimumHeight(120)
        self._file_table.currentCellChanged.connect(self._on_file_table_selection_changed)
        layout.addWidget(self._file_table, 1)

        file_btn_row = QHBoxLayout()
        self._file_add_btn = QPushButton("Add Files\u2026")
        self._file_add_btn.setEnabled(False)
        self._file_add_btn.clicked.connect(self._on_add_file)
        file_btn_row.addWidget(self._file_add_btn)

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
            self._file_remove_btn.setEnabled(False)
            return

        version = self._versions[row]
        self._ver_name.setText(version.engine_version)
        self._ue_ver.setText(version.unreal_version)

        # Rebuild parent combo excluding this version (no self-reference)
        self._parent_combo.blockSignals(True)
        current_parent = self._parent_combo.currentData()
        self._parent_combo.clear()
        self._parent_combo.addItem("(none)", "")
        for v in self._versions:
            if v.engine_version != version.engine_version:
                self._parent_combo.addItem(v.engine_version, v.engine_version)
        idx = self._parent_combo.findData(version.parent_version)
        self._parent_combo.setCurrentIndex(max(idx, 0))
        self._parent_combo.blockSignals(False)

        self._changelog.setPlainText(version.changelog)

        self._populate_file_table(version.files)

        self._clone_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)
        self._file_add_btn.setEnabled(True)
        self._file_remove_btn.setEnabled(False)

    def _on_file_table_selection_changed(self, row: int, column: int, prev_row: int, prev_column: int):
        """Enable the Remove button when a file row is selected."""
        has_selection = row >= 0
        version_row = self._version_list.currentRow()
        has_version = 0 <= version_row < len(self._versions)
        self._file_remove_btn.setEnabled(has_version and has_selection)

    def _clear_details(self):
        self._ver_name.clear()
        self._ue_ver.clear()
        self._parent_combo.setCurrentIndex(0)
        self._changelog.clear()
        self._file_table.setRowCount(0)

    def _populate_file_table(self, files: List[EngineFile]):
        self._file_table.setRowCount(len(files))
        for i, f in enumerate(files):
            engine_path = f.path_custom or f.path_target
            self._file_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self._file_table.setItem(i, 1, QTableWidgetItem(engine_path))
            item = self._file_table.item(i, 1)
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
        if dlg.exec() != QDialog.Accepted:
            return

        entries = dlg.get_entries()
        copied_paths = dlg.get_copied_paths()

        for i, entry in enumerate(entries):
            version.files.append(entry)

            # Copy browsed files into the version directory (if from outside)
            abs_path = copied_paths[i] if i < len(copied_paths) else ""
            if abs_path and not abs_path.startswith(ver_dir):
                rel = entry.path_custom
                if os.path.isabs(rel):
                    rel = os.path.basename(rel)
                    entry.path_custom = rel
                    entry.path_target = rel
                dest = os.path.join(ver_dir, rel)
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
