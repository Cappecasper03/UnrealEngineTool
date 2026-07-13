"""Tests for version_io — binary info.dat read/write, create, delete, discover."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from patcher.version_io import (
    read_info, write_info, discover_versions,
    create_version, delete_version,
)
from models import EngineFile, EngineInfo

from .conftest import VERSIONS_ROOT, VERSION_NAME


@pytest.fixture
def test_info_path() -> Path:
    return VERSIONS_ROOT / VERSION_NAME / "info.dat"


class TestReadInfo:
    """Reading the binary info.dat format."""

    def test_read_test_version(self, test_info_path):
        info = read_info(str(test_info_path))
        assert info.engine_version == VERSION_NAME
        assert info.unreal_version == "5.7"
        assert len(info.files) == 1

    def test_file_entries_have_paths(self, test_info_path):
        info = read_info(str(test_info_path))
        fe = info.files[0]
        assert "SHomeScreen.cpp" in fe.path_target
        assert fe.path_custom != ""
        assert fe.path_default != ""


class TestDiscoverVersions:
    """Version discovery from directory."""

    def test_discover_finds_test_version(self):
        versions = discover_versions(str(VERSIONS_ROOT))
        names = [v.engine_version for v in versions]
        assert VERSION_NAME in names

    def test_discover_empty_directory(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        versions = discover_versions(str(empty))
        assert versions == []

    def test_discover_nonexistent_directory(self):
        versions = discover_versions("D:/nonexistent_versions")
        assert versions == []


class TestCreateDeleteVersion:
    """Creating and deleting engine versions."""

    def test_create_and_delete(self, tmp_path):
        ver_dir = tmp_path / "TestCreate"
        # Create
        info = create_version(str(tmp_path), "TestCreate", unreal_version="5.7")
        assert info.engine_version == "TestCreate"
        assert (tmp_path / "TestCreate" / "info.dat").exists()

        # Read back
        info2 = read_info(str(tmp_path / "TestCreate" / "info.dat"))
        assert info2.engine_version == "TestCreate"

        # Delete
        delete_version(info)
        assert not (tmp_path / "TestCreate").exists()

    def test_create_with_clone(self, tmp_path):
        # Create original
        orig = create_version(str(tmp_path), "Orig", unreal_version="5.7")
        orig.files.append(EngineFile(
            path_custom="a.cpp", path_default="a.cpp", path_target="Engine/a.cpp",
        ))
        write_info(orig)

        # Clone
        cloned = create_version(
            str(tmp_path), "Clone", unreal_version="5.7",
            clone_from=orig,
        )
        assert len(cloned.files) == 1
        assert cloned.files[0].path_custom == "a.cpp"

    def test_create_duplicate_raises(self, tmp_path):
        create_version(str(tmp_path), "Dup")
        with pytest.raises(FileExistsError):
            create_version(str(tmp_path), "Dup")
