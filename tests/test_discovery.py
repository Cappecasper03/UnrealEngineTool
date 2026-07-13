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


class TestFullAddFilesPipeline:
    """End-to-end: adding source files triggers auto-discovery of binaries + intermediates.

    Replicates the _on_browse() logic from FileEntryDialog without a GUI.
    """

    @pytest.fixture
    def fake_ue_root(self, tmp_path) -> str:
        """Create a UE root with source files, binaries, and intermediates for Core & MainFrame."""
        ue = tmp_path / "UE_5.7"

        # ── Source files (what the user would browse to) ──
        srcs = [
            ue / "Engine" / "Source" / "Runtime" / "Core" / "Private" / "Core.cpp",
            ue / "Engine" / "Source" / "Editor" / "MainFrame" / "Private" / "MainFrameModule.cpp",
        ]
        for s in srcs:
            s.parent.mkdir(parents=True, exist_ok=True)
            s.write_text("// source")

        # ── Binaries for Core (4 files) + MainFrame (2 files) ──
        bin_dir = ue / "Engine" / "Binaries" / "Win64"
        bin_dir.mkdir(parents=True, exist_ok=True)
        for mod, ext in [("Core", ".dll"), ("Core", ".pdb"), ("Core", ".lib"),
                         ("Core", ".target"), ("MainFrame", ".dll"), ("MainFrame", ".pdb")]:
            (bin_dir / f"UnrealEditor-{mod}{ext}").write_text("fake")
        # Non-matching module binary (OtherMod) — should NOT be discovered
        (bin_dir / "UnrealEditor-OtherMod.dll").write_text("fake")

        # ── Intermediates for Core (generated header) + MainFrame (generated + precompiled) ──
        base = ue / "Engine" / "Intermediate" / "Build" / "Win64"
        # Core generated header
        (base / "UnrealEditor" / "Inc" / "Core" / "UHT" / "CoreTypes.generated.h").parent.mkdir(parents=True, exist_ok=True)
        (base / "UnrealEditor" / "Inc" / "Core" / "UHT" / "CoreTypes.generated.h").write_text("// gen")
        # MainFrame generated header
        (base / "UnrealEditor" / "Inc" / "MainFrame" / "UHT" / "MainFrameModule.generated.h").parent.mkdir(parents=True, exist_ok=True)
        (base / "UnrealEditor" / "Inc" / "MainFrame" / "UHT" / "MainFrameModule.generated.h").write_text("// gen")
        # Non-matching stem — should NOT be discovered
        (base / "UnrealEditor" / "Inc" / "MainFrame" / "UHT" / "OtherThing.generated.h").write_text("// gen")
        # MainFrame precompiled
        (base / "UnrealEditor" / "Development" / "MainFrame" / "MainFrameModule.cpp.obj").parent.mkdir(parents=True, exist_ok=True)
        (base / "UnrealEditor" / "Development" / "MainFrame" / "MainFrameModule.cpp.obj").write_text("// obj")
        (base / "UnrealEditor" / "Development" / "MainFrame" / "MainFrame.precompiled").write_text("// precomp")

        return str(ue)

    def _simulate_on_browse(self, ue_root: str, paths):
        """Replicate _on_browse() logic: build entries, extract modules, discover, merge.

        Returns list of path_custom strings from all entries.
        """
        from models import EngineFile
        entries = []
        all_ue_roots = set()
        version_dir = ""

        # Phase 1: user-picked entries
        for path in sorted(paths):
            rel = _relativise(path, version_dir)
            entries.append(EngineFile(path_custom=rel, path_default="", path_target=rel,
                                       local_name=os.path.basename(rel)))
            ue_root_found = _find_engine_root(path)
            if ue_root_found:
                all_ue_roots.add(ue_root_found)

        # Phase 2: extract modules and source stems
        source_modules = set()
        source_stems = set()
        for e in entries:
            rel = e.path_custom
            mod = _module_name_from_path(rel)
            if mod:
                source_modules.add(mod)
            if rel.lower().startswith("engine/source/"):
                stem = os.path.splitext(os.path.basename(rel))[0]
                if stem:
                    source_stems.add(stem)

        # Phase 3: auto-discover binaries and intermediates
        for root in all_ue_roots:
            for rel_path, abs_path in _discover_binaries(root, source_modules):
                if not any(e.path_custom == rel_path for e in entries):
                    entries.append(EngineFile(path_custom=rel_path, path_default="",
                                               path_target=rel_path,
                                               local_name=os.path.basename(rel_path)))
            for rel_path, abs_path in _discover_module_intermediates(root, source_modules, source_stems):
                if not any(e.path_custom == rel_path for e in entries):
                    entries.append(EngineFile(path_custom=rel_path, path_default="",
                                               path_target=rel_path,
                                               local_name=os.path.basename(rel_path)))

        return [e.path_custom for e in entries]

    def test_user_files_present(self, fake_ue_root):
        """User-picked source files always appear in results."""
        src_files = [
            os.path.join(fake_ue_root, "Engine/Source/Runtime/Core/Private/Core.cpp"),
            os.path.join(fake_ue_root, "Engine/Source/Editor/MainFrame/Private/MainFrameModule.cpp"),
        ]
        paths = self._simulate_on_browse(fake_ue_root, src_files)
        assert "Engine/Source/Runtime/Core/Private/Core.cpp" in paths
        assert "Engine/Source/Editor/MainFrame/Private/MainFrameModule.cpp" in paths

    def test_core_binaries_auto_discovered(self, fake_ue_root):
        """Core module source should pull in Core's .dll, .pdb, .lib, .target."""
        src_files = [
            os.path.join(fake_ue_root, "Engine/Source/Runtime/Core/Private/Core.cpp"),
        ]
        paths = self._simulate_on_browse(fake_ue_root, src_files)
        for ext in [".dll", ".pdb", ".lib", ".target"]:
            assert f"Engine/Binaries/Win64/UnrealEditor-Core{ext}" in paths, \
                f"Missing Core binary: {ext}"

    def test_mainframe_binaries_auto_discovered(self, fake_ue_root):
        """MainFrame module source should pull in MainFrame binaries."""
        src_files = [
            os.path.join(fake_ue_root, "Engine/Source/Editor/MainFrame/Private/MainFrameModule.cpp"),
        ]
        paths = self._simulate_on_browse(fake_ue_root, src_files)
        assert "Engine/Binaries/Win64/UnrealEditor-MainFrame.dll" in paths
        assert "Engine/Binaries/Win64/UnrealEditor-MainFrame.pdb" in paths

    def test_non_matching_module_not_discovered(self, fake_ue_root):
        """OtherMod binary should not appear when user only picks Core/MainFrame files."""
        src_files = [
            os.path.join(fake_ue_root, "Engine/Source/Runtime/Core/Private/Core.cpp"),
        ]
        paths = self._simulate_on_browse(fake_ue_root, src_files)
        assert all("OtherMod" not in p for p in paths)

    def test_intermediates_discovered_with_stem_filter(self, fake_ue_root):
        """Generated headers matching the source file's stem should appear."""
        src_files = [
            os.path.join(fake_ue_root, "Engine/Source/Editor/MainFrame/Private/MainFrameModule.cpp"),
        ]
        paths = self._simulate_on_browse(fake_ue_root, src_files)
        # MainFrameModule.cpp should pull in MainFrameModule.generated.h
        assert any("MainFrameModule.generated.h" in p for p in paths)
        # OtherThing.generated.h has a different stem — should NOT appear
        assert all("OtherThing.generated.h" not in p for p in paths)

    def test_two_modules_combined(self, fake_ue_root):
        """Picking sources from two modules discovers binaries+intermediates for both."""
        src_files = [
            os.path.join(fake_ue_root, "Engine/Source/Runtime/Core/Private/Core.cpp"),
            os.path.join(fake_ue_root, "Engine/Source/Editor/MainFrame/Private/MainFrameModule.cpp"),
        ]
        paths = self._simulate_on_browse(fake_ue_root, src_files)
        assert "Engine/Binaries/Win64/UnrealEditor-Core.dll" in paths
        assert "Engine/Binaries/Win64/UnrealEditor-MainFrame.dll" in paths
        # Precompiled files for MainFrame
        assert any("MainFrameModule.cpp.obj" in p for p in paths)

    def test_precompiled_files_discovered(self, fake_ue_root):
        """MainFrame source should pull in .cpp.obj and .precompiled files."""
        src_files = [
            os.path.join(fake_ue_root, "Engine/Source/Editor/MainFrame/Private/MainFrameModule.cpp"),
        ]
        paths = self._simulate_on_browse(fake_ue_root, src_files)
        assert any(p.endswith(".cpp.obj") for p in paths)
        assert any(p.endswith(".precompiled") for p in paths)

    def test_no_duplicate_binaries_from_same_module(self, fake_ue_root):
        """Two source files in the same module should not double-add binaries."""
        src_files = [
            os.path.join(fake_ue_root, "Engine/Source/Runtime/Core/Private/Core.cpp"),
            os.path.join(fake_ue_root, "Engine/Source/Runtime/Core/Private/Core.h"),
        ]
        paths = self._simulate_on_browse(fake_ue_root, src_files)
        # Core.dll should appear exactly once
        count = sum(1 for p in paths if p == "Engine/Binaries/Win64/UnrealEditor-Core.dll")
        assert count == 1, f"Core.dll appears {count} times instead of 1"
