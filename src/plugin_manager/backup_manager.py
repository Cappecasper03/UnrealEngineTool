"""Handles backup/restore and template save/load for plugin EnabledByDefault states."""

import os
from typing import List, Set

from logger import get_logger
from models import PluginData

log = get_logger("backup_manager")


class BackupManager:
    """Backup/restore and template save/load for plugin states."""

    def save_backup(self, file_path: str, plugins: List[PluginData], ue_root: str):
        """Save a backup of all currently enabled-by-default plugins (absolute paths)."""
        lines = []
        plugins_root = os.path.join(ue_root, "Engine", "Plugins")
        enabled = [p for p in plugins if p.enabled_by_default]
        for p in enabled:
            lines.append(os.path.join(plugins_root, p.relative_path))
        with open(file_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        log.info("save_backup: %d plugin(s) saved to %s", len(enabled), file_path)

    def save_template(self, file_path: str, plugins: List[PluginData]):
        """Save a template of enabled-by-default plugins (relative paths)."""
        lines = [p.relative_path for p in plugins if p.enabled_by_default]
        with open(file_path, "w") as f:
            f.write("\n".join(lines) + "\n")
        log.info("save_template: %d plugin(s) saved to %s", len(lines), file_path)

    def load_backup(self, file_path: str, plugins: List[PluginData], ue_root: str) -> int:
        """Load a backup file and apply EnabledByDefault state. Returns restore count."""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Backup file not found: {file_path}")

        with open(file_path, "r") as f:
            lines = f.readlines()

        plugins_root = os.path.join(ue_root, "Engine", "Plugins")
        enabled_paths: Set[str] = set()

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                continue
            if trimmed.startswith(plugins_root):
                rel = os.path.relpath(trimmed, plugins_root).replace("\\", "/")
                enabled_paths.add(rel)
            else:
                enabled_paths.add(trimmed.replace("\\", "/"))

        count = 0
        for p in plugins:
            if p.relative_path in enabled_paths:
                p.enabled_by_default = True
                count += 1
            else:
                p.enabled_by_default = False
        log.info("load_backup: restored state for %d plugin(s) from %s", count, file_path)
        return count

    def load_template(self, file_path: str, plugins: List[PluginData]) -> int:
        """Load a template file (relative paths) and apply EnabledByDefault state."""
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Template file not found: {file_path}")

        with open(file_path, "r") as f:
            lines = f.readlines()

        enabled_paths: Set[str] = {line.strip() for line in lines if line.strip()}

        count = 0
        for p in plugins:
            if p.relative_path in enabled_paths:
                p.enabled_by_default = True
                count += 1
            else:
                p.enabled_by_default = False
        log.info("load_template: applied template for %d plugin(s) from %s", count, file_path)
        return count

    def apply_minimal(self, plugins: List[PluginData]) -> int:
        """Apply 'Minimal' preset: only essential plugins remain enabled."""
        minimal: Set[str] = {
            "AISupport", "ContentBrowserAssetDataSource", "ContentBrowserClassDataSource",
            "CurveEditorTools", "TextureFormateOodle", "OodleData",
            "PluginBrowser", "PluginUtils", "PropertyAccessEditor",
        }
        count = 0
        for p in plugins:
            if p.name in minimal:
                p.enabled_by_default = True
                count += 1
            else:
                p.enabled_by_default = False
        log.info("apply_minimal: %d plugin(s) remain enabled", count)
        return count
