"""Tests for the FilePatcher class — backup, copy, revert, marker operations."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from patcher.file_patcher import FilePatcher, PatchResult
from patcher.version_io import discover_versions

from .conftest import (
    PROJECT_ROOT, _PATCHES_ROOT, UE_INSTALL_DIR, VERSION_NAME,
    TARGET_FILE, MARKER_FILE, CUSTOM_SRC, ORIGINAL_SRC,
    VERSION_NAME, md5, _PATCHES_ROOT,
)


@pytest.fixture
def patcher() -> FilePatcher:
    return FilePatcher()


@pytest.fixture
def version():
    versions = discover_versions(str(_PATCHES_ROOT))
    v = next((x for x in versions if x.engine_version == VERSION_NAME), None)
    assert v is not None, f"Version {VERSION_NAME} not found"
    return v


@pytest.fixture
def all_versions():
    return discover_versions(str(_PATCHES_ROOT))


class TestMarker:
    """Marker file read/write/detect."""

    def test_write_and_read_marker(self, patcher):
        patcher.write_marker(str(UE_INSTALL_DIR), "test-version")
        assert MARKER_FILE.read_text().strip() == "test-version"

        read_back = patcher.read_marker(str(UE_INSTALL_DIR))
        assert read_back == "test-version"

    def test_read_marker_empty(self, patcher):
        if MARKER_FILE.exists():
            MARKER_FILE.unlink()
        assert patcher.read_marker(str(UE_INSTALL_DIR)) == ""


class TestApplyCustom:
    """Applying a custom engine version."""

    def test_apply_custom_success(self, patcher, version, all_versions):
        original_hash = md5(TARGET_FILE)
        result = patcher.apply_custom(
            version, all_versions, str(UE_INSTALL_DIR), str(_PATCHES_ROOT),
            source_mode=False,
        )
        assert result.success, f"failed: {result.message}"
        assert result.files_copied >= 1

        # File changed to custom
        assert md5(TARGET_FILE) == md5(CUSTOM_SRC)
        # Marker updated
        assert MARKER_FILE.read_text().strip() == VERSION_NAME

    def test_apply_custom_creates_backup(self, patcher, version, all_versions):
        backup_dir = _PATCHES_ROOT / VERSION_NAME / "_originals"
        target_rel = "Engine/Source/Editor/MainFrame/Private/HomeScreen/SHomeScreen.cpp"
        backup_path = backup_dir / target_rel

        result = patcher.apply_custom(
            version, all_versions, str(UE_INSTALL_DIR), str(_PATCHES_ROOT),
            source_mode=False,
        )
        assert result.success
        assert backup_path.exists(), f"Backup not found at {backup_path}"
        assert md5(backup_path) == md5(ORIGINAL_SRC)


class TestApplyDefault:
    """Reverting to default engine version."""

    def test_revert_success(self, patcher, version, all_versions):
        # Apply custom first so we have something to revert
        patcher.apply_custom(
            version, all_versions, str(UE_INSTALL_DIR), str(_PATCHES_ROOT),
            source_mode=False,
        )
        assert md5(TARGET_FILE) == md5(CUSTOM_SRC)

        # Now revert
        result = patcher.apply_default(
            version, all_versions, str(UE_INSTALL_DIR), str(_PATCHES_ROOT),
            source_mode=False,
        )
        assert result.success, f"failed: {result.message}"
        assert result.files_copied >= 1

        # File restored to original
        assert md5(TARGET_FILE) == md5(ORIGINAL_SRC)
        # Marker says default
        assert MARKER_FILE.read_text().strip() == "default"


class TestIsSourceFile:
    """_is_source_file helper — used during source-mode apply to filter binaries."""

    def test_cpp_is_source(self):
        from patcher.file_patcher import _is_source_file
        assert _is_source_file("Engine/Source/Mod/file.cpp") is True

    def test_h_is_source(self):
        from patcher.file_patcher import _is_source_file
        assert _is_source_file("Engine/Source/Mod/file.h") is True

    def test_dll_is_not_source(self):
        from patcher.file_patcher import _is_source_file
        assert _is_source_file("Engine/Binaries/Win64/Mod.dll") is False

    def test_pdb_is_not_source(self):
        from patcher.file_patcher import _is_source_file
        assert _is_source_file("Engine/Binaries/Win64/Mod.pdb") is False

    def test_empty_ext_is_not_source(self):
        from patcher.file_patcher import _is_source_file
        assert _is_source_file("Engine/Source/Mod/README") is False


class TestDetectAppliedVersion:
    """FilePatcher.detect_applied_version — marker-based version detection."""

    def test_reads_marker_value(self, target_file, marker_file):
        from patcher.file_patcher import FilePatcher
        from patcher.version_io import discover_versions
        from .conftest import _PATCHES_ROOT
        # Path: .../UE_5.7/Engine/Source/Editor/... -> UE root is 7 levels up from cpp
        ue_root = target_file.parents[6]
        versions = discover_versions(str(_PATCHES_ROOT))
        # Marker should be "default" from conftest hard_reset
        result = FilePatcher.detect_applied_version(str(ue_root), versions)
        assert result == "default"

    def test_returns_none_when_no_marker(self, tmp_path):
        from patcher.file_patcher import FilePatcher
        result = FilePatcher.detect_applied_version(str(tmp_path), [])
        assert result is None

    def test_matches_case_insensitive(self, tmp_path):
        from patcher.file_patcher import FilePatcher
        FilePatcher.write_marker(str(tmp_path), "UE_5.7-Test")
        from models import EngineInfo
        result = FilePatcher.detect_applied_version(str(tmp_path), [EngineInfo(engine_version="ue_5.7-test")])
        assert result == "ue_5.7-test"

    def test_accepts_unknown_marker(self, tmp_path):
        """An unrecognised marker value should still be returned as-is."""
        from patcher.file_patcher import FilePatcher
        FilePatcher.write_marker(str(tmp_path), "manual-edit")
        result = FilePatcher.detect_applied_version(str(tmp_path), [])
        assert result == "manual-edit"
