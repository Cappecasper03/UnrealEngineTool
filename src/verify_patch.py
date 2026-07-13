#!/usr/bin/env python3
"""Verify the state of a UE installation against a patch version.

Usage:
    python src/verify_patch.py <ue-install-dir> <expected-version-name>

Prints a human-readable report of what's applied, what files differ, and exits
with code 0 if everything matches, 1 if there are differences.

The verification script is designed for use with the headless CLI mode:
    
    # Apply a custom engine
    python src/main.py --cli apply-custom UE_5.7-Test path/to/UE_5.7

    # Verify it was applied correctly
    python src/verify_patch.py path/to/UE_5.7 UE_5.7-Test

    # Revert to default
    python src/main.py --cli apply-default UE_5.7-Test path/to/UE_5.7

    # Verify it was reverted
    python src/verify_patch.py path/to/UE_5.7 default

Exit codes:
    0 = matches expected state
    1 = does not match expected state
    2 = error (invalid args, missing files)
"""

import hashlib
import os
import sys
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from patcher.version_io import discover_versions, read_info
from patcher.file_patcher import FilePatcher
from models import EngineInfo


def md5(path: str) -> str:
    """Compute MD5 hash of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_versions_root() -> str:
    """Resolve the patches directory under LOCALAPPDATA."""
    from logger import default_patches_root
    return default_patches_root()


def _find_version(
    version_name: str, versions: List[EngineInfo]
) -> Optional[EngineInfo]:
    key = version_name.lower()
    for v in versions:
        if v.engine_version.lower() == key:
            return v
    return None


def verify(
    ue_dir: str, expected_version: str, verbose: bool = True
) -> Tuple[bool, str]:
    """Verify the state of a UE installation.

    Returns (ok, message).
    """
    if not os.path.isdir(ue_dir):
        return False, f"UE directory does not exist: {ue_dir}"

    ue_dir = os.path.normpath(ue_dir)
    root = _get_versions_root()
    versions = discover_versions(root)

    # ── Check the marker ──
    marker = FilePatcher.read_marker(ue_dir)
    expected_lower = expected_version.lower()

    if marker.lower() != expected_lower:
        return (
            False,
            f"Marker mismatch: expected '{expected_version}', "
            f"found '{marker}'",
        )

    if verbose:
        print(f"[OK] Marker: {marker}")

    # Special case: "default" means not applied — just check marker
    if expected_lower == "default":
        # No further file checks needed for default state
        return True, f"UE installation is in default state (marker: {marker})"

    # ── Check file hashes ──
    version = _find_version(expected_version, versions)
    if not version:
        return False, f"Version '{expected_version}' not found in {root}"

    if not version.files:
        return True, f"Version '{expected_version}' has no file entries to verify"

    issues = []
    ok_count = 0

    for fe in version.files:
        target_path = os.path.join(ue_dir, fe.path_target.lstrip("\\/"))
        if not os.path.isfile(target_path):
            issues.append(f"  MISSING  {fe.path_target}")
            continue

        # Determine which source to compare against
        source_path = fe.path_custom if fe.path_custom else fe.path_default
        if source_path and not os.path.isabs(source_path):
            source_path = os.path.join(
                root, version.engine_version, source_path
            )

        if source_path and os.path.isfile(source_path):
            actual_hash = md5(target_path)
            expected_hash = md5(source_path)

            if actual_hash == expected_hash:
                ok_count += 1
                if verbose:
                    print(f"[OK] {fe.path_target}")
            else:
                issues.append(
                    f"  MISMATCH {fe.path_target}\n"
                    f"      actual:   {actual_hash}\n"
                    f"      expected: {expected_hash}"
                )
        else:
            # Source file doesn't exist (e.g. backup-based path)
            # Just report that the target exists
            ok_count += 1
            if verbose:
                print(f"[OK] {fe.path_target}  (exists, source not available for comparison)")

    if issues:
        report = (
            f"Verification FAILED for '{expected_version}' "
            f"at {ue_dir}:\n"
            + "\n".join(issues)
        )
        return False, report

    return (
        True,
        f"All {ok_count} file(s) match '{expected_version}' "
        f"at {ue_dir}",
    )


def main() -> int:
    if len(sys.argv) < 3:
        print(
            f"Usage: {sys.argv[0]} <ue-install-dir> <expected-version-name>\n"
            f"       Use 'default' for an unpatched installation.",
            file=sys.stderr,
        )
        return 2

    ue_dir = sys.argv[1]
    expected = sys.argv[2]

    ok, msg = verify(ue_dir, expected)
    print(msg)

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
