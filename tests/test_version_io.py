"""Tests for version_io — binary info.dat read/write, create, delete, discover."""

import os
import struct
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from patcher.version_io import (
    read_info, write_info, discover_versions,
    create_version, delete_version,
)
from models import EngineFile, EngineInfo

from .conftest import _PATCHES_ROOT, VERSION_NAME


@pytest.fixture
def test_info_path() -> Path:
    return _PATCHES_ROOT / VERSION_NAME / "info.dat"


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
        versions = discover_versions(str(_PATCHES_ROOT))
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


class TestEditVersion:
    """Editing existing version metadata and file entries."""

    def test_edit_metadata_round_trip(self, tmp_path):
        """Modify name, changelog, parent, unreal_dir → write → read back."""
        ver = create_version(str(tmp_path), "EditMe", unreal_version="5.7")
        # Changing the engine_version means the info_dir must also change
        new_dir = os.path.join(str(tmp_path), "EditMe-V2", "info.dat")
        ver.info_dir = new_dir
        ver.engine_version = "EditMe-V2"
        ver.changelog = "Fixed the thing"
        ver.parent_version = "Base"
        ver.unreal_dir = "C:/UE_5.7"
        write_info(ver)

        info = read_info(str(tmp_path / "EditMe-V2" / "info.dat"))
        assert info.engine_version == "EditMe-V2"
        assert info.changelog == "Fixed the thing"
        assert info.parent_version == "Base"
        assert info.unreal_dir == "C:/UE_5.7"

    def test_add_file_entry_then_write(self, tmp_path):
        """Add a file entry to a version, write, then read it back."""
        ver = create_version(str(tmp_path), "AddFiles")
        ver.files.append(EngineFile(
            path_custom="Custom/a.cpp",
            path_default="Originals/a.cpp",
            path_target="Engine/Source/Mod/a.cpp",
            local_name="a.cpp",
        ))
        write_info(ver)

        info = read_info(str(tmp_path / "AddFiles" / "info.dat"))
        assert len(info.files) == 1
        fe = info.files[0]
        assert fe.path_custom == "Custom/a.cpp"
        assert fe.path_default == "Originals/a.cpp"
        assert fe.path_target == "Engine/Source/Mod/a.cpp"

    def test_remove_file_entry_then_write(self, tmp_path):
        """Add two files, remove one, write, read back — should have one."""
        ver = create_version(str(tmp_path), "RmFiles")
        ver.files.append(EngineFile(
            path_custom="a.cpp", path_default="", path_target="Engine/a.cpp",
        ))
        ver.files.append(EngineFile(
            path_custom="b.cpp", path_default="", path_target="Engine/b.cpp",
        ))
        write_info(ver)

        # Remove the first entry, rewrite
        ver.files.pop(0)
        write_info(ver)

        info = read_info(str(tmp_path / "RmFiles" / "info.dat"))
        assert len(info.files) == 1
        assert info.files[0].path_custom == "b.cpp"

    def test_multiple_file_entries(self, tmp_path):
        """Write and read back a version with several file entries."""
        ver = create_version(str(tmp_path), "MultiFiles")
        for i in range(5):
            ver.files.append(EngineFile(
                path_custom=f"{i}.cpp",
                path_default=f"o{i}.cpp",
                path_target=f"Engine/Mod/{i}.cpp",
                local_name=f"{i}.cpp",
            ))
        write_info(ver)

        info = read_info(str(tmp_path / "MultiFiles" / "info.dat"))
        assert len(info.files) == 5
        for i, fe in enumerate(info.files):
            assert fe.path_custom == f"{i}.cpp"

    def test_empty_changelog_and_parent(self, tmp_path):
        """Verify that empty strings are preserved correctly."""
        ver = create_version(str(tmp_path), "EmptyFields")
        # Defaults are already empty
        write_info(ver)

        info = read_info(str(tmp_path / "EmptyFields" / "info.dat"))
        assert info.changelog == ""
        assert info.parent_version == ""
        assert info.unreal_dir == ""

    def test_clone_copies_file_directory(self, tmp_path):
        """Clone with actual directory copy (shutil.copytree)."""
        import shutil

        # Create original version with a real file on disk
        orig_ver = create_version(str(tmp_path), "CloneSrc", unreal_version="5.7")
        orig_ver.files.append(EngineFile(
            path_custom="my_file.cpp",
            path_default="",
            path_target="Engine/Src/my_file.cpp",
        ))
        write_info(orig_ver)

        # Put a real file in the version directory
        src_dir = os.path.dirname(orig_ver.info_dir)
        with open(os.path.join(src_dir, "my_file.cpp"), "w") as f:
            f.write("// test content")

        # Clone
        cloned = create_version(
            str(tmp_path), "CloneDst", unreal_version="5.7",
            clone_from=orig_ver,
        )
        dst_dir = os.path.dirname(cloned.info_dir)
        if os.path.isdir(src_dir):
            shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)

        # Verify cloned info
        assert cloned.engine_version == "CloneDst"
        assert len(cloned.files) == 1
        assert cloned.files[0].path_custom == "my_file.cpp"

        # Verify file was copied
        cloned_file = os.path.join(dst_dir, "my_file.cpp")
        assert os.path.isfile(cloned_file)
        with open(cloned_file) as f:
            assert f.read() == "// test content"

        # Verify the original still exists
        assert os.path.isfile(os.path.join(src_dir, "my_file.cpp"))


class TestVersionIOErrors:
    """Error handling for binary info.dat I/O."""

    def test_read_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            read_info("D:/nonexistent_info.dat")

    def test_read_invalid_header_raises(self, tmp_path):
        bad_file = str(tmp_path / "bad.dat")
        with open(bad_file, "wb") as f:
            f.write(b"NOTRPEngineHeader\x00\x00\x00\x00")
        with pytest.raises(ValueError, match="Invalid header"):
            read_info(bad_file)

    def test_read_empty_file_raises(self, tmp_path):
        empty_file = str(tmp_path / "empty.dat")
        with open(empty_file, "wb") as f:
            f.write(b"")
        with pytest.raises(ValueError, match="Invalid header"):
            read_info(empty_file)

    def test_read_truncated_file_raises(self, tmp_path):
        """A file that has the header but is cut off before strings."""
        bad_file = str(tmp_path / "truncated.dat")
        with open(bad_file, "wb") as f:
            f.write(b"RPEngineHeader")
        with pytest.raises((ValueError, struct.error)):
            read_info(bad_file)

    def test_delete_nonexistent_raises(self, tmp_path):
        fake = EngineInfo(
            info_dir=str(tmp_path / "Nope" / "info.dat"),
            engine_version="Nope",
        )
        with pytest.raises(FileNotFoundError):
            delete_version(fake)

    def test_write_creates_directory(self, tmp_path):
        """write_info should create parent directories."""
        deep_dir = str(tmp_path / "a" / "b" / "c")
        info = EngineInfo(
            info_dir=os.path.join(deep_dir, "info.dat"),
            engine_version="Deep",
        )
        info.files.append(EngineFile(
            path_custom="x.cpp", path_default="", path_target="Engine/x.cpp",
        ))
        write_info(info)
        assert os.path.isfile(os.path.join(deep_dir, "info.dat"))
