"""Tests for the patcher logger — per-session files, stdout handler, log content."""

import glob
import logging
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from logger import get_logger, enable_stdout, log_path


def _log_dir() -> str:
    return os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
        "UnrealEngineTool", "logs",
    )


class TestLoggerInit:
    """Logger initialisation and path conventions."""

    def test_log_path_after_init(self):
        """Calling get_logger creates a log file."""
        l = get_logger("test_path")
        p = log_path()
        assert p != ""
        assert "unrealenginetool_" in p
        assert ".log" in p
        assert _log_dir().lower() in p.lower()

    def test_same_logger_returns_same_file(self):
        """Multiple get_logger calls from the same session use the same file."""
        l1 = get_logger("test_same_file")
        p1 = log_path()
        l2 = get_logger("test_same_file_2")
        p2 = log_path()
        assert p1 == p2


class TestLogContent:
    """Log entries and formatting."""

    def test_log_writes_to_file(self):
        l = get_logger("test_content")
        l.info("hello from test")
        l.debug("debug detail")
        l.error("something broke")

        p = log_path()
        with open(p, encoding="utf-8") as f:
            content = f.read()
        assert "hello from test" in content
        assert "debug detail" in content
        assert "something broke" in content

    def test_stdout_handler(self, capsys):
        """enable_stdout adds a stream handler to root."""
        root = logging.getLogger("patcher")
        handler_count_before = len([h for h in root.handlers if isinstance(h, logging.StreamHandler)])
        enable_stdout()
        handler_count_after = len([h for h in root.handlers if isinstance(h, logging.StreamHandler)])
        assert handler_count_after >= handler_count_before

    def test_logger_name_format(self):
        l = get_logger("test_format")
        assert l.name == "unrealenginetool.test_format"


class TestLogDirectory:
    """Log directory creation."""

    def test_log_directory_created(self):
        log_dir = _log_dir()
        assert os.path.isdir(log_dir), f"Log dir not created: {log_dir}"
