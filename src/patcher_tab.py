"""Patcher tab UI — manage engine versions, apply/revert engine files."""

import os
import threading
from typing import List, Optional

from PySide6.QtCore import Qt, Signal, QObject, QThread
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


class PatcherTab(QWidget):
    """Patcher tab with version management, changelog, and apply/revert controls."""

    def __init__(self):
        super().__init__()
        self._version_io = None  # We use module-level functions instead
        self._file_patcher = FilePatcher()

        self._versions: List[EngineInfo] = []
        self._source_mode = False
        self._is_working = False
        self._versions_root = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "Versions"
        )

        self._build_ui()
        self._discover_versions()
        self._refresh_detected_paths()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(6)

        # ── Section 1: Target UE Directory + Version ──
        layout.addWidget(self._make_section_label("Target Installation"))

        top_row = QHBoxLayout()

        dir_label = QLabel("UE Directory:")
        top_row.addWidget(dir_label)

        self._engine_dir = QLineEdit()
        self._engine_dir.setPlaceholderText("Path to Unreal Engine installation...")
        self._engine_dir.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._engine_dir.textChanged.connect(self._update_apply_buttons)
        top_row.addWidget(self._engine_dir, 1)

        ver_label = QLabel("Version:")
        top_row.addWidget(ver_label)

        self._version_picker = QComboBox()
        self._version_picker.setFixedWidth(200)
        self._version_picker.currentIndexChanged.connect(self._on_version_selected)
        top_row.addWidget(self._version_picker)

        self._browse_btn = QPushButton("Browse\u2026")
        self._browse_btn.clicked.connect(self._on_browse_dir)
        top_row.addWidget(self._browse_btn)

        self._settings_btn = QPushButton("Settings")
        self._settings_btn.clicked.connect(self._on_settings)
        top_row.addWidget(self._settings_btn)

        self._info_btn = QPushButton("Info")
        self._info_btn.clicked.connect(self._on_info)
        top_row.addWidget(self._info_btn)

        layout.addLayout(top_row)

        # Auto-detect row
        detect_row = QHBoxLayout()
        self._detect_combo = QComboBox()
        self._detect_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._detect_combo.addItem("(detect installations...)")
        detect_row.addWidget(self._detect_combo)

        self._detect_btn = QPushButton("Set")
        self._detect_btn.setFixedWidth(60)
        self._detect_btn.clicked.connect(self._on_detect_set)
        detect_row.addWidget(self._detect_btn)

        self._refresh_detect_btn = QPushButton("Refresh")
        self._refresh_detect_btn.setFixedWidth(80)
        self._refresh_detect_btn.clicked.connect(self._refresh_detected_paths)
        detect_row.addWidget(self._refresh_detect_btn)

        layout.addLayout(detect_row)

        # ── Section 2: Applied version indicator ──
        indicator_row = QHBoxLayout()
        self._applied_version_label = QLabel("")
        self._applied_version_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        indicator_row.addWidget(self._applied_version_label)

        self._version_count_label = QLabel("")
        self._version_count_label.setAlignment(Qt.AlignRight)
        indicator_row.addWidget(self._version_count_label)

        layout.addLayout(indicator_row)

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

        self._source_mode_btn = QPushButton("Engine Mode")
        self._source_mode_btn.setCheckable(True)
        self._source_mode_btn.clicked.connect(self._toggle_source_mode)
        action_row.addWidget(self._source_mode_btn)

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

    # ── Version Discovery ──

    def _discover_versions(self):
        self._version_picker.clear()
        self._version_picker.addItem("(none)")
        self._version_picker.setCurrentIndex(0)
        self._changelog.clear()

        try:
            self._versions = discover_versions(self._versions_root)
            if self._versions:
                self._version_picker.clear()
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
            self._status_label.setStyleSheet(f"color: {C_TEXT_DIM};")
            self._status_label.setText(f"Ready \u2014 {len(self._versions)} engine version(s) loaded.")
            self._update_applied_indicator()

        except Exception as e:
            self._status_label.setStyleSheet(f"color: {C_ACCENT_RED};")
            self._status_label.setText(f"Error discovering versions: {e}")

    # ── Event Handlers ──

    def _on_version_selected(self, idx: int):
        if idx < 0 or idx >= len(self._versions):
            self._changelog.setPlainText("No version selected.")
            self._update_applied_indicator()
            return

        version = self._versions[idx]

        if version.unreal_dir:
            self._engine_dir.setText(version.unreal_dir)

        # Build changelog with parent inheritance
        text_parts = [
            f"=== Rock Pocket Engine {version.engine_version} ===  (UE {version.unreal_version})\n"
        ]

        if version.changelog:
            text_parts.append(f"Changelog:\n{version.changelog}\n")

        # Add parent changelogs
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
        self._update_applied_indicator()

    def _on_browse_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Unreal Engine Installation Directory")
        if path:
            self._engine_dir.setText(path)

    # ── Registry / Auto-detect ──

    def _refresh_detected_paths(self):
        """Re-scan registry and filesystem for UE installations and populate the detect combo."""
        self._detect_combo.clear()
        self._detect_combo.addItem("(select an installation...)")

        paths = discover_ue_installations()
        for p in paths:
            self._detect_combo.addItem(p)

        if paths:
            self._detect_combo.addItem("")
            self._detect_combo.addItem("Browse for a different folder... (opens file dialog)")
            self._detect_combo.currentIndexChanged.connect(self._on_detect_combo_changed)

    def _on_detect_combo_changed(self, idx: int):
        """Handle selection from the detect combo — 'Browse...' entry opens a file dialog."""
        if idx <= 0:
            return
        text = self._detect_combo.currentText().strip()

        # Check if user selected the "Browse..." placeholder
        if "Browse" in text:
            path = QFileDialog.getExistingDirectory(self, "Select Unreal Engine Installation Directory")
            if path:
                self._engine_dir.setText(path)
            # Reset combo to the placeholder
            self._detect_combo.setCurrentIndex(0)
            return

        if os.path.isdir(text):
            self._engine_dir.setText(text)
            self._engine_dir.setCursorPosition(len(text))

    def _on_detect_set(self):
        """Set the engine dir to the currently selected detected path."""
        idx = self._detect_combo.currentIndex()
        if idx <= 0:
            return
        text = self._detect_combo.currentText().strip()
        if os.path.isdir(text):
            self._engine_dir.setText(text)
            self._engine_dir.setCursorPosition(len(text))
        else:
            self._detect_combo.setCurrentIndex(0)

    def _on_apply(self, custom_engine: bool):
        idx = self._version_picker.currentIndex()
        if idx < 0 or idx >= len(self._versions):
            self._status_label.setStyleSheet(f"color: {C_ACCENT_RED};")
            self._status_label.setText("No version selected.")
            return

        version = self._versions[idx]
        ue_dir = self._engine_dir.text().strip()

        if not ue_dir or not os.path.isdir(ue_dir):
            self._status_label.setStyleSheet(f"color: {C_ACCENT_RED};")
            self._status_label.setText("Invalid UE directory. Please select a valid Unreal Engine installation.")
            return

        action_name = "apply custom engine" if custom_engine else "revert to default"
        mode_name = "Source files only" if self._source_mode else "Full engine files"

        if custom_engine:
            msg = (
                f"This will copy engine files to:\n{ue_dir}\n\n"
                f"Version: {version.engine_version} (UE {version.unreal_version})\n"
                f"Mode: {mode_name}\n\n"
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

        # Run in background thread
        def work():
            try:
                if custom_engine:
                    result = self._file_patcher.apply_custom(
                        version, self._versions, ue_dir, self._versions_root, self._source_mode,
                    )
                else:
                    result = self._file_patcher.apply_default(
                        version, self._versions, ue_dir, self._versions_root, self._source_mode,
                    )
            except Exception as e:
                result = PatchResult(success=False, message=str(e))

            # Call finish on main thread via signal
            self._finish_apply(result, version.engine_version)

        QThread.start(QThread(target=work))

    def _finish_apply(self, result: PatchResult, version_name: str):
        self._operation_label.setVisible(False)
        self._operation_progress.setVisible(False)
        self._is_working = False
        self._set_buttons_enabled(True)

        if result.success:
            self._status_label.setStyleSheet(f"color: {C_ACCENT_GREEN};")
            self._status_label.setText(f"Success: {result.message}")
            self._update_applied_indicator(version_name)
        else:
            self._status_label.setStyleSheet(f"color: {C_ACCENT_RED};")
            self._status_label.setText(f"Failed: {result.message}")

    def _on_settings(self):
        version_names = ", ".join(v.engine_version for v in self._versions) if self._versions else "(none)"
        QMessageBox.information(
            self,
            "Version Settings",
            "Full version management (add/edit/remove versions and file mappings)\n"
            "will be available in an upcoming release.\n\n"
            f"Versions found: {version_names}\n\n"
            f"Version files stored at:\n{self._versions_root}",
        )

    def _on_info(self):
        mode = "Source Mode (copies .h/.cpp files only)" if self._source_mode else "Engine Mode (copies binaries and all files)"
        QMessageBox.information(
            self,
            "About Patcher",
            "Unreal Engine Tool \u2014 Patcher\n\n"
            "Applies custom engine files (Rock Pocket Engine) to a UE installation.\n\n"
            f"Current mode: {mode}\n\n"
            "Engine Mode: Copies binaries (.dll, .exe, .pdb, etc.)\n"
            "Source Mode: Copies source files (.h, .cpp) only\n\n"
            "Versions support parent inheritance \u2014 a child version's files override the parent's.\n\n"
            "Based on the RPEngineInstaller reference implementation.",
        )

    def _toggle_source_mode(self):
        self._source_mode = self._source_mode_btn.isChecked()
        self._source_mode_btn.setText("Source Mode" if self._source_mode else "Engine Mode")
        self._update_apply_buttons()

    # ── Helpers ──

    def _update_apply_buttons(self):
        has_version = 0 <= self._version_picker.currentIndex() < len(self._versions)
        has_dir = bool(self._engine_dir.text().strip()) and os.path.isdir(self._engine_dir.text().strip())
        self._apply_custom_btn.setEnabled(has_version and has_dir and not self._is_working)
        self._apply_default_btn.setEnabled(has_version and has_dir and not self._is_working)

    def _set_buttons_enabled(self, enabled: bool):
        self._apply_custom_btn.setEnabled(enabled)
        self._apply_default_btn.setEnabled(enabled)
        self._source_mode_btn.setEnabled(enabled)
        self._browse_btn.setEnabled(enabled)
        self._settings_btn.setEnabled(enabled)
        self._info_btn.setEnabled(enabled)
        self._engine_dir.setEnabled(enabled)
        self._version_picker.setEnabled(enabled)

    def _update_applied_indicator(self, version_name: Optional[str] = None):
        if version_name:
            self._applied_version_label.setStyleSheet(f"color: {C_ACCENT_GREEN}; font-weight: 600;")
            self._applied_version_label.setText(f"\u2714 Applied: {version_name}")
        else:
            self._applied_version_label.setStyleSheet(f"color: {C_TEXT_DIM};")
            self._applied_version_label.setText("No version applied")
