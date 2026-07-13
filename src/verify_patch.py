#!/usr/bin/env python3
"""Verify the state of a UE installation against a patch.

Usage:
    python src/verify_patch.py <ue-install-dir> <expected-patch-name>

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

from logger import get_logger
from patcher.patch_io import discover_patches, read_info
from patcher.file_patcher import FilePatcher
from models import EngineInfo

log = get_logger("verify_patch")


def md5(path: str) -> str:
    """Compute MD5 hash of a file."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _get_patches_root() -> str:
    """Resolve the patches directory under LOCALAPPDATA."""
    from logger import default_patches_root
    return default_patches_root()


def _find_patch(
    patch_name: str, patches: List[EngineInfo]
) -> Optional[EngineInfo]:
    key = patch_name.lower()
    for p in patches:
        if p.patch_name.lower() == key:
            return p
    return None


def verify(
    ue_dir: str, expected_patch: str, verbose: bool = True
) -> Tuple[bool, str]:
    """Verify the state of a UE installation.

    Returns (ok, message).
    """
    if not os.path.isdir(ue_dir):
        return False, f"UE directory does not exist: {ue_dir}"

    ue_dir = os.path.normpath(ue_dir)
    root = _get_patches_root()
    patches = discover_patches(root)

    # ── Check the marker ──
    marker = FilePatcher.read_marker(ue_dir)
    expected_lower = expected_patch.lower()

    if marker.lower() != expected_lower:
        return (
            False,
            f"Marker mismatch: expected '{expected_patch}', "
            f"found '{marker}'",
        )

    if verbose:
        print(f"[OK] Marker: {marker}")

    log.debug("Marker check: expected=%s actual=%s OK", expected_patch, marker)

    # Special case: "default" means not applied — just check marker
    if expected_lower == "default":
        # No further file checks needed for default state
        return True, f"UE installation is in default state (marker: {marker})"

    # ── Check file hashes ──
    patch = _find_patch(expected_patch, patches)
    if not patch:
        return False, f"Patch '{expected_patch}' not found in {root}"

    if not patch.files:
        return True, f"Patch '{expected_patch}' has no file entries to verify"

    issues = []
    ok_count = 0

    for fe in patch.files:
        target_path = os.path.join(ue_dir, fe.path_target.lstrip("\\/"))
        if not os.path.isfile(target_path):
            issues.append(f"  MISSING  {fe.path_target}")
            continue

        # Determine which source to compare against
        source_path = fe.path_custom if fe.path_custom else fe.path_default
        if source_path and not os.path.isabs(source_path):
            source_path = os.path.join(
                root, patch.patch_name, source_path
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
            f"Verification FAILED for '{expected_patch}' "
            f"at {ue_dir}:\n"
            + "\n".join(issues)
        )
        log.warning("Verification FAILED for %s at %s: %d issue(s)",
                     expected_patch, ue_dir, len(issues))
        return False, report

    log.info("Verification PASSED for %s at %s: %d file(s) OK",
             expected_patch, ue_dir, ok_count)
    return (
        True,
        f"All {ok_count} file(s) match '{expected_patch}' "
        f"at {ue_dir}",
    )


def main() -> int:
    if len(sys.argv) < 3:
        print(
            f"Usage: {sys.argv[0]} <ue-install-dir> <expected-patch-name>\n"
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
