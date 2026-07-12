"""Patcher tab UI — manage engine versions, apply/revert engine files."""

import os
import threading
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLineEdit, QLabel, QProgressBar, QPlainTextEdit,
    QFileDialog, QMessageBox, QFrame, QSizePolicy,
)

from models import EngineInfo
from registry_helper import discover_ue_installations
from theme import (
    C_ACCENT_ORANGE, C_ACCENT, C_ACCENT_GREEN,
    C_TEXT_DIM, C_TEXT_BRIGHT, C_ACCENT_RED,
)
from patcher.version_io import discover_versions
from patcher.file_patcher import FilePatcher, PatchResult
from patcher.version_dialog import VersionManagerDialog


class PatcherTab(QWidget):
    """Patcher tab with combined UE selector, version management, and apply/revert controls."""

    _patch_finished = Signal(object, str)

    # Hidden style for the combo box (like plugin manager) — no dropdown arrow
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
        self._file_patcher = FilePatcher()
        self._patch_finished.connect(self._finish_apply)

        self._versions: List[EngineInfo] = []
        self._current_ue_root = ""
        self._is_working = False
        self._versions_root = os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "Versions"
        ))

        self._build_ui()
        self._discover_versions()
        self._discover_paths()

    # ── UI Setup ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(6)

        # ── Section 1: UE Folder Selector (combined combo + Browse) ──
        layout.addWidget(self._make_section_label("Unreal Engine Installation"))

        folder_row = QHBoxLayout()
        self._ue_folder_combo = QComboBox()
        self._ue_folder_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._ue_folder_combo.setStyleSheet(self._COMBO_QSS)
        self._ue_folder_combo.currentIndexChanged.connect(self._on_folder_selected)
        folder_row.addWidget(self._ue_folder_combo)

        self._browse_btn = QPushButton("Browse\u2026")
        self._browse_btn.clicked.connect(self._on_browse)
        folder_row.addWidget(self._browse_btn)

        layout.addLayout(folder_row)

        # ── Section 2: Version selector + applied indicator ──
        version_row = QHBoxLayout()

        ver_label = QLabel("Engine Version:")
        version_row.addWidget(ver_label)

        self._version_picker = QComboBox()
        self._version_picker.setMinimumWidth(200)
        self._version_picker.currentIndexChanged.connect(self._on_version_selected)
        version_row.addWidget(self._version_picker, 1)

        self._version_count_label = QLabel("")
        self._version_count_label.setAlignment(Qt.AlignRight)
        version_row.addWidget(self._version_count_label)

        layout.addLayout(version_row)

        # Applied version indicator
        self._applied_version_label = QLabel("")
        self._applied_version_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self._applied_version_label)

        # ── Section 3: Changelog ──
        layout.addWidget(self._make_section_label("Changelog"))

        self._changelog = QPlainTextEdit()
        self._changelog.setReadOnly(True)
        self._changelog.setPlaceholderText("Select a version to view its changelog...")
        self._changelog.setMinimumHeight(120)
        layout.addWidget(self._changelog, 1)

        # ── Section 4: Action buttons ──
        layout.addWidget(self._make_section_label("Actions"))

        # Operation overlay (progress + label)
        op_row = QHBoxLayout()
        self._operation_label = QLabel("")
        self._operation_label.setVisible(False)
        op_row.addWidget(self._operation_label)

        self._operation_progress = QProgressBar()
        self._operation_progress.setVisible(False)
        self._operation_progress.setMaximum(0)  # Indeterminate
        self._operation_progress.setFixedHeight(8)
        self._operation_progress.setTextVisible(False)
        op_row.addWidget(self._operation_progress, 1)
        layout.addLayout(op_row)

        action_row = QHBoxLayout()

        self._apply_custom_btn = QPushButton("  Apply Custom Engine")
        self._apply_custom_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._apply_custom_btn.setMinimumWidth(180)
        self._apply_custom_btn.clicked.connect(lambda: self._on_apply(True))
        action_row.addWidget(self._apply_custom_btn)

        self._apply_default_btn = QPushButton("  Revert to Default")
        self._apply_default_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._apply_default_btn.setMinimumWidth(160)
        self._apply_default_btn.clicked.connect(lambda: self._on_apply(False))
        action_row.addWidget(self._apply_default_btn)

        action_row.addWidget(self._make_vsep())

        self._manage_btn = QPushButton("Manage")
        self._manage_btn.clicked.connect(self._on_manage_versions)
        action_row.addWidget(self._manage_btn)

        action_row.addStretch(1)

        layout.addLayout(action_row)

        # ── Section 5: Status ──
        layout.addWidget(self._make_section_label("Status"))

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        self._status_label.setMinimumHeight(36)
        layout.addWidget(self._status_label)

        # Initial state
        self._update_apply_buttons()
        self._status_label.setStyleSheet(f"color: {C_TEXT_DIM};")
        self._status_label.setText("Ready.")

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

    # ── UE Path Discovery ──

    def _discover_paths(self):
        """Populate the UE folder combo from registry + filesystem locations."""
        self._ue_folder_combo.blockSignals(True)
        self._ue_folder_combo.clear()

        paths = discover_ue_installations()
        for p in paths:
            self._ue_folder_combo.addItem(p)
            idx = self._ue_folder_combo.count() - 1
            self._ue_folder_combo.setItemData(idx, p, Qt.UserRole)
            self._ue_folder_combo.setItemData(idx, p, Qt.ToolTipRole)

        self._ue_folder_combo.blockSignals(False)

        # Auto-select the first discovered installation
        if paths:
            self._ue_folder_combo.setCurrentIndex(0)
            self._on_folder_selected(0)

    def _on_folder_selected(self, index: int):
        if index < 0:
            return
        text = self._ue_folder_combo.currentText().strip()
        self._current_ue_root = self._ue_folder_combo.itemData(index, Qt.UserRole) or text
        self._on_ue_dir_changed()

    def _on_browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Unreal Engine Directory")
        if not path:
            return

        # Normalise and check if already in combo
        norm = os.path.normpath(path).lower()
        for i in range(self._ue_folder_combo.count()):
            stored = self._ue_folder_combo.itemData(i, Qt.UserRole)
            if stored and os.path.normpath(stored).lower() == norm:
                self._ue_folder_combo.setCurrentIndex(i)
                return

        self._ue_folder_combo.addItem(path)
        idx = self._ue_folder_combo.count() - 1
        self._ue_folder_combo.setItemData(idx, path, Qt.UserRole)
        self._ue_folder_combo.setItemData(idx, path, Qt.ToolTipRole)
        self._ue_folder_combo.setCurrentIndex(idx)

    def _on_ue_dir_changed(self):
        """Called when the user selects/browses a new UE directory."""
        ue_dir = self._current_ue_root
        if not ue_dir or not os.path.isdir(ue_dir):
            self._applied_version_label.setStyleSheet(f"color: {C_TEXT_DIM};")
            self._applied_version_label.setText("")
            self._update_apply_buttons()
            return

        # Detect what version is currently applied
        applied = FilePatcher.detect_applied_version(ue_dir, self._versions)
        if applied:
            self._applied_version_label.setStyleSheet(f"color: {C_ACCENT_GREEN}; font-weight: 600;")
            self._applied_version_label.setText(f"\u2714 Applied: {applied}")
        else:
            self._applied_version_label.setStyleSheet(f"color: {C_TEXT_DIM};")
            self._applied_version_label.setText("No version applied")

        self._update_apply_buttons()

    # ── Version Discovery ──

    def _discover_versions(self):
        self._version_picker.blockSignals(True)
        self._version_picker.clear()
        self._changelog.clear()

        try:
            self._versions = discover_versions(self._versions_root)
            if self._versions:
                for v in self._versions:
                    self._version_picker.addItem(f"{v.engine_version}  (UE {v.unreal_version})")
                self._version_picker.setCurrentIndex(len(self._versions) - 1)
                self._on_version_selected(len(self._versions) - 1)
                self._version_count_label.setText(f"{len(self._versions)} version(s) available")
            else:
                self._version_count_label.setText("No versions found")
                self._changelog.setPlainText(
                    "No engine versions discovered.\n\n"
                    f"Place version folders under:\n{self._versions_root}\n\n"
                    "Each folder should contain an info.dat file with version data."
                )

            self._update_apply_buttons()
            self._on_ue_dir_changed()

        except Exception as e:
            self._status_label.setStyleSheet(f"color: {C_ACCENT_RED};")
            self._status_label.setText(f"Error discovering versions: {e}")

        self._version_picker.blockSignals(False)

    # ── Event Handlers ──

    def _on_version_selected(self, idx: int):
        if idx < 0 or idx >= len(self._versions):
            self._changelog.setPlainText("No version selected.")
            return

        version = self._versions[idx]

        # Build changelog with parent inheritance
        text_parts = [
            f"=== Rock Pocket Engine {version.engine_version} ===  (UE {version.unreal_version})\n"
        ]
        if version.changelog:
            text_parts.append(f"Changelog:\n{version.changelog}\n")

        parent_version = version.parent_version
        visited = set()
        while parent_version and parent_version.lower() not in visited:
            visited.add(parent_version.lower())
            parent = next(
                (v for v in self._versions if v.engine_version.lower() == parent_version.lower()),
                None,
            )
            if not parent:
                break
            text_parts.append(f"\n--- Previous: {parent.engine_version} ---\n{parent.changelog}\n")
            parent_version = parent.parent_version

        self._changelog.setPlainText("".join(text_parts))
        self._changelog.verticalScrollBar().setValue(0)
        self._update_apply_buttons()

    def _on_apply(self, custom_engine: bool):
        idx = self._version_picker.currentIndex()
        if idx < 0 or idx >= len(self._versions):
            self._status_label.setStyleSheet(f"color: {C_ACCENT_RED};")
            self._status_label.setText("No version selected.")
            return

        version = self._versions[idx]
        ue_dir = self._current_ue_root

        if not ue_dir or not os.path.isdir(ue_dir):
            self._status_label.setStyleSheet(f"color: {C_ACCENT_RED};")
            self._status_label.setText("Invalid UE directory. Please select a valid Unreal Engine installation.")
            return

        if custom_engine:
            msg = (
                f"This will copy engine files to:\n{ue_dir}\n\n"
                f"Version: {version.engine_version} (UE {version.unreal_version})\n\n"
                "This modifies your UE installation. Continue?"
            )
        else:
            msg = (
                f"This will revert engine files to defaults at:\n{ue_dir}\n\n"
                f"Version: {version.engine_version} (UE {version.unreal_version})\n\n"
                "This modifies your UE installation. Continue?"
            )

        reply = QMessageBox.question(
            self,
            "Apply Custom Engine?" if custom_engine else "Revert to Default?",
            msg,
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._do_apply(custom_engine, version, ue_dir)

    def _do_apply(self, custom_engine: bool, version: EngineInfo, ue_dir: str):
        self._is_working = True
        self._set_buttons_enabled(False)

        self._operation_label.setText("Applying custom engine..." if custom_engine else "Reverting to default...")
        self._operation_label.setVisible(True)
        self._operation_progress.setVisible(True)

        ver_name = version.engine_version

        def work():
            try:
                if custom_engine:
                    result = self._file_patcher.apply_custom(
                        version, self._versions, ue_dir, self._versions_root, False,
                    )
                else:
                    result = self._file_patcher.apply_default(
                        version, self._versions, ue_dir, self._versions_root, False,
                    )
            except Exception as e:
                result = PatchResult(success=False, message=str(e))

            self._patch_finished.emit(result, ver_name)

        thread = threading.Thread(target=work, daemon=True)
        thread.start()

    def _finish_apply(self, result: PatchResult, version_name: str):
        self._operation_label.setVisible(False)
        self._operation_progress.setVisible(False)
        self._is_working = False
        self._set_buttons_enabled(True)

        if result.success:
            self._status_label.setStyleSheet(f"color: {C_ACCENT_GREEN};")
            self._status_label.setText(f"Success: {result.message}")
            self._on_ue_dir_changed()  # Refresh applied indicator (reads marker)
        else:
            self._status_label.setStyleSheet(f"color: {C_ACCENT_RED};")
            self._status_label.setText(f"Failed: {result.message}")

    def _on_manage_versions(self):
        """Open the Version Manager dialog."""
        dlg = VersionManagerDialog(self, versions_root=self._versions_root)
        dlg.exec()
        # Re-discover versions regardless of changes (handles external edits too)
        self._discover_versions()

    # ── Helpers ──

    def _update_apply_buttons(self):
        has_version = 0 <= self._version_picker.currentIndex() < len(self._versions)
        has_dir = bool(self._current_ue_root) and os.path.isdir(self._current_ue_root)
        self._apply_custom_btn.setEnabled(has_version and has_dir and not self._is_working)
        self._apply_default_btn.setEnabled(has_version and has_dir and not self._is_working)

    def _set_buttons_enabled(self, enabled: bool):
        self._apply_custom_btn.setEnabled(enabled)
        self._apply_default_btn.setEnabled(enabled)
        self._manage_btn.setEnabled(enabled)
        self._browse_btn.setEnabled(enabled)
        self._ue_folder_combo.setEnabled(enabled)
        self._version_picker.setEnabled(enabled)
