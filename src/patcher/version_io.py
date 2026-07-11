"""Reads and writes the binary info.dat format from RPEngineInstaller.

Format: "RPEngineHeader" (14 bytes) + length-prefixed strings + file entries.
Each string: uint32 length + UTF8 bytes.
Each file entry: 3 length-prefixed strings (pathCustom, pathDefault, pathTarget).
"""

import os
import struct
from typing import List

from models import EngineFile, EngineInfo

HEADER = b"RPEngineHeader"


def _read_string(data: bytes, offset: int) -> tuple:
    """Read a length-prefixed UTF-8 string from binary data."""
    length = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    if length <= 0:
        return "", offset
    value = data[offset:offset + length].decode("utf-8")
    offset += length
    return value, offset


def _write_string(value: str) -> bytes:
    """Write a string as length-prefixed UTF-8 bytes."""
    if not value:
        return struct.pack("<I", 0)
    encoded = value.encode("utf-8")
    return struct.pack("<I", len(encoded)) + encoded


def read_info(file_path: str) -> EngineInfo:
    """Read a version's info.dat file."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Version info file not found: {file_path}")

    with open(file_path, "rb") as f:
        data = f.read()

    info = EngineInfo(info_dir=file_path)
    offset = 0

    # Verify header
    header = data[:14]
    if header != HEADER:
        raise ValueError(f"Invalid header: expected {HEADER!r}, got {header!r}")
    offset += 14

    info.engine_version, offset = _read_string(data, offset)
    info.parent_version, offset = _read_string(data, offset)
    info.unreal_version, offset = _read_string(data, offset)
    info.unreal_dir, offset = _read_string(data, offset)
    info.changelog, offset = _read_string(data, offset)

    file_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4

    for _ in range(file_count):
        path_custom, offset = _read_string(data, offset)
        path_default, offset = _read_string(data, offset)
        path_target, offset = _read_string(data, offset)

        src_path = path_custom if path_custom else path_default
        local_name = os.path.basename(src_path)

        info.files.append(EngineFile(
            path_custom=path_custom,
            path_default=path_default,
            path_target=path_target,
            local_name=local_name,
        ))

    return info


def write_info(info: EngineInfo):
    """Write a version's info.dat file (binary format)."""
    dir_path = os.path.dirname(info.info_dir)
    if dir_path and not os.path.isdir(dir_path):
        os.makedirs(dir_path, exist_ok=True)

    parts = [HEADER]
    parts.append(_write_string(info.engine_version))
    parts.append(_write_string(info.parent_version))
    parts.append(_write_string(info.unreal_version))
    parts.append(_write_string(info.unreal_dir))
    parts.append(_write_string(info.changelog))
    parts.append(struct.pack("<I", len(info.files)))

    for f in info.files:
        parts.append(_write_string(f.path_custom))
        parts.append(_write_string(f.path_default))
        parts.append(_write_string(f.path_target))

    with open(info.info_dir, "wb") as f:
        for part in parts:
            f.write(part)


def discover_versions(versions_root: str) -> List[EngineInfo]:
    """Find all version info files under a root directory."""
    versions: List[EngineInfo] = []

    if not os.path.isdir(versions_root):
        return versions

    for dirpath, _, filenames in os.walk(versions_root):
        for fn in filenames:
            if fn == "info.dat":
                file_path = os.path.join(dirpath, fn)
                try:
                    versions.append(read_info(file_path))
                except (ValueError, OSError):
                    pass  # Skip malformed files

    return versions
