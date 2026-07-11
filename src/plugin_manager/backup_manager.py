"""Handles backup/restore and template save/load for plugin EnabledByDefault states."""

import os
from typing import List, Set

from models import PluginData


class BackupManager:
    """Backup/restore and template save/load for plugin states."""

    def save_backup(self, file_path: str, plugins: List[PluginData], ue_root: str):
        """Save a backup of all currently enabled-by-default plugins (absolute paths)."""
        lines = []
        plugins_root = os.path.join(ue_root, "Engine", "Plugins")
        for p in plugins:
            if p.enabled_by_default:
                lines.append(os.path.join(plugins_root, p.relative_path))
        with open(file_path, "w") as f:
            f.write("\n".join(lines) + "\n")

    def save_template(self, file_path: str, plugins: List[PluginData]):
        """Save a template of enabled-by-default plugins (relative paths)."""
        lines = [p.relative_path for p in plugins if p.enabled_by_default]
        with open(file_path, "w") as f:
            f.write("\n".join(lines) + "\n")

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
            # Extract relative path if it's absolute
            if trimmed.startswith(plugins_root):
                rel = os.path.relpath(trimmed, plugins_root)
                enabled_paths.add(rel)
            else:
                enabled_paths.add(trimmed)

        count = 0
        for p in plugins:
            if p.relative_path in enabled_paths:
                p.enabled_by_default = True
                count += 1
            else:
                p.enabled_by_default = False
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
        return count
