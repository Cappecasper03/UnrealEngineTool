"""Applies changes to .uplugin files on disk: toggles EnabledByDefault and Installed."""

import os
import re
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
            lines = f.readlines()

        new_lines: List[str] = []
        ebd_found = False
        installed_found = False
        modules_found = False

        new_ebd = plugin.enabled_by_default
        orig_ebd_str = str(original.enabled_by_default).lower() if original else "false"
        new_ebd_str = str(new_ebd).lower()

        new_installed = plugin.installed
        orig_installed_str = str(original.installed).lower() if original else "false"
        new_installed_str = str(new_installed).lower()

        for line in lines:
            # Find and replace EnabledByDefault
            ok, replaced = self._try_replace_json_value(
                line, "EnabledByDefault", orig_ebd_str, new_ebd_str
            )
            if ok:
                new_lines.append(replaced)
                ebd_found = True
                continue

            # Find and replace Installed
            ok, replaced = self._try_replace_json_value(
                line, "Installed", orig_installed_str, new_installed_str
            )
            if ok:
                new_lines.append(replaced)
                installed_found = True
                continue

            # Track the "Modules" line for injection
            if not modules_found and line.strip().startswith('"Modules"'):
                modules_found = True
                indent = len(line) - len(line.lstrip())

                # Inject missing fields before Modules
                if not ebd_found:
                    new_lines.append(f"{' ' * indent}\"EnabledByDefault\": {new_ebd_str},\n")
                    ebd_found = True
                if not installed_found:
                    new_lines.append(f"{' ' * indent}\"Installed\": {new_installed_str},\n")
                    installed_found = True

                new_lines.append(line)
                continue

            new_lines.append(line)

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

    @staticmethod
    def _try_replace_json_value(
        line: str, key: str, old_value: str, new_value: str
    ) -> tuple:
        """Try to replace a JSON key-value pair on a single line."""
        pattern = rf'("{key}":\s*){re.escape(old_value)}(,?)'
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            result = (
                line[: match.start()]
                + match.group(1)
                + new_value
                + match.group(2)
                + line[match.end():]
            )
            return True, result

        # Check if key already exists
        exists_pattern = rf'"{key}"\s*:'
        if re.search(exists_pattern, line):
            return True, line  # Already has the key with a different value — skip

        return False, line

    @staticmethod
    def _unset_readonly(file_path: str):
        if os.path.isfile(file_path):
            attrs = os.stat(file_path).st_mode
            if not (attrs & 0o200):  # Not writable
                os.chmod(file_path, attrs | 0o200)
