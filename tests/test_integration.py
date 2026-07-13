"""End-to-end integration tests — full workflow: apply custom, verify, revert, verify."""

import subprocess
import sys
from pathlib import Path

import pytest

from patcher.file_patcher import FilePatcher, PatchResult
from patcher.version_io import discover_versions

from .conftest import (
    PROJECT_ROOT, UE_INSTALL_DIR, VERSION_NAME,
    TARGET_FILE, MARKER_FILE, CUSTOM_SRC, ORIGINAL_SRC,
    md5, _PATCHES_ROOT,
)


def run(*args: str) -> tuple:
    """Run via subprocess (exercises main.py dispatch)."""
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "main.py"), *args],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


@pytest.mark.order(1)
class TestFullWorkflow:
    """Complete apply → verify → revert → verify cycle."""

    def test_001_initial_state_is_default(self):
        assert MARKER_FILE.read_text().strip() == "default"
        assert md5(TARGET_FILE) == md5(ORIGINAL_SRC)

    def test_002_apply_custom(self):
        patcher = FilePatcher()
        versions = discover_versions(str(_PATCHES_ROOT))
        v = next(x for x in versions if x.engine_version == VERSION_NAME)
        result = patcher.apply_custom(
            v, versions, str(UE_INSTALL_DIR), str(_PATCHES_ROOT),
            source_mode=False,
        )
        assert result.success
        assert MARKER_FILE.read_text().strip() == VERSION_NAME
        assert md5(TARGET_FILE) == md5(CUSTOM_SRC)

    def test_003_cli_list_shows_applied(self):
        rc, _, _ = run("list")
        assert rc == 0

    def test_004_revert(self):
        patcher = FilePatcher()
        versions = discover_versions(str(_PATCHES_ROOT))
        v = next(x for x in versions if x.engine_version == VERSION_NAME)
        result = patcher.apply_default(
            v, versions, str(UE_INSTALL_DIR), str(_PATCHES_ROOT),
            source_mode=False,
        )
        assert result.success
        assert MARKER_FILE.read_text().strip() == "default"
        assert md5(TARGET_FILE) == md5(ORIGINAL_SRC)

    def test_005_cli_apply_custom(self):
        rc, out, _ = run("apply-custom", VERSION_NAME, str(UE_INSTALL_DIR))
        assert rc == 0
        assert MARKER_FILE.read_text().strip() == VERSION_NAME
        assert md5(TARGET_FILE) == md5(CUSTOM_SRC)

    def test_006_cli_apply_default(self):
        rc, out, _ = run("apply-default", VERSION_NAME, str(UE_INSTALL_DIR))
        assert rc == 0
        assert MARKER_FILE.read_text().strip() == "default"
        assert md5(TARGET_FILE) == md5(ORIGINAL_SRC)

    def test_007_final_state_is_default(self):
        assert MARKER_FILE.read_text().strip() == "default"
        assert md5(TARGET_FILE) == md5(ORIGINAL_SRC)
