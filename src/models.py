"""Data models for the Unreal Engine Tool."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class PluginData:
    """Represents a single Unreal Engine plugin (.uplugin)."""
    name: str = ""
    friendly_name: str = ""
    description: str = ""
    category: str = ""
    version_name: str = ""
    enabled_by_default: bool = False
    installed: bool = False
    relative_path: str = ""  # Relative to Engine/Plugins/
    full_path: str = ""  # Absolute path to .uplugin file
    icon_path: str = ""  # Path to plugin icon (128x128 PNG)

    # Snapshot for detecting modifications
    _original_enabled: bool = False
    _original_installed: bool = False

    def snapshot_original(self):
        self._original_enabled = self.enabled_by_default
        self._original_installed = self.installed

    def restore_original(self):
        self.enabled_by_default = self._original_enabled
        self.installed = self._original_installed

    @property
    def is_modified(self) -> bool:
        return (self.enabled_by_default != self._original_enabled or
                self.installed != self._original_installed)


# ───── Patcher Models ─────

from enum import IntEnum


class EngineStatus(IntEnum):
    NONE = 0
    MODIFY = 1
    ADD = 2
    REMOVE = 3


@dataclass
class EngineFile:
    """A single file entry in an engine version manifest."""
    path_custom: str = ""
    path_default: str = ""
    path_target: str = ""
    local_name: str = ""


@dataclass
class EngineInfo:
    """Represents a custom engine version with its file manifests and metadata."""
    info_dir: str = ""
    engine_version: str = ""
    parent_version: str = ""
    unreal_version: str = ""
    unreal_dir: str = ""
    changelog: str = ""
    files: List[EngineFile] = field(default_factory=list)
    status: EngineStatus = EngineStatus.NONE
