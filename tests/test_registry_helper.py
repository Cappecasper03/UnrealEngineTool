"""Tests for registry_helper — filesystem fallback for UE installation discovery.

The registry-dependent functions (_from_registry_builds, _from_registry_installed_dirs)
can only be tested on actual Windows machines with UE installed. These tests cover the
filesystem fallback path which is testable in any environment.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from registry_helper import _from_common_filesystem


class TestFromCommonFilesystem:
    """Filesystem fallback — scanning well-known Epic Games directories."""

    def test_returns_empty_when_no_dirs_exist(self, tmp_path, monkeypatch):
        """Patch COMMON_UE_ROOTS to a non-existent temp dir."""
        nonexistent = str(tmp_path / "nonexistent")
        monkeypatch.setattr(
            "registry_helper._COMMON_UE_ROOTS",
            [nonexistent],
        )
        result = _from_common_filesystem()
        assert result == []

    def test_finds_ue_dirs(self, tmp_path, monkeypatch):
        """Create a directory with a UE_* folder."""
        test_root = tmp_path / "Epic Games"
        test_root.mkdir(parents=True)
        (test_root / "UE_5.7").mkdir()
        (test_root / "UE_5.8").mkdir()
        (test_root / "NotUE").mkdir()  # Should be ignored

        monkeypatch.setattr(
            "registry_helper._COMMON_UE_ROOTS",
            [str(test_root)],
        )
        result = _from_common_filesystem()
        assert len(result) == 2
        assert any("UE_5.7" in p for p in result)
        assert any("UE_5.8" in p for p in result)
        assert all("NotUE" not in p for p in result)

    def test_deduplication(self, tmp_path, monkeypatch):
        """Dedup happens in discover_ue_installations, not _from_common_filesystem."""
        test_root = tmp_path / "Epic Games"
        test_root.mkdir(parents=True)
        (test_root / "UE_5.7").mkdir()

        monkeypatch.setattr(
            "registry_helper._COMMON_UE_ROOTS",
            [str(test_root), str(test_root)],  # Same root twice
        )
        result = _from_common_filesystem()
        # _from_common_filesystem doesn't dedup — that's the parent's job
        assert len(result) == 2

    def test_handles_permission_error(self, tmp_path, monkeypatch):
        """PermissionError on a directory should be silently skipped."""
        import stat
        test_root = tmp_path / "Epic Games"
        test_root.mkdir(parents=True)
        (test_root / "UE_5.7").mkdir()
        restricted = test_root / "Restricted"
        restricted.mkdir()
        os.chmod(str(restricted), 0o000)  # No permissions

        monkeypatch.setattr(
            "registry_helper._COMMON_UE_ROOTS",
            [str(test_root)],
        )
        try:
            result = _from_common_filesystem()
            assert len(result) >= 1  # Should still find UE_5.7
        finally:
            os.chmod(str(restricted), stat.S_IRWXU)  # Restore for cleanup
