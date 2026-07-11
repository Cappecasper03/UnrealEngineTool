"""Handles copying engine files to/from a UE installation directory."""

import os
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from models import EngineInfo


@dataclass
class PatchResult:
    success: bool = False
    files_copied: int = 0
    files_removed: int = 0
    message: str = ""


def _is_source_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    return ext in {".h", ".cpp"}


class FilePatcher:
    """Handles copying/removing engine files for custom engine versions."""

    def apply_custom(
        self,
        engine_version: EngineInfo,
        all_versions: List[EngineInfo],
        ue_install_dir: str,
        versions_root: str,
        source_mode: bool,
    ) -> PatchResult:
        return self._apply_files(
            engine_version, all_versions, ue_install_dir, versions_root,
            custom_engine=True, source_mode=source_mode,
        )

    def apply_default(
        self,
        engine_version: EngineInfo,
        all_versions: List[EngineInfo],
        ue_install_dir: str,
        versions_root: str,
        source_mode: bool,
    ) -> PatchResult:
        return self._apply_files(
            engine_version, all_versions, ue_install_dir, versions_root,
            custom_engine=False, source_mode=source_mode,
        )

    def _apply_files(
        self,
        engine_version: EngineInfo,
        all_versions: List[EngineInfo],
        ue_install_dir: str,
        versions_root: str,
        custom_engine: bool,
        source_mode: bool,
    ) -> PatchResult:
        result = PatchResult()

        # Validate UE directory
        if source_mode:
            test_file = os.path.join(
                ue_install_dir, "Engine", "Source", "Runtime", "Engine", "Private", "Actor.cpp"
            )
        else:
            test_file = os.path.join(
                ue_install_dir, "Engine", "Binaries", "Win64", "UnrealEditor-Engine.dll"
            )

        if not os.path.isdir(ue_install_dir) or not os.path.isfile(test_file):
            result.success = False
            result.message = (
                f"Invalid UE directory: {ue_install_dir} "
                f"({'source' if source_mode else 'engine'} test file not found)"
            )
            return result

        files_to_copy: List[Tuple[str, str]] = []
        files_to_remove: List[str] = []
        ignored_targets: Set[str] = set()

        # Collect files with parent inheritance
        self._collect_files(
            engine_version, all_versions, custom_engine, versions_root,
            source_mode, files_to_copy, files_to_remove, ignored_targets,
        )

        # Verify sources exist
        for src, _ in files_to_copy:
            if not os.path.isfile(src):
                result.success = False
                result.message = f"Source file not found: {src}"
                return result

        # Copy files
        for src, dst in files_to_copy:
            dst_dir = os.path.dirname(dst)
            if dst_dir and not os.path.isdir(dst_dir):
                os.makedirs(dst_dir, exist_ok=True)

            try:
                if os.path.isfile(dst):
                    os.chmod(dst, os.stat(dst).st_mode | 0o200)  # Remove readonly
                with open(src, "rb") as sf, open(dst, "wb") as df:
                    df.write(sf.read())
                os.chmod(dst, os.stat(dst).st_mode & ~0o222)  # Make readonly
                result.files_copied += 1
            except OSError as e:
                result.success = False
                result.message = f"Failed to copy {src} -> {dst}: {e}"
                return result

        # Remove files
        for file_path in files_to_remove:
            if not os.path.isfile(file_path):
                continue
            try:
                os.chmod(file_path, os.stat(file_path).st_mode | 0o200)
                os.remove(file_path)
                result.files_removed += 1
            except OSError as e:
                result.success = False
                result.message = f"Failed to remove {file_path}: {e}"
                return result

        result.success = True
        action = "Custom engine applied" if custom_engine else "Default engine applied"
        result.message = (
            f"{action}: {result.files_copied} files copied, "
            f"{result.files_removed} removed."
        )
        return result

    def _collect_files(
        self,
        version: EngineInfo,
        all_versions: List[EngineInfo],
        custom_engine: bool,
        versions_root: str,
        source_mode: bool,
        files_to_copy: List[Tuple[str, str]],
        files_to_remove: List[str],
        ignored_targets: Set[str],
    ):
        for file_entry in version.files:
            target = file_entry.path_target
            if not target:
                continue

            if target in ignored_targets:
                continue
            ignored_targets.add(target)

            unreal_dir = version.unreal_dir

            if custom_engine:
                if file_entry.path_custom:
                    source_path = (
                        file_entry.path_custom
                        if os.path.isabs(file_entry.path_custom)
                        else os.path.join(versions_root, version.engine_version, file_entry.path_custom)
                    )
                    if source_mode and not _is_source_file(file_entry.path_custom):
                        continue
                    target_path = os.path.join(unreal_dir, target.lstrip("\\/"))
                    files_to_copy.append((source_path, target_path))
                elif file_entry.path_default:
                    target_path = os.path.join(unreal_dir, target.lstrip("\\/"))
                    if os.path.isfile(target_path):
                        files_to_remove.append(target_path)
            else:
                if file_entry.path_default:
                    source_path = (
                        file_entry.path_default
                        if os.path.isabs(file_entry.path_default)
                        else os.path.join(versions_root, version.engine_version, file_entry.path_default)
                    )
                    if source_mode and not _is_source_file(file_entry.path_default):
                        continue
                    target_path = os.path.join(unreal_dir, target.lstrip("\\/"))
                    files_to_copy.append((source_path, target_path))
                elif file_entry.path_custom:
                    target_path = os.path.join(unreal_dir, target.lstrip("\\/"))
                    if os.path.isfile(target_path):
                        files_to_remove.append(target_path)

        # Recurse to parent
        if version.parent_version:
            for v in all_versions:
                if v.engine_version.lower() == version.parent_version.lower():
                    self._collect_files(
                        v, all_versions, custom_engine, versions_root,
                        source_mode, files_to_copy, files_to_remove, ignored_targets,
                    )
                    break
