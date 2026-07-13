"""Applies changes to .uplugin files on disk: toggles EnabledByDefault and Installed."""

import json
import os
from typing import Dict, List, Optional

from models import PluginData


class PatchResult:
    def __init__(self):
        self.modified_count: int = 0
        self.error_count: int = 0
        self.errors: List[str] = []


class UPluginPatcher:
    """Writes modified plugin states back to disk."""

    def apply_changes(
        self,
        plugins: List[PluginData],
        original_plugins: List[PluginData],
        plugins_root: str,
    ) -> PatchResult:
        """Write all modified plugins back to disk."""
        result = PatchResult()
        original_lookup: Dict[str, PluginData] = {}

        for orig in original_plugins:
            if orig.name not in original_lookup:
                original_lookup[orig.name] = orig

        for plugin in plugins:
            if not plugin.is_modified:
                continue

            try:
                self._patch_file(plugin, original_lookup.get(plugin.name))
                result.modified_count += 1
            except Exception as e:
                result.error_count += 1
                result.errors.append(f"{plugin.name}: {e}")

        return result

    def _patch_file(self, plugin: PluginData, original: Optional[PluginData]):
        file_path = plugin.full_path
        self._unset_readonly(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["EnabledByDefault"] = plugin.enabled_by_default
        data["Installed"] = plugin.installed

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

    @staticmethod
    def _unset_readonly(file_path: str):
        if os.path.isfile(file_path):
            attrs = os.stat(file_path).st_mode
            if not (attrs & 0o200):  # Not writable
                os.chmod(file_path, attrs | 0o200)
