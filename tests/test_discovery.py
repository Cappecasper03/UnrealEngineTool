"""Tests for auto-discovery helpers: binary matching, intermediate scanning, path relativisation."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from patcher.version_dialog import (
    _discover_binaries,
    _discover_module_intermediates,
    _relativise,
    _find_engine_root,
    _module_name_from_path,
)


class TestRelativise:
    """Path-to-engine-relative conversion."""

    def test_engine_subdir_path(self):
        rel = _relativise("D:/UE_5.7/Engine/Source/Runtime/Core.cpp")
        assert rel == "Engine/Source/Runtime/Core.cpp"

    def test_engine_subdir_with_backslashes(self):
        rel = _relativise("D:\\UE_5.7\\Engine\\Source\\Runtime\\Core.cpp")
        assert rel == "Engine/Source/Runtime/Core.cpp"

    def test_basename_when_no_engine_dir(self):
        rel = _relativise("C:/somewhere/else/file.cpp")
        assert rel == "file.cpp"

    def test_with_version_dir_prefix(self, tmp_path):
        ver_dir = str(tmp_path / "v1.0")
        path = os.path.join(ver_dir, "Engine/Source/Runtime/Core.cpp")
        rel = _relativise(path, version_dir=ver_dir)
        assert rel == "Engine/Source/Runtime/Core.cpp"

    def test_case_insensitive_engine(self):
        rel = _relativise("D:/UE_5.7/ENGINE/Source/Runtime/Core.cpp")
        # _relativise preserves the original casing after the match
        assert "Engine/" in rel or "ENGINE/" in rel
        assert "Source/Runtime/Core.cpp" in rel


class TestFindEngineRoot:
    """Extracting UE installation root from a file path."""

    def test_typical_engine_path(self):
        root = _find_engine_root("D:/UE_5.7/Engine/Source/Runtime/Core.cpp")
        assert root == "D:/UE_5.7"

    def test_with_backslashes(self):
        root = _find_engine_root("D:\\UE_5.7\\Engine\\Source\\Runtime\\Core.cpp")
        assert root == "D:/UE_5.7"

    def test_no_engine_dir(self):
        root = _find_engine_root("C:/somewhere/else/file.cpp")
        assert root == ""

    def test_root_is_engine_dir(self):
        """_find_engine_root needs a path component after /Engine/ to extract root."""
        root = _find_engine_root("D:/UE_5.7/Engine/Source")
        assert root == "D:/UE_5.7"

    def test_case_insensitive_engine_root(self):
        root = _find_engine_root("D:/UE_5.7/ENGINE/Source")
        assert root == "D:/UE_5.7"


class TestModuleNameFromPath:
    """Extracting the UE module name from source paths."""

    def test_standard_module_path(self):
        mod = _module_name_from_path("Engine/Source/Runtime/Core/Private/Core.cpp")
        assert mod == "Core"

    def test_deep_module_path(self):
        mod = _module_name_from_path("Engine/Source/Editor/MainFrame/Private/Window.cpp")
        assert mod == "MainFrame"

    def test_developer_path(self):
        mod = _module_name_from_path("Engine/Source/Developer/DesktopPlatform/Private/DesktopPlatform.cpp")
        assert mod == "DesktopPlatform"

    def test_short_path_returns_empty(self):
        mod = _module_name_from_path("Engine/Source/Runtime")
        assert mod == ""

    def test_non_source_path_returns_empty(self):
        mod = _module_name_from_path("Engine/Binaries/Win64/foo.dll")
        assert mod == ""

    def test_outside_engine_returns_empty(self):
        mod = _module_name_from_path("Other/Source/Module/file.cpp")
        assert mod == ""


class TestDiscoverBinaries:
    """Auto-discovery of module binaries from Engine/Binaries/Win64."""

    @pytest.fixture
    def fake_engine(self, tmp_path):
        """Create a fake UE root with binaries."""
        engine = tmp_path / "UE_Test"
        bin_dir = engine / "Engine" / "Binaries" / "Win64"
        bin_dir.mkdir(parents=True)
        # Create module binaries
        for module, ext in [("Core", ".dll"), ("Core", ".pdb"), ("Core", ".lib"),
                            ("Core", ".target"),
                            ("MainFrame", ".dll"), ("MainFrame", ".pdb"),
                            ("OtherMod", ".dll")]:
            (bin_dir / f"UnrealEditor-{module}{ext}").write_text("fake")
        # Create a non-module file that should be ignored
        (bin_dir / "something_else.txt").write_text("ignore")
        return str(engine)

    def test_finds_matching_binaries(self, fake_engine):
        results = _discover_binaries(fake_engine, {"Core"})
        rels = [r[0] for r in results]
        assert "Engine/Binaries/Win64/UnrealEditor-Core.dll" in rels
        assert "Engine/Binaries/Win64/UnrealEditor-Core.pdb" in rels
        assert "Engine/Binaries/Win64/UnrealEditor-Core.lib" in rels
        assert "Engine/Binaries/Win64/UnrealEditor-Core.target" in rels

    def test_excludes_other_modules(self, fake_engine):
        results = _discover_binaries(fake_engine, {"Core"})
        rels = [r[0] for r in results]
        assert all("MainFrame" not in r for r in rels)
        assert all("OtherMod" not in r for r in rels)

    def test_multiple_modules(self, fake_engine):
        results = _discover_binaries(fake_engine, {"Core", "MainFrame"})
        assert len(results) >= 6  # at least Core(4) + MainFrame(2)

    def test_empty_source_modules_returns_empty(self, fake_engine):
        results = _discover_binaries(fake_engine, set())
        assert results == []

    def test_nonexistent_bin_dir(self, tmp_path):
        results = _discover_binaries(str(tmp_path / "nowhere"), {"Core"})
        assert results == []

    def test_excludes_non_binary_files(self, fake_engine):
        results = _discover_binaries(fake_engine, {"OtherMod"})
        rels = [r[0] for r in results]
        assert len(rels) == 1
        assert rels[0].endswith(".dll")


class TestDiscoverModuleIntermediates:
    """Auto-discovery of generated and precompiled files."""

    @pytest.fixture
    def fake_engine(self, tmp_path):
        """Create a fake UE root with intermediate build files."""
        engine = tmp_path / "UE_Test"
        base = engine / "Engine" / "Intermediate" / "Build" / "Win64"

        # Generated headers
        inc = base / "UnrealEditor" / "Inc" / "MainFrame" / "UHT"
        inc.mkdir(parents=True)
        (inc / "HomeScreenSettings.generated.h").write_text("// gen")
        (inc / "OtherThing.generated.h").write_text("// gen")  # Different stem

        inc2 = base / "UnrealEditor" / "Inc" / "Core" / "UHT"
        inc2.mkdir(parents=True)
        (inc2 / "CoreTypes.generated.h").write_text("// gen")

        # Precompiled
        dev = base / "UnrealEditor" / "Development" / "MainFrame"
        dev.mkdir(parents=True)
        (dev / "HomeScreenSettings.cpp.obj").write_text("// obj")
        (dev / "HomeScreenSettings.h.obj").write_text("// obj")
        (dev / "MainFrame.precompiled").write_text("// precomp")

        shipping = base / "UnrealEditor" / "Shipping" / "MainFrame"
        shipping.mkdir(parents=True)
        (shipping / "HomeScreenSettings.cpp.obj").write_text("// obj")

        return str(engine)

    def test_finds_generated_headers_matching_stem(self, fake_engine):
        results = _discover_module_intermediates(
            fake_engine, {"MainFrame"}, {"HomeScreenSettings"},
        )
        rels = [r[0] for r in results]
        hits = [r for r in rels if r.endswith(".generated.h")]
        assert len(hits) == 1
        assert "HomeScreenSettings.generated.h" in hits[0]

    def test_excludes_non_matching_stem(self, fake_engine):
        results = _discover_module_intermediates(
            fake_engine, {"MainFrame"}, {"HomeScreenSettings"},
        )
        rels = [r[0] for r in results]
        assert all("OtherThing.generated.h" not in r for r in rels)

    def test_finds_precompiled_files(self, fake_engine):
        results = _discover_module_intermediates(
            fake_engine, {"MainFrame"}, {"HomeScreenSettings"},
        )
        rels = [r[0] for r in results]
        assert any(r.endswith(".cpp.obj") for r in rels)
        assert any(r.endswith(".h.obj") for r in rels)
        assert any(r.endswith(".precompiled") for r in rels)

    def test_multiple_modules(self, fake_engine):
        results = _discover_module_intermediates(
            fake_engine, {"MainFrame", "Core"}, set(),
        )
        assert len(results) >= 5

    def test_empty_modules_returns_empty(self, fake_engine):
        results = _discover_module_intermediates(fake_engine, set(), set())
        assert results == []

    def test_nonexistent_base_dir(self, tmp_path):
        results = _discover_module_intermediates(
            str(tmp_path / "nowhere"), {"MainFrame"}, set(),
        )
        assert results == []
