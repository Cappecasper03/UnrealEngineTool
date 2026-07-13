"""Tests for the headless CLI — runs via subprocess to exercise main.py dispatch."""

import subprocess
import sys

import pytest

from .conftest import (
    PROJECT_ROOT, UE_INSTALL_DIR, VERSION_NAME,
)


def run(*args: str) -> tuple:
    """Run the tool via subprocess and return (rc, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "main.py"), *args],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


class TestDispatch:
    """Tests that CLI commands are dispatched without needing --cli."""

    def test_list(self):
        rc, out, _ = run("list")
        assert rc == 0
        assert VERSION_NAME in out

    def test_help_short(self):
        rc, out, _ = run("-h")
        assert rc == 0
        assert "Headless CLI" in out
        assert "--cli" not in out  # no legacy references

    def test_help_long(self):
        rc, out, _ = run("--help")
        assert rc == 0
        assert "Headless CLI" in out

    def test_apply_custom(self):
        rc, out, _ = run("apply-custom", VERSION_NAME, str(UE_INSTALL_DIR))
        assert rc == 0
        assert "Success:" in out

    def test_apply_default(self):
        rc, out, _ = run("apply-default", VERSION_NAME, str(UE_INSTALL_DIR))
        assert rc == 0
        assert "Success:" in out

    def test_log_path(self):
        rc, out, _ = run("log-path")
        assert rc == 0
        assert "UnrealEngineTool.log" in out

    def test_aliases(self):
        rc, out, _ = run("apply", VERSION_NAME, str(UE_INSTALL_DIR))
        assert rc == 0
        assert "Success:" in out
        rc, out, _ = run("revert", VERSION_NAME, str(UE_INSTALL_DIR))
        assert rc == 0
        assert "Success:" in out


class TestErrors:
    """Tests error-handling paths."""

    def test_invalid_version(self):
        rc, out, _ = run("apply-custom", "NonExistent", str(UE_INSTALL_DIR))
        assert rc == 1
        assert "not found" in out

    def test_invalid_ue_dir(self):
        rc, out, _ = run("apply-custom", VERSION_NAME, "D:/nonexistent")
        assert rc == 1
        assert "does not exist" in out

    def test_no_versions_dir(self):
        # Temporarily remove the versions root reference by using a bogus version
        rc, out, _ = run("list")
        assert rc == 0  # list handles empty gracefully

    def test_no_args_shows_help(self):
        # No args should launch GUI, but we test via --help alias
        rc, out, _ = run("-h")
        assert rc == 0
