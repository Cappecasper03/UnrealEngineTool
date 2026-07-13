"""End-to-end integration tests — full workflow: apply custom, verify, revert, verify."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from patcher.patch_io import discover_patches
from patcher.file_patcher import FilePatcher, PatchResult

from .conftest import (
    PROJECT_ROOT, UE_INSTALL_DIR, PATCH_NAME,
    TARGET_FILE, MARKER_FILE, CUSTOM_SRC, ORIGINAL_SRC,
    md5, _PATCHES_ROOT,
)


def run(*args: str) -> tuple:
    """Run via subprocess (exercises main.py dispatch)."""
    env = {**os.environ, "UNREAL_ENGINE_TOOL_TEST": "1"}
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "src" / "main.py"), *args],
        capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        env=env,
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
        patches = discover_patches(str(_PATCHES_ROOT))
        p = next(x for x in patches if x.patch_name == PATCH_NAME)
        result = patcher.apply_custom(
            p, patches, str(UE_INSTALL_DIR), str(_PATCHES_ROOT),
            source_mode=False,
        )
        assert result.success
        assert MARKER_FILE.read_text().strip() == PATCH_NAME
        assert md5(TARGET_FILE) == md5(CUSTOM_SRC)

    def test_003_cli_list_shows_applied(self):
        rc, _, _ = run("list")
        assert rc == 0

    def test_004_revert(self):
        patcher = FilePatcher()
        patches = discover_patches(str(_PATCHES_ROOT))
        p = next(x for x in patches if x.patch_name == PATCH_NAME)
        result = patcher.apply_default(
            p, patches, str(UE_INSTALL_DIR), str(_PATCHES_ROOT),
            source_mode=False,
        )
        assert result.success
        assert MARKER_FILE.read_text().strip() == "default"
        assert md5(TARGET_FILE) == md5(ORIGINAL_SRC)

    def test_005_cli_apply_custom(self):
        rc, out, _ = run("apply-custom", PATCH_NAME, str(UE_INSTALL_DIR))
        assert rc == 0
        assert MARKER_FILE.read_text().strip() == PATCH_NAME
        assert md5(TARGET_FILE) == md5(CUSTOM_SRC)

    def test_006_cli_apply_default(self):
        rc, out, _ = run("apply-default", PATCH_NAME, str(UE_INSTALL_DIR))
        assert rc == 0
        assert MARKER_FILE.read_text().strip() == "default"
        assert md5(TARGET_FILE) == md5(ORIGINAL_SRC)

    def test_007_final_state_is_default(self):
        assert MARKER_FILE.read_text().strip() == "default"
        assert md5(TARGET_FILE) == md5(ORIGINAL_SRC)
