"""Handles copying engine files to/from a UE installation directory."""

import os
import shutil
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

from models import EngineInfo
from logger import get_logger

log = get_logger("file_patcher")


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

    # Marker file written to UE installation after a successful apply
    MARKER_RELPATH = "Engine/Binaries/.uepatcher_version"

    @staticmethod
    def marker_path(ue_dir: str) -> str:
        return os.path.join(ue_dir, FilePatcher.MARKER_RELPATH)

    @staticmethod
    def write_marker(ue_dir: str, version_name: str):
        """Write the applied version marker."""
        path = FilePatcher.marker_path(ue_dir)
        d = os.path.dirname(path)
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        with open(path, "w") as f:
            f.write(version_name.strip())

    @staticmethod
    def read_marker(ue_dir: str) -> str:
        """Read the applied version marker, or empty string if none."""
        path = FilePatcher.marker_path(ue_dir)
        if not os.path.isfile(path):
            return ""
        try:
            with open(path, "r") as f:
                value = f.read().strip()
            log.debug("Read marker from %s: %s", path, value)
            return value
        except OSError:
            return ""

    @staticmethod
    def detect_applied_version(ue_dir: str, all_versions: List[EngineInfo]) -> Optional[str]:
        """Return the engine_version matching the marker, or None."""
        marker = FilePatcher.read_marker(ue_dir)
        if not marker:
            return None
        # Check against known versions (case-insensitive)
        for v in all_versions:
            if v.engine_version.lower() == marker.lower():
                return v.engine_version
        # Also accept marker value that isn't a known version (manual edit)
        return marker

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
            log.error("Invalid UE directory: %s (%s test file missing)", ue_install_dir,
                      "source" if source_mode else "engine")
            return result

        files_to_copy: List[Tuple[str, str]] = []
        files_to_remove: List[str] = []
        ignored_targets: Set[str] = set()

        # Collect files with parent inheritance
        self._collect_files(
            engine_version, all_versions, custom_engine, versions_root,
            ue_install_dir, source_mode,
            files_to_copy, files_to_remove, ignored_targets,
        )

        ver_dir = os.path.join(versions_root, engine_version.engine_version)

        action_label = "custom" if custom_engine else "default"
        log.info("%s apply start — version=%s target=%s files_to_copy=%d files_to_remove=%d",
                 action_label, engine_version.engine_version, ue_install_dir,
                 len(files_to_copy), len(files_to_remove))

        if custom_engine:
            # ── Back up originals before overwriting ──
            for i, (src, dst) in enumerate(files_to_copy):
                if not os.path.isfile(dst):
                    continue  # No original to back up — file doesn't exist in UE yet
                # Compute backup path inside version dir
                target_rel = os.path.relpath(dst, ue_install_dir)
                backup_abs = os.path.join(ver_dir, "_originals", target_rel)
                backup_dir = os.path.dirname(backup_abs)
                if backup_dir and not os.path.isdir(backup_dir):
                    os.makedirs(backup_dir, exist_ok=True)
                try:
                    if os.path.isfile(backup_abs):
                        os.chmod(backup_abs, os.stat(backup_abs).st_mode | 0o200)
                    shutil.copy2(dst, backup_abs)
                    os.chmod(backup_abs, os.stat(backup_abs).st_mode & ~0o222)

                    # Update the EngineFile entry so path_default points to the backup
                    target = os.path.relpath(dst, ue_install_dir).replace("\\", "/")
                    for fe in engine_version.files:
                        if fe.path_target.replace("\\", "/") == target:
                            backup_rel = f"_originals/{target_rel.replace(chr(92), '/')}"
                            fe.path_default = backup_rel
                            break
                    result.files_removed += 1  # Reuse as "backed up" counter
                    log.debug("Backed up: %s -> %s", dst, backup_abs)
                except OSError as e:
                    result.success = False
                    result.message = f"Failed to back up {dst}: {e}"
                    return result

            # Save updated path_default back to info.dat so revert can find originals
            if result.files_removed > 0:
                try:
                    from patcher.version_io import write_info
                    write_info(engine_version)
                except OSError:
                    pass  # Non-fatal — backups exist on disk anyway

        # Verify sources exist
        for src, _ in files_to_copy:
            if not os.path.isfile(src):
                result.success = False
                result.message = f"Source file not found: {src}"
                log.error("Source file not found: %s", src)
                return result

        # Copy files (custom → UE, or default → UE on revert)
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
                log.debug("Copied: %s -> %s", src, dst)
            except OSError as e:
                result.success = False
                result.message = f"Failed to copy {src} -> {dst}: {e}"
                return result

        # Remove files (only orphan files that exist in backup but no longer in manifest)
        for file_path in files_to_remove:
            if not os.path.isfile(file_path):
                continue
            try:
                os.chmod(file_path, os.stat(file_path).st_mode | 0o200)
                os.remove(file_path)
                result.files_removed += 1
                log.debug("Removed: %s", file_path)
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
        # Write marker so we can detect applied version on next launch
        marker_value = "default" if not custom_engine else engine_version.engine_version
        try:
            self.write_marker(ue_install_dir, marker_value)
            log.info("Marker written: %s -> %s", marker_value, FilePatcher.marker_path(ue_install_dir))
        except OSError:
            pass  # Non-fatal — marker is just a convenience

        log.info("Result: %s (files_copied=%d files_removed=%d)",
                 "✓" if result.success else "✗", result.files_copied, result.files_removed)
        return result

    def _collect_files(
        self,
        version: EngineInfo,
        all_versions: List[EngineInfo],
        custom_engine: bool,
        versions_root: str,
        ue_install_dir: str,
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

            if custom_engine:
                if file_entry.path_custom:
                    source_path = (
                        file_entry.path_custom
                        if os.path.isabs(file_entry.path_custom)
                        else os.path.join(versions_root, version.engine_version, file_entry.path_custom)
                    )
                    if source_mode and not _is_source_file(file_entry.path_custom):
                        continue
                    target_path = os.path.join(ue_install_dir, target.lstrip("\\/"))
                    files_to_copy.append((source_path, target_path))
                elif file_entry.path_default:
                    target_path = os.path.join(ue_install_dir, target.lstrip("\\/"))
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
                    target_path = os.path.join(ue_install_dir, target.lstrip("\\/"))
                    files_to_copy.append((source_path, target_path))
                elif file_entry.path_custom:
                    target_path = os.path.join(ue_install_dir, target.lstrip("\\/"))
                    if os.path.isfile(target_path):
                        files_to_remove.append(target_path)

        # Recurse to parent
        if version.parent_version:
            for v in all_versions:
                if v.engine_version.lower() == version.parent_version.lower():
                    self._collect_files(
                        v, all_versions, custom_engine, versions_root,
                        ue_install_dir, source_mode,
                        files_to_copy, files_to_remove, ignored_targets,
                    )
                    break
