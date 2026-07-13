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
    relative_path: str = ""
    full_path: str = ""
    icon_path: str = ""

    # Snapshot for detecting modifications (EnabledByDefault only)
    _original_enabled: bool = False

    def snapshot_original(self):
        self._original_enabled = self.enabled_by_default

    def restore_original(self):
        self.enabled_by_default = self._original_enabled

    @property
    def is_modified(self) -> bool:
        return self.enabled_by_default != self._original_enabled


# ───── Patcher Models ─────

from enum import IntEnum


class EngineStatus(IntEnum):
    NONE = 0
    MODIFY = 1
    ADD = 2
    REMOVE = 3


@dataclass
class EngineFile:
    """A single file entry in an engine patch manifest."""
    path_custom: str = ""
    path_default: str = ""
    path_target: str = ""
    local_name: str = ""


@dataclass
class EngineInfo:
    """Represents a custom engine patch with its file manifests and metadata."""
    info_dir: str = ""
    patch_name: str = ""
    parent_patch: str = ""
    unreal_version: str = ""
    unreal_dir: str = ""
    changelog: str = ""
    files: List[EngineFile] = field(default_factory=list)
    status: EngineStatus = EngineStatus.NONE
