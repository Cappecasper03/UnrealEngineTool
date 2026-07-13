#!/usr/bin/env python3
"""Headless CLI mode for the Unreal Engine Tool Patcher.

Runs the patcher logic (apply-custom / apply-default) without a GUI.
Designed for scripting and CI pipelines.

Usage:
    python src/main.py list
    python src/main.py apply-custom <patch-name> <ue-install-dir>
    python src/main.py apply-default <patch-name> <ue-install-dir>
"""

import argparse
import os
import sys
from typing import List, Optional

# Ensure src dir is on the path (same logic as main.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import EngineInfo
from logger import get_logger, enable_stdout
from patcher.patch_io import discover_patches
from patcher.file_patcher import FilePatcher, PatchResult

log = get_logger("cli")


def _get_patches_root() -> str:
    """Resolve the patches directory under LOCALAPPDATA."""
    from logger import default_patches_root
    return default_patches_root()


def cmd_list(args: argparse.Namespace) -> int:
    """List all available engine patches."""
    root = _get_patches_root()
    patches = discover_patches(root)

    if not patches:
        print("No patches found.")
        if not os.path.isdir(root):
            print(f"Patches directory does not exist: {root}")
        return 0

    print(f"Found {len(patches)} patch(es):\n")
    for p in patches:
        parent = f"  (parent: {p.parent_patch})" if p.parent_patch else ""
        unreal = f"  UE {p.unreal_version}" if p.unreal_version else ""
        file_count = len(p.files)
        print(f"  {p.patch_name}{parent}{unreal}")
        print(f"      Files: {file_count}")
        if p.changelog:
            # Show first line of changelog
            first_line = p.changelog.split("\n")[0].strip()
            if first_line:
                print(f"      {first_line}")
        print()

    return 0


def _find_patch(
    patch_name: str, patches: List[EngineInfo]
) -> Optional[EngineInfo]:
    """Find a patch by name (case-insensitive)."""
    key = patch_name.lower()
    for p in patches:
        if p.patch_name.lower() == key:
            return p
    return None


def cmd_apply_custom(args: argparse.Namespace) -> int:
    """Apply a custom engine patch to a UE installation."""
    return _do_apply(args, custom_engine=True)


def cmd_apply_default(args: argparse.Namespace) -> int:
    """Revert a UE installation to the default engine patch."""
    return _do_apply(args, custom_engine=False)


def _do_apply(args: argparse.Namespace, custom_engine: bool) -> int:
    root = _get_patches_root()
    patches = discover_patches(root)

    if not patches:
        log.error("No patches found at %s", root)
        print("Error: No patches found.")
        print(f"Patches directory: {root}")
        return 1

    # Normalise UE install directory
    ue_dir = os.path.normpath(os.path.abspath(args.ue_dir))
    if not os.path.isdir(ue_dir):
        log.error("UE install directory does not exist: %s", ue_dir)
        print(f"Error: UE install directory does not exist: {ue_dir}")
        return 1

    # Find the requested patch
    patch = _find_patch(args.patch_name, patches)
    if not patch:
        log.error("Patch '%s' not found", args.patch_name)
        print(
            f"Error: Patch '{args.patch_name}' not found. "
            f"Use 'list' to see available patches."
        )
        return 1

    # Run the patcher
    label = "custom" if custom_engine else "default"
    log.info("Starting %s apply: patch=%s target=%s", label, patch.patch_name, ue_dir)
    print(
        f"Applying {label} engine '{patch.patch_name}' "
        f"to {ue_dir} ..."
    )

    patcher = FilePatcher()
    if custom_engine:
        result = patcher.apply_custom(
            patch, patches, ue_dir, root, source_mode=False,
        )
    else:
        result = patcher.apply_default(
            patch, patches, ue_dir, root, source_mode=False,
        )

    if result.success:
        log.info("Apply %s succeeded: %s", label, result.message)
        print(f"Success: {result.message}")
        return 0
    else:
        log.error("Apply %s failed: %s", label, result.message)
        print(f"Failed: {result.message}", file=sys.stderr)
        return 1


def _cmd_log_path(args: argparse.Namespace) -> int:
    """Show the log file location."""
    from logger import log_path
    path = log_path()
    if path:
        print(f"Log file: {path}")
    else:
        print("Logger not initialised yet.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Unreal Engine Tool Patcher — Headless CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # List available patches\n"
            "  python src/main.py list\n\n"
            "  # Apply a custom engine patch\n"
            "  python src/main.py apply-custom UE_5.7-Test \"C:/Program Files/UE_5.7\"\n\n"
            "  # Revert to default\n"
            "  python src/main.py apply-default UE_5.7-Test \"C:/Program Files/UE_5.7\"\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List available patches")

    # log-path
    subparsers.add_parser("log-path", help="Show the log file location")

    # apply-custom
    apply_custom = subparsers.add_parser(
        "apply-custom", aliases=["apply"],
        help="Apply a custom engine patch to a UE installation",
    )
    apply_custom.add_argument(
        "patch_name", help="Name of the patch to apply (e.g. UE_5.7-Test)"
    )
    apply_custom.add_argument(
        "ue_dir", help="Path to the Unreal Engine installation directory"
    )

    # apply-default
    apply_default = subparsers.add_parser(
        "apply-default", aliases=["revert"],
        help="Revert a UE installation to the default engine patch",
    )
    apply_default.add_argument(
        "patch_name", help="Name of the patch to revert"
    )
    apply_default.add_argument(
        "ue_dir", help="Path to the Unreal Engine installation directory"
    )

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the headless CLI.

    Returns exit code (0 = success, 1 = error).
    """
    enable_stdout()

    parser = build_parser()
    args = parser.parse_args(argv)

    command_map = {
        "list": cmd_list,
        "apply-custom": cmd_apply_custom,
        "apply": cmd_apply_custom,
        "apply-default": cmd_apply_default,
        "revert": cmd_apply_default,
        "log-path": _cmd_log_path,
    }

    handler = command_map.get(args.command)
    if not handler:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
