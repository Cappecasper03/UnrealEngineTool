"""Recursively scans a UE engine directory to discover all .uplugin files."""

import json
import os
from typing import Callable, List, Optional

from logger import get_logger
from models import PluginData

log = get_logger("plugin_scanner")

# Directories to skip when scanning plugin folders
IGNORED_FOLDERS = frozenset({
    "Binaries", "Config", "Content", "Docs", "Intermediate",
    "Library", "Private", "Public", "Resources", "SDK", "SDKs",
    "Shaders", "Source", "SourceArt", "ThirdParty",
})


class UPluginScanner:
    """Scans a UE engine directory for .uplugin files under Engine/Plugins/."""

    def scan(
        self,
        ue_root_path: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> List[PluginData]:
        """Scan a UE root directory for all .uplugin files under Engine/Plugins/."""
        plugins_dir = os.path.join(ue_root_path, "Engine", "Plugins")
        if not os.path.isdir(plugins_dir):
            raise FileNotFoundError(
                f"Engine Plugins directory not found: {plugins_dir}"
            )

        plugins: List[PluginData] = []
        self._scan_directory(plugins_dir, plugins_dir, plugins, progress_callback)
        log.info("scan: found %d plugin(s) under %s", len(plugins), plugins_dir)
        return plugins

    def _scan_directory(
        self,
        directory: str,
        plugins_root: str,
        results: List[PluginData],
        progress: Optional[Callable[[str], None]],
    ):
        try:
            entries = os.listdir(directory)
        except PermissionError:
            return

        for entry in entries:
            sub_path = os.path.join(directory, entry)
            if not os.path.isdir(sub_path):
                continue

            dir_name = os.path.basename(sub_path)
            if dir_name in IGNORED_FOLDERS:
                continue

            if progress:
                progress(sub_path)

            # Find .uplugin files in this directory
            try:
                for file_name in os.listdir(sub_path):
                    if file_name.endswith(".uplugin"):
                        plugin = self._read_uplugin(
                            os.path.join(sub_path, file_name),
                            plugins_root,
                        )
                        results.append(plugin)
                        break  # One .uplugin per directory
            except (PermissionError, OSError):
                pass

            # Recurse
            self._scan_directory(sub_path, plugins_root, results, progress)

    @staticmethod
    def read_uplugin(full_path: str, plugins_root: str) -> PluginData:
        """Parse a single .uplugin JSON file into a PluginData object."""
        return UPluginScanner._read_uplugin(full_path, plugins_root)

    @staticmethod
    def _read_uplugin(full_path: str, plugins_root: str) -> PluginData:
        data = PluginData(
            name=os.path.splitext(os.path.basename(full_path))[0],
            full_path=full_path,
            relative_path=os.path.relpath(full_path, plugins_root),
        )

        # Try to load the plugin icon
        plugin_dir = os.path.dirname(full_path)
        icon_path = os.path.join(plugin_dir, "Resources", "icon128.png")
        if os.path.isfile(icon_path):
            data.icon_path = icon_path

        # Parse the JSON .uplugin file
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                root = json.load(f)

            data.friendly_name = root.get("FriendlyName", "")
            data.description = root.get("Description", "")
            data.category = root.get("Category", "")
            data.version_name = root.get("VersionName", "")
            data.enabled_by_default = root.get("EnabledByDefault", False)
            data.installed = root.get("Installed", False)

            log.debug("  Found plugin: %s (enabled=%s, installed=%s)",
                      data.name, str(data.enabled_by_default).lower(), str(data.installed).lower())

        except (json.JSONDecodeError, OSError) as e:
            data.description = f"[Parse error: {e}]"
            log.warning("  Parse error for %s: %s", full_path, e)

        data.snapshot_original()

        return data
