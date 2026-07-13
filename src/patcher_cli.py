#!/usr/bin/env python3
"""Headless CLI mode for the Unreal Engine Tool Patcher.

Runs the patcher logic (apply-custom / apply-default) without a GUI.
Designed for scripting and CI pipelines.

Usage:
    python src/main.py list
    python src/main.py apply-custom <version-name> <ue-install-dir>
    python src/main.py apply-default <version-name> <ue-install-dir>
"""

import argparse
import os
import sys
from typing import List, Optional

# Ensure src dir is on the path (same logic as main.py)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import EngineInfo
from patcher.patcher_logger import get_logger, enable_stdout
from patcher.version_io import discover_versions
from patcher.file_patcher import FilePatcher, PatchResult

log = get_logger("cli")


def _get_versions_root() -> str:
    """Resolve the Versions/ directory relative to the project root."""
    return os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "Versions"
    ))


def cmd_list(args: argparse.Namespace) -> int:
    """List all available engine patch versions."""
    root = _get_versions_root()
    versions = discover_versions(root)

    if not versions:
        print("No patch versions found.")
        if not os.path.isdir(root):
            print(f"Versions directory does not exist: {root}")
        return 0

    print(f"Found {len(versions)} patch version(s):\n")
    for v in versions:
        parent = f"  (parent: {v.parent_version})" if v.parent_version else ""
        unreal = f"  UE {v.unreal_version}" if v.unreal_version else ""
        file_count = len(v.files)
        print(f"  {v.engine_version}{parent}{unreal}")
        print(f"      Files: {file_count}")
        if v.changelog:
            # Show first line of changelog
            first_line = v.changelog.split("\n")[0].strip()
            if first_line:
                print(f"      {first_line}")
        print()

    return 0


def _find_version(
    version_name: str, versions: List[EngineInfo]
) -> Optional[EngineInfo]:
    """Find a version by name (case-insensitive)."""
    key = version_name.lower()
    for v in versions:
        if v.engine_version.lower() == key:
            return v
    return None


def cmd_apply_custom(args: argparse.Namespace) -> int:
    """Apply a custom engine version to a UE installation."""
    return _do_apply(args, custom_engine=True)


def cmd_apply_default(args: argparse.Namespace) -> int:
    """Revert a UE installation to the default engine version."""
    return _do_apply(args, custom_engine=False)


def _do_apply(args: argparse.Namespace, custom_engine: bool) -> int:
    root = _get_versions_root()
    versions = discover_versions(root)

    if not versions:
        log.error("No patch versions found at %s", root)
        print("Error: No patch versions found.")
        print(f"Versions directory: {root}")
        return 1

    # Normalise UE install directory
    ue_dir = os.path.normpath(os.path.abspath(args.ue_dir))
    if not os.path.isdir(ue_dir):
        log.error("UE install directory does not exist: %s", ue_dir)
        print(f"Error: UE install directory does not exist: {ue_dir}")
        return 1

    # Find the requested version
    version = _find_version(args.version_name, versions)
    if not version:
        log.error("Version '%s' not found", args.version_name)
        print(
            f"Error: Version '{args.version_name}' not found. "
            f"Use 'list' to see available versions."
        )
        return 1

    # Run the patcher
    label = "custom" if custom_engine else "default"
    log.info("Starting %s apply: version=%s target=%s", label, version.engine_version, ue_dir)
    print(
        f"Applying {label} engine '{version.engine_version}' "
        f"to {ue_dir} ..."
    )

    patcher = FilePatcher()
    if custom_engine:
        result = patcher.apply_custom(
            version, versions, ue_dir, root, source_mode=False,
        )
    else:
        result = patcher.apply_default(
            version, versions, ue_dir, root, source_mode=False,
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
    from patcher.patcher_logger import log_path
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
            "  # List available patch versions\n"
            "  python src/main.py list\n\n"
            "  # Apply a custom engine version\n"
            "  python src/main.py apply-custom UE_5.7-Test \"C:/Program Files/UE_5.7\"\n\n"
            "  # Revert to default\n"
            "  python src/main.py apply-default UE_5.7-Test \"C:/Program Files/UE_5.7\"\n"
        ),
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    subparsers.add_parser("list", help="List available patch versions")

    # log-path
    subparsers.add_parser("log-path", help="Show the log file location")

    # apply-custom
    apply_custom = subparsers.add_parser(
        "apply-custom", aliases=["apply"],
        help="Apply a custom engine version to a UE installation",
    )
    apply_custom.add_argument(
        "version_name", help="Name of the patch version to apply (e.g. UE_5.7-Test)"
    )
    apply_custom.add_argument(
        "ue_dir", help="Path to the Unreal Engine installation directory"
    )

    # apply-default
    apply_default = subparsers.add_parser(
        "apply-default", aliases=["revert"],
        help="Revert a UE installation to the default engine version",
    )
    apply_default.add_argument(
        "version_name", help="Name of the patch version to revert"
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
