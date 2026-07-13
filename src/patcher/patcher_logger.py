"""Logger setup for the patcher — writes to file (always) and stdout (CLI mode).

Log file: %LOCALAPPDATA%/UnrealEngineTool/logs/patcher_<timestamp>.log
A new file is created per session. CLI mode adds a stdout handler for interactive use.
"""

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

_LOG_DIR: Optional[str] = None
_FILE_HANDLER: Optional[logging.FileHandler] = None
_STDOUT_HANDLER: Optional[logging.StreamHandler] = None
_INITIALISED = False

_FORMAT = "%(asctime)s  %(levelname)-5s  %(name)s  %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


def _default_log_dir() -> str:
    """Resolve %LOCALAPPDATA%/UnrealEngineTool/logs."""
    return os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "UnrealEngineTool",
        "logs",
    )


def _session_timestamp() -> str:
    """Return a compact, sortable timestamp for this session."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _init():
    """One-time initialisation of the file log handler."""
    global _FILE_HANDLER, _INITIALISED, _LOG_DIR
    if _INITIALISED:
        return

    log_dir = _default_log_dir()
    ts = _session_timestamp()
    log_path = os.path.join(log_dir, f"patcher_{ts}.log")

    # Create directory if needed
    _LOG_DIR = log_dir
    if not os.path.isdir(_LOG_DIR):
        try:
            os.makedirs(_LOG_DIR, exist_ok=True)
        except OSError:
            _LOG_DIR = os.path.expanduser("~")
            log_path = os.path.join(_LOG_DIR, f"patcher_{ts}.log")

    _FILE_HANDLER = logging.FileHandler(log_path, encoding="utf-8")
    _FILE_HANDLER.setLevel(logging.DEBUG)
    _FILE_HANDLER.setFormatter(logging.Formatter(_FORMAT, _DATE_FMT))

    root_logger = logging.getLogger("patcher")
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(_FILE_HANDLER)

    _INITIALISED = True


def get_logger(name: str) -> logging.Logger:
    """Get a patcher logger. Always logs to file; CLI can also enable stdout."""
    _init()
    logger = logging.getLogger(f"patcher.{name}")
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
    _STDOUT_HANDLER.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-5s  %(message)s", _DATE_FMT,
    ))
    root_logger = logging.getLogger("patcher")
    root_logger.addHandler(_STDOUT_HANDLER)


def log_path() -> str:
    """Return the current log file path, or empty string if uninitialised."""
    if _FILE_HANDLER is None:
        return ""
    return _FILE_HANDLER.baseFilename  # type: ignore[attr-defined]
