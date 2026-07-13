"""Discover Unreal Engine installation paths from the Windows registry and common filesystem locations."""

import os
import sys
from typing import List

from logger import get_logger

log = get_logger("registry_helper")


def discover_ue_installations() -> List[str]:
    r"""Return a sorted, deduplicated list of discovered UE installation directories.

    Checks (in priority order):
      1. HKCU\Software\Epic Games\Unreal Engine\Builds  (GUID -> path)
      2. HKLM\SOFTWARE\EpicGames\Unreal Engine\InstalledDirectory  (per-version)
      3. HKCU\Software\Epic Games\Unreal Engine\{Version}\InstalledDirectory
      4. Common filesystem locations (C:\Program Files\Epic Games\UE_*, etc.)
    """
    found: List[str] = []

    if sys.platform == "win32":
        found.extend(_from_registry_builds())
        found.extend(_from_registry_installed_dirs())
    found.extend(_from_common_filesystem())

    # Deduplicate by case-normalized path
    seen: set = set()
    unique: List[str] = []
    for p in found:
        p = os.path.normpath(p)
        key = p.lower()
        if key not in seen:
            seen.add(key)
            unique.append(p)

    unique.sort(key=lambda x: x.lower())
    log.info("discover_ue_installations: %d unique path(s) found (%d total sources)",
             len(unique), len(found))
    for p in unique:
        log.debug("  %s", p)
    return unique


# ── Registry queries ──────────────────────────────────────────────


def _from_registry_builds() -> List[str]:
    r"""Read HKCU\Software\Epic Games\Unreal Engine\Builds — GUID -> install path."""
    import winreg

    paths: List[str] = []
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Epic Games\Unreal Engine\Builds",
        ) as key:
            i = 0
            while True:
                try:
                    _name, value, _typ = winreg.EnumValue(key, i)
                    if isinstance(value, str) and os.path.isdir(value):
                        paths.append(value)
                    i += 1
                except OSError:
                    break
    except FileNotFoundError:
        pass
    return paths


def _from_registry_installed_dirs() -> List[str]:
    r"""Read per-version InstalledDirectory from HKLM and HKCU.

    HKLM\SOFTWARE\EpicGames\Unreal Engine\{Version}\InstalledDirectory
    HKCU\Software\Epic Games\Unreal Engine\{Version}\InstalledDirectory
    """
    import winreg

    paths: List[str] = []
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\EpicGames\Unreal Engine"),
        (winreg.HKEY_CURRENT_USER, r"Software\Epic Games\Unreal Engine"),
    ]

    for hkey, root_path in roots:
        try:
            with winreg.OpenKey(hkey, root_path) as root_key:
                j = 0
                while True:
                    try:
                        sub_name = winreg.EnumKey(root_key, j)
                        sub_path = f"{root_path}\\{sub_name}"
                        try:
                            with winreg.OpenKey(hkey, sub_path) as sk:
                                try:
                                    val, _typ = winreg.QueryValueEx(sk, "InstalledDirectory")
                                    if isinstance(val, str) and os.path.isdir(val):
                                        paths.append(val)
                                except FileNotFoundError:
                                    pass
                        except OSError:
                            pass
                        j += 1
                    except OSError:
                        break
        except FileNotFoundError:
            pass

    return paths


# ── Filesystem fallback ───────────────────────────────────────────


_COMMON_UE_ROOTS = [
    r"C:\Program Files\Epic Games",
    r"C:\Epic Games",
    r"D:\Epic Games",
    r"E:\Epic Games",
    r"D:\Program Files\Epic Games",
    r"E:\Program Files\Epic Games",
]


def _from_common_filesystem() -> List[str]:
    """Scan well-known Epic Games directories for UE_* folders."""
    paths: List[str] = []
    for root in _COMMON_UE_ROOTS:
        if not os.path.isdir(root):
            continue
        try:
            for entry in os.listdir(root):
                full = os.path.join(root, entry)
                if os.path.isdir(full) and entry.upper().startswith("UE_"):
                    paths.append(full)
        except PermissionError:
            pass
    return paths
