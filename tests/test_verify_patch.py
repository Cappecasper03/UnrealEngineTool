"""Tests for verify_patch — verifying UE installation state against a patch version."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from verify_patch import verify, md5
from patcher.file_patcher import FilePatcher
from patcher.version_io import create_version
from models import EngineFile


class TestVerifyMd5:
    """md5 helper."""

    def test_md5_known_value(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        h = md5(str(f))
        assert h == "5d41402abc4b2a76b9719d911017c592"

    def test_md5_different_files(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("same")
        b.write_text("different")
        assert md5(str(a)) != md5(str(b))


class TestVerifyFunction:
    """verify() function — compares marker + file hashes."""

    def test_returns_false_for_nonexistent_ue_dir(self):
        ok, msg = verify("D:/nonexistent_ue_dir", "some-version", verbose=False)
        assert ok is False
        assert "does not exist" in msg

    def test_marker_mismatch(self, tmp_path):
        """Expected version doesn't match the marker file."""
        FilePatcher.write_marker(str(tmp_path), "applied-v1")
        # Override patches root to empty so discover_versions returns []
        from logger import default_patches_root
        import logging
        logging.getLogger("unrealenginetool.verify_patch").setLevel(logging.CRITICAL)
        ok, msg = verify(str(tmp_path), "expected-v2", verbose=False)
        assert ok is False
        assert "Marker mismatch" in msg

    def test_default_marker_passes(self, tmp_path):
        """If expected is 'default' and marker says 'default', pass."""
        FilePatcher.write_marker(str(tmp_path), "default")
        ok, msg = verify(str(tmp_path), "default", verbose=False)
        assert ok is True
        assert "default state" in msg

    def test_no_files_to_verify(self, tmp_path):
        """Version with no file entries should pass."""
        import verify_patch as vp
        original_get_root = vp._get_versions_root
        vp._get_versions_root = lambda: str(tmp_path)

        from patcher.version_io import create_version
        ver = create_version(str(tmp_path), "EmptyVersion")
        try:
            FilePatcher.write_marker(str(tmp_path), "EmptyVersion")
            ok, msg = vp.verify(str(tmp_path), "EmptyVersion", verbose=False)
            assert ok is True
            assert "no file entries" in msg
        finally:
            vp._get_versions_root = original_get_root

    def test_files_match(self, tmp_path):
        """All file hashes match — passes."""
        import verify_patch as vp
        original_get_root = vp._get_versions_root
        vp._get_versions_root = lambda: str(tmp_path)

        ver_name = "MatchTest"
        from patcher.version_io import create_version
        from models import EngineFile
        ver = create_version(str(tmp_path), ver_name)
        ver.files.append(EngineFile(
            path_custom="my_file.cpp",
            path_target="Engine/Target/my_file.cpp",
        ))
        from patcher.version_io import write_info
        write_info(ver)

        # Create files on disk
        ver_dir = tmp_path / ver_name
        (ver_dir / "my_file.cpp").write_text("expected content")
        target = tmp_path / "Engine" / "Target" / "my_file.cpp"
        target.parent.mkdir(parents=True)
        target.write_text("expected content")

        try:
            FilePatcher.write_marker(str(tmp_path), ver_name)
            ok, msg = vp.verify(str(tmp_path), ver_name, verbose=False)
            assert ok is True
            assert "match" in msg
        finally:
            vp._get_versions_root = original_get_root

    def test_files_mismatch(self, tmp_path):
        """File content differs — fails."""
        import verify_patch as vp
        original_get_root = vp._get_versions_root
        vp._get_versions_root = lambda: str(tmp_path)

        ver_name = "MismatchTest"
        from patcher.version_io import create_version
        from models import EngineFile
        ver = create_version(str(tmp_path), ver_name)
        ver.files.append(EngineFile(
            path_custom="file.cpp",
            path_target="Engine/Target/file.cpp",
        ))
        from patcher.version_io import write_info
        write_info(ver)

        ver_dir = tmp_path / ver_name
        (ver_dir / "file.cpp").write_text("expected")
        target = tmp_path / "Engine" / "Target" / "file.cpp"
        target.parent.mkdir(parents=True)
        target.write_text("DIFFERENT content")

        try:
            FilePatcher.write_marker(str(tmp_path), ver_name)
            ok, msg = vp.verify(str(tmp_path), ver_name, verbose=False)
            assert ok is False
            assert "MISMATCH" in msg or "FAILED" in msg
        finally:
            vp._get_versions_root = original_get_root
