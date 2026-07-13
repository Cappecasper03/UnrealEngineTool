"""Applies changes to .uplugin files on disk: toggles EnabledByDefault only."""

import json
import os
from typing import Dict, List, Optional

from logger import get_logger
from models import PluginData

log = get_logger("plugin_patcher")


class PatchResult:
    def __init__(self):
        self.modified_count: int = 0
        self.error_count: int = 0
        self.errors: List[str] = []


class UPluginPatcher:
    """Writes modified plugin states back to disk.

    Only EnabledByDefault is user-toggleable — Installed is read-only
    metadata from the .uplugin file.
    """

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

        modified_names = [p.name for p in plugins if p.is_modified]
        log.info("apply_changes: %d plugin(s) modified out of %d — %s",
                 len(modified_names), len(plugins),
                 modified_names if modified_names else "(none)")

        for plugin in plugins:
            if not plugin.is_modified:
                continue

            try:
                orig = original_lookup.get(plugin.name)
                self._patch_file(plugin, orig)
                result.modified_count += 1
                log.info("  Patched %s: EnabledByDefault %s -> %s",
                         plugin.name,
                         str(orig.enabled_by_default).lower() if orig else "?",
                         str(plugin.enabled_by_default).lower())
            except Exception as e:
                result.error_count += 1
                result.errors.append(f"{plugin.name}: {e}")
                log.error("  Failed to patch %s: %s", plugin.name, e)

        log.info("apply_changes done: %d patched, %d error(s)",
                 result.modified_count, result.error_count)
        return result

    def _patch_file(self, plugin: PluginData, original: Optional[PluginData]):
        """Rewrite a .uplugin file with the new EnabledByDefault value.

        Installed is intentionally left untouched — it is read-only metadata.
        """
        file_path = plugin.full_path
        self._unset_readonly(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["EnabledByDefault"] = plugin.enabled_by_default

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        log.debug("  Wrote %s: EnabledByDefault=%s", plugin.name, str(plugin.enabled_by_default).lower())

    @staticmethod
    def _unset_readonly(file_path: str):
        if os.path.isfile(file_path):
            attrs = os.stat(file_path).st_mode
            if not (attrs & 0o200):  # Not writable
                os.chmod(file_path, attrs | 0o200)
