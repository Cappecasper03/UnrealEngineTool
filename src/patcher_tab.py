"""Patcher tab UI — manage engine versions, apply/revert engine files."""

import os
import threading
from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QProgressBar, QPlainTextEdit,
    QFileDialog, QMessageBox, QFrame, QSizePolicy,
)

from models import EngineInfo
from registry_helper import discover_ue_installations
from theme import (
    C_ACCENT, C_ACCENT_GREEN,
    C_TEXT_DIM, C_TEXT_BRIGHT, C_ACCENT_RED,
    C_CARD, C_CARD_BORDER,
)
from patcher.patch_io import discover_patches
from patcher.file_patcher import FilePatcher, PatchResult
from patcher.patch_dialog import PatchManagerDialog
from logger import get_logger

log = get_logger("patcher_tab")


def _make_section_card(title: str) -> tuple:
    """Create a styled section card with header.

    Returns (card_frame, inner_layout) for adding widgets to.
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


class PatcherTab(QWidget):
    """Patcher tab with combined UE selector, version management, and apply/revert controls."""

    _patch_finished = Signal(object, str)

    # Hidden style for the combo box (no dropdown arrow)
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

        self._patches: List[EngineInfo] = []
        self._current_ue_root = ""
        self._is_working = False
        self._patches_root = os.path.normpath(
            os.path.join(
                os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                "UnrealEngineTool", "patches",
            )
        )

        self._build_ui()
        self._discover_patches()
        self._discover_paths()

    # ── UI Setup ──

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(10)

        # ════════════════════════════════════════════
        # CARD 1: Installation
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
        layout.addWidget(card1)

        # ════════════════════════════════════════════
        # CARD 2: Patch
        # ════════════════════════════════════════════
        card2, c2 = _make_section_card("Patch")

        # Patch selector row
        patch_row = QHBoxLayout()
        patch_row.setSpacing(6)

        patch_label = QLabel("Patch:")
        patch_label.setStyleSheet("background: transparent;")
        patch_row.addWidget(patch_label)

        self._patch_picker = QComboBox()
        self._patch_picker.setMinimumWidth(200)
        self._patch_picker.setStyleSheet(self._COMBO_QSS)
        self._patch_picker.currentIndexChanged.connect(self._on_patch_selected)
        patch_row.addWidget(self._patch_picker, 1)

        self._manage_btn = QPushButton("Manage")
        self._manage_btn.setObjectName("toolBtn")
        self._manage_btn.clicked.connect(self._on_manage_patches)
        patch_row.addWidget(self._manage_btn)

        self._patch_count_label = QLabel("")
        self._patch_count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._patch_count_label.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 12px; background: transparent;")
        patch_row.addWidget(self._patch_count_label)

        c2.addLayout(patch_row)

        # Applied version indicator
        self._applied_version_label = QLabel("")
        self._applied_version_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._applied_version_label.setStyleSheet("background: transparent; font-size: 12px;")
        c2.addWidget(self._applied_version_label)

        layout.addWidget(card2)

        # ════════════════════════════════════════════
        # CARD 3: Changelog
        # ════════════════════════════════════════════
        card3, c3 = _make_section_card("Changelog")
        c3.setContentsMargins(12, 4, 12, 10)
        c3.setSpacing(4)

        self._changelog = QPlainTextEdit()
        self._changelog.setReadOnly(True)
        self._changelog.setPlaceholderText("Select a patch to view its changelog\u2026")
        self._changelog.setMinimumHeight(100)
        c3.addWidget(self._changelog, 1)

        layout.addWidget(card3, 1)

        # ════════════════════════════════════════════
        # CARD 4: Actions
        # ════════════════════════════════════════════
        card4, c4 = _make_section_card("Actions")

        # Operation overlay (hidden until active)
        op_row = QHBoxLayout()
        self._operation_label = QLabel("")
        self._operation_label.setVisible(False)
        self._operation_label.setStyleSheet("background: transparent;")
        op_row.addWidget(self._operation_label)

        self._operation_progress = QProgressBar()
        self._operation_progress.setVisible(False)
        self._operation_progress.setMaximum(0)  # Indeterminate
        self._operation_progress.setFixedHeight(6)
        self._operation_progress.setTextVisible(False)
        op_row.addWidget(self._operation_progress, 1)
        c4.addLayout(op_row)

        # Action buttons row
        action_row = QHBoxLayout()
        action_row.setSpacing(6)

        self._apply_custom_btn = QPushButton("Apply Custom Engine")
        self._apply_custom_btn.setProperty("class", "primary")
        self._apply_custom_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_custom_btn.setMinimumWidth(180)
        self._apply_custom_btn.clicked.connect(lambda: self._on_apply(True))
        action_row.addWidget(self._apply_custom_btn)

        self._apply_default_btn = QPushButton("Revert to Default")
        self._apply_default_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._apply_default_btn.setMinimumWidth(160)
        self._apply_default_btn.clicked.connect(lambda: self._on_apply(False))
        action_row.addWidget(self._apply_default_btn)

        action_row.addStretch(1)

        c4.addLayout(action_row)

        layout.addWidget(card4)

        # ════════════════════════════════════════════
        # Status bar (below cards, no card wrapper)
        # ════════════════════════════════════════════
        self._status_label = QLabel("Ready.")
        self._status_label.setWordWrap(True)
        self._status_label.setMinimumHeight(24)
        self._status_label.setStyleSheet(f"color: {C_TEXT_DIM}; font-size: 12px; padding: 2px 4px; background: transparent;")
        layout.addWidget(self._status_label)

        # Initial state
        self._update_apply_buttons()

    # ── UE Path Discovery ──

    def _discover_paths(self):
        """Populate the UE folder combo from registry + filesystem locations."""
        self._ue_folder_combo.blockSignals(True)
        self._ue_folder_combo.clear()

        paths = discover_ue_installations()
        for p in paths:
            self._ue_folder_combo.addItem(p)
            idx = self._ue_folder_combo.count() - 1
            self._ue_folder_combo.setItemData(idx, p, Qt.ItemDataRole.UserRole)
            self._ue_folder_combo.setItemData(idx, p, Qt.ItemDataRole.ToolTipRole)

        self._ue_folder_combo.blockSignals(False)

        # Auto-select the first discovered installation
        if paths:
            self._ue_folder_combo.setCurrentIndex(0)
            self._on_folder_selected(0)

    def _on_folder_selected(self, index: int):
        if index < 0:
            return
        text = self._ue_folder_combo.currentText().strip()
        self._current_ue_root = self._ue_folder_combo.itemData(index, Qt.ItemDataRole.UserRole) or text
        self._on_ue_dir_changed()

    def _on_browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Unreal Engine Directory")
        if not path:
            return

        # Normalise and check if already in combo
        norm = os.path.normpath(path).lower()
        for i in range(self._ue_folder_combo.count()):
            stored = self._ue_folder_combo.itemData(i, Qt.ItemDataRole.UserRole)
            if stored and os.path.normpath(stored).lower() == norm:
                self._ue_folder_combo.setCurrentIndex(i)
                return

        self._ue_folder_combo.addItem(path)
        idx = self._ue_folder_combo.count() - 1
        self._ue_folder_combo.setItemData(idx, path, Qt.ItemDataRole.UserRole)
        self._ue_folder_combo.setItemData(idx, path, Qt.ItemDataRole.ToolTipRole)
        self._ue_folder_combo.setCurrentIndex(idx)

    def _on_ue_dir_changed(self):
        """Called when the user selects/browses a new UE directory."""
        ue_dir = self._current_ue_root
        if not ue_dir or not os.path.isdir(ue_dir):
            self._applied_version_label.setStyleSheet(f"color: {C_TEXT_DIM}; background: transparent;")
            self._applied_version_label.setText("")
            self._update_apply_buttons()
            return

        # Detect what patch is currently applied
        applied = FilePatcher.detect_applied_version(ue_dir, self._patches)
        if applied:
            self._applied_version_label.setStyleSheet(
                f"color: {C_ACCENT_GREEN}; font-weight: 600; background: transparent;"
            )
            self._applied_version_label.setText(f"\u2714 Applied: {applied}")
        else:
            self._applied_version_label.setStyleSheet(
                f"color: {C_TEXT_DIM}; background: transparent;"
            )
            self._applied_version_label.setText("No patch applied")

        self._update_apply_buttons()

    # ── Patch Discovery ──

    def _discover_patches(self):
        self._patch_picker.blockSignals(True)
        self._patch_picker.clear()
        self._changelog.clear()

        try:
            self._patches = discover_patches(self._patches_root)
            if self._patches:
                log.info("Discovered %d patch(es) from %s", len(self._patches), self._patches_root)
                for p in self._patches:
                    self._patch_picker.addItem(f"{p.patch_name}  ({p.unreal_dir})" if p.unreal_dir else p.patch_name)
                self._patch_picker.setCurrentIndex(len(self._patches) - 1)
                self._on_patch_selected(len(self._patches) - 1)
                self._patch_count_label.setText(f"{len(self._patches)} patch(es)")
            else:
                self._patch_count_label.setText("No patches found")
                self._changelog.setPlainText(
                    "No patches discovered.\n\n"
                    f"Place patch folders under:\n{self._patches_root}\n\n"
                    "Each folder should contain an info.dat file with patch data."
                )

            self._update_apply_buttons()
            self._on_ue_dir_changed()

        except Exception as e:
            log.error("Error discovering patches from %s: %s", self._patches_root, e)
            self._status_label.setStyleSheet(f"color: {C_ACCENT_RED}; font-size: 12px;")
            self._status_label.setText(f"Error discovering patches: {e}")

        self._patch_picker.blockSignals(False)

    # ── Event Handlers ──

    def _on_patch_selected(self, idx: int):
        if idx < 0 or idx >= len(self._patches):
            self._changelog.setPlainText("No patch selected.")
            return

        patch = self._patches[idx]

        # Build changelog with parent inheritance
        text_parts = []
        if patch.changelog:
            text_parts.append(f"{patch.changelog}\n")

        parent_patch = patch.parent_patch
        visited = set()
        while parent_patch and parent_patch.lower() not in visited:
            visited.add(parent_patch.lower())
            parent = next(
                (p for p in self._patches if p.patch_name.lower() == parent_patch.lower()),
                None,
            )
            if not parent:
                break
            text_parts.append(f"\n--- Previous: {parent.patch_name} ---\n{parent.changelog}\n")
            parent_patch = parent.parent_patch

        self._changelog.setPlainText("".join(text_parts))
        self._changelog.verticalScrollBar().setValue(0)
        self._update_apply_buttons()

    def _on_apply(self, custom_engine: bool):
        idx = self._patch_picker.currentIndex()
        if idx < 0 or idx >= len(self._patches):
            self._status_label.setStyleSheet(f"color: {C_ACCENT_RED}; font-size: 12px;")
            self._status_label.setText("No patch selected.")
            return

        patch = self._patches[idx]
        ue_dir = self._current_ue_root

        if not ue_dir or not os.path.isdir(ue_dir):
            self._status_label.setStyleSheet(f"color: {C_ACCENT_RED}; font-size: 12px;")
            self._status_label.setText("Invalid UE directory. Please select a valid Unreal Engine installation.")
            return

        if custom_engine:
            msg = (
                f"This will copy engine files to:\n{ue_dir}\n\n"
                f"Patch: {patch.patch_name} (UE {patch.unreal_version})\n\n"
                "This modifies your UE installation. Continue?"
            )
        else:
            msg = (
                f"This will revert engine files to defaults at:\n{ue_dir}\n\n"
                f"Patch: {patch.patch_name} (UE {patch.unreal_version})\n\n"
                "This modifies your UE installation. Continue?"
            )

        reply = QMessageBox.question(
            self,
            "Apply Custom Engine?" if custom_engine else "Revert to Default?",
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._do_apply(custom_engine, patch, ue_dir)

    def _do_apply(self, custom_engine: bool, patch: EngineInfo, ue_dir: str):
        self._is_working = True
        self._set_buttons_enabled(False)

        action_label = "custom" if custom_engine else "default"
        log.info("GUI apply start: %s patch=%s target=%s", action_label, patch.patch_name, ue_dir)

        self._operation_label.setText("Applying custom engine\u2026" if custom_engine else "Reverting to default\u2026")
        self._operation_label.setVisible(True)
        self._operation_progress.setVisible(True)

        p_name = patch.patch_name

        def work():
            try:
                if custom_engine:
                    result = self._file_patcher.apply_custom(
                        patch, self._patches, ue_dir, self._patches_root, False,
                    )
                else:
                    result = self._file_patcher.apply_default(
                        patch, self._patches, ue_dir, self._patches_root, False,
                    )
            except Exception as e:
                result = PatchResult(success=False, message=str(e))

            self._patch_finished.emit(result, p_name)

        thread = threading.Thread(target=work, daemon=True)
        thread.start()

    def _finish_apply(self, result: PatchResult, patch_name: str):
        self._operation_label.setVisible(False)
        self._operation_progress.setVisible(False)
        self._is_working = False
        self._set_buttons_enabled(True)

        if result.success:
            log.info("GUI apply result: success — %s", result.message)
            self._status_label.setStyleSheet(f"color: {C_ACCENT_GREEN}; font-size: 12px;")
            self._status_label.setText(f"Success: {result.message}")
            self._on_ue_dir_changed()  # Refresh applied indicator (reads marker)
        else:
            log.error("GUI apply result: failed — %s", result.message)
            self._status_label.setStyleSheet(f"color: {C_ACCENT_RED}; font-size: 12px;")
            self._status_label.setText(f"Failed: {result.message}")

    def _on_manage_patches(self):
        """Open the Patch Manager dialog."""
        dlg = PatchManagerDialog(self, versions_root=self._patches_root)
        dlg.exec()
        # Re-discover patches regardless of changes (handles external edits too)
        self._discover_patches()

    # ── Helpers ──

    def _update_apply_buttons(self):
        has_version = 0 <= self._patch_picker.currentIndex() < len(self._patches)
        has_dir = bool(self._current_ue_root) and os.path.isdir(self._current_ue_root)
        self._apply_custom_btn.setEnabled(has_version and has_dir and not self._is_working)
        self._apply_default_btn.setEnabled(has_version and has_dir and not self._is_working)

    def _set_buttons_enabled(self, enabled: bool):
        self._apply_custom_btn.setEnabled(enabled)
        self._apply_default_btn.setEnabled(enabled)
        self._manage_btn.setEnabled(enabled)
        self._browse_btn.setEnabled(enabled)
        self._ue_folder_combo.setEnabled(enabled)
        self._patch_picker.setEnabled(enabled)
