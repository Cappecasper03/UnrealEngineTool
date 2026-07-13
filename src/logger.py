"""Application-wide logger — writes to file (always) and stdout (CLI mode).

Log file: %LOCALAPPDATA%/UnrealEngineTool/logs/UnrealEngineTool.log
A copy-and-clear rotation scheme is used:
  - The active log is always UnrealEngineTool.log (same file entry).
  - On startup, any existing UnrealEngineTool.log is COPIED to
    UnrealEngineTool-backup-YYYY.MM.DD-HH.MM.SS.log, then the original
    file is truncated.  Because the same file entry stays open, text
    editors/viewers tailing the log don't need to re-open or switch files.
CLI mode adds a stdout handler for interactive use.
"""

import logging
import os
import shutil
import sys
from datetime import datetime
from typing import Optional

_LOG_DIR: Optional[str] = None
_FILE_HANDLER: Optional[logging.FileHandler] = None
_STDOUT_HANDLER: Optional[logging.StreamHandler] = None
_INITIALISED = False

_FORMAT = "%(asctime)s  %(levelname)-5s  %(relpath)s  %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

_LOG_FILENAME = "UnrealEngineTool"
_LOG_EXT = ".log"

# Resolve the project root once (parent of src/)
_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


class _RelPathFormatter(logging.Formatter):
    """Formatter that replaces %(relpath)s with the file path relative to the project root."""

    def format(self, record: logging.LogRecord) -> str:
        # Compute relative path from the caller's source file
        full = record.pathname
        try:
            rel = os.path.relpath(full, _PROJECT_ROOT)
        except ValueError:
            rel = full  # fallback: different drive on Windows
        record.relpath = rel.replace("\\", "/")
        return super().format(record)


def _default_log_dir() -> str:
    """Resolve %LOCALAPPDATA%/UnrealEngineTool/logs."""
    return os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "UnrealEngineTool",
        "logs",
    )


def default_patches_root() -> str:
    """Resolve %LOCALAPPDATA%/UnrealEngineTool/patches."""
    return os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "UnrealEngineTool",
        "patches",
    )


def _backup_timestamp() -> str:
    """Return a UE5-style backup timestamp: YYYY.MM.DD-HH.MM.SS."""
    return datetime.now().strftime("%Y.%m.%d-%H.%M.%S")


def _rotate_existing_log(log_dir: str) -> None:
    """Copy an existing UnrealEngineTool.log to a backup, then truncate the original.

    Copying instead of renaming keeps the same file entry active so that text
    editors/viewers tailing the log can continue watching the same file.

    Skips rotation if the active file is empty or if UNREAL_ENGINE_TOOL_TEST
    is set (avoids creating pointless backups from test subprocesses).
    """
    active_path = os.path.join(log_dir, _LOG_FILENAME + _LOG_EXT)
    if not os.path.isfile(active_path):
        return
    # Don't back up an empty file (already truncated by a previous init)
    if os.path.getsize(active_path) == 0:
        return
    # Skip rotation in test subprocesses
    if os.environ.get("UNREAL_ENGINE_TOOL_TEST"):
        return
    ts = _backup_timestamp()
    backup_name = f"{_LOG_FILENAME}-backup-{ts}{_LOG_EXT}"
    backup_path = os.path.join(log_dir, backup_name)
    try:
        shutil.copy2(active_path, backup_path)
        # Truncate the active file in-place (same file entry)
        with open(active_path, "w") as f:
            pass
    except OSError:
        # If we can't rotate (permissions, etc.), just overwrite the file
        pass


def _init():
    """One-time initialisation of the file log handler.

    Copies any existing log to a timestamped backup, then truncates the
    active file so the same file entry stays valid for viewers.
    """
    global _FILE_HANDLER, _INITIALISED, _LOG_DIR
    if _INITIALISED:
        return

    log_dir = _default_log_dir()
    log_path_ = os.path.join(log_dir, _LOG_FILENAME + _LOG_EXT)

    # Create directory if needed
    _LOG_DIR = log_dir
    if not os.path.isdir(_LOG_DIR):
        try:
            os.makedirs(_LOG_DIR, exist_ok=True)
        except OSError:
            _LOG_DIR = os.path.expanduser("~")
            log_path_ = os.path.join(_LOG_DIR, _LOG_FILENAME + _LOG_EXT)
        else:
            # Directory was just created — nothing to rotate
            pass
    else:
        # Directory exists — rotate old log if present
        _rotate_existing_log(_LOG_DIR)

    _FILE_HANDLER = logging.FileHandler(log_path_, encoding="utf-8")
    _FILE_HANDLER.setLevel(logging.DEBUG)
    _FILE_HANDLER.setFormatter(_RelPathFormatter(_FORMAT, _DATE_FMT))

    root_logger = logging.getLogger("unrealenginetool")
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(_FILE_HANDLER)

    _INITIALISED = True


def get_logger(name: str) -> logging.Logger:
    """Get a application logger. Always logs to file; CLI can also enable stdout."""
    _init()
    logger = logging.getLogger(f"unrealenginetool.{name}")
    logger.setLevel(logging.DEBUG)
    return logger


def enable_stdout(level: int = logging.INFO):
    """Add a stdout handler for CLI mode. Safe to call multiple times."""
    global _STDOUT_HANDLER
    _init()
    if _STDOUT_HANDLER is not None:
        return
    _STDOUT_HANDLER = logging.StreamHandler(sys.stdout)
    _STDOUT_HANDLER.setLevel(level)
    _STDOUT_HANDLER.setFormatter(_RelPathFormatter(
        "%(asctime)s  %(levelname)-5s  %(message)s", _DATE_FMT,
    ))
    root_logger = logging.getLogger("unrealenginetool")
    root_logger.addHandler(_STDOUT_HANDLER)


def log_path() -> str:
    """Return the current log file path, or empty string if uninitialised."""
    if _FILE_HANDLER is None:
        return ""
    return _FILE_HANDLER.baseFilename  # type: ignore[attr-defined]
