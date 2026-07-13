"""Tests for UPluginScanner — scanning .uplugin files from a UE install directory."""

import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from plugin_manager.scanner import UPluginScanner


def _write_uplugin(dir_path: str, name: str, **fields) -> str:
    """Write a .uplugin JSON file and return the full path."""
    os.makedirs(dir_path, exist_ok=True)
    data = {"FileVersion": 3}
    data.update(fields)
    path = os.path.join(dir_path, f"{name}.uplugin")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


@pytest.fixture
def fake_plugins_root(tmp_path) -> str:
    """Create a UE Engine/Plugins directory structure with several test plugins."""
    root = tmp_path / "UE_Test"
    plugins_root = root / "Engine" / "Plugins"
    (plugins_root / "Marketplace" / "AwesomePlugin").mkdir(parents=True)
    _write_uplugin(
        str(plugins_root / "Marketplace" / "AwesomePlugin"),
        "AwesomePlugin",
        FriendlyName="Awesome Plugin",
        Description="Does awesome things",
        Category="Rendering",
        EnabledByDefault=True,
        Installed=True,
        VersionName="1.0",
    )

    (plugins_root / "BuiltIn" / "CoreUtils").mkdir(parents=True)
    _write_uplugin(
        str(plugins_root / "BuiltIn" / "CoreUtils"),
        "CoreUtils",
        FriendlyName="Core Utilities",
        Description="Core utility plugin",
        EnabledByDefault=False,
    )

    # Plugin with Resources/icon128.png
    plugin_dir = plugins_root / "Marketplace" / "WithIcon"
    plugin_dir.mkdir(parents=True)
    res_dir = plugin_dir / "Resources"
    res_dir.mkdir()
    (res_dir / "icon128.png").write_text("fake png")
    _write_uplugin(
        str(plugin_dir),
        "WithIcon",
        FriendlyName="Icon Plugin",
    )

    # Nested subdirectory (not in IGNORED_FOLDERS)
    (plugins_root / "Marketplace" / "Nested" / "SubPlugin").mkdir(parents=True)
    _write_uplugin(
        str(plugins_root / "Marketplace" / "Nested" / "SubPlugin"),
        "SubPlugin",
        FriendlyName="Sub Plugin",
    )

    return str(root)


class TestUPluginScanner:
    """Scanning UE plugins directories."""

    def test_discovers_all_plugins(self, fake_plugins_root):
        scanner = UPluginScanner()
        plugins = scanner.scan(fake_plugins_root)
        names = {p.name for p in plugins}
        assert "AwesomePlugin" in names
        assert "CoreUtils" in names
        assert "WithIcon" in names
        assert "SubPlugin" in names

    def test_plugin_fields_populated(self, fake_plugins_root):
        scanner = UPluginScanner()
        plugins = scanner.scan(fake_plugins_root)
        ap = next(p for p in plugins if p.name == "AwesomePlugin")
        assert ap.friendly_name == "Awesome Plugin"
        assert ap.description == "Does awesome things"
        assert ap.category == "Rendering"
        assert ap.enabled_by_default is True
        assert ap.installed is True
        assert ap.version_name == "1.0"

    def test_icon_path_found(self, fake_plugins_root):
        scanner = UPluginScanner()
        plugins = scanner.scan(fake_plugins_root)
        ip = next(p for p in plugins if p.name == "WithIcon")
        assert ip.icon_path != ""
        assert ip.icon_path.endswith("icon128.png")

    def test_no_icon_when_missing(self, fake_plugins_root):
        scanner = UPluginScanner()
        plugins = scanner.scan(fake_plugins_root)
        ap = next(p for p in plugins if p.name == "AwesomePlugin")
        assert ap.icon_path == ""

    def test_relative_path(self, fake_plugins_root):
        scanner = UPluginScanner()
        plugins = scanner.scan(fake_plugins_root)
        ap = next(p for p in plugins if p.name == "AwesomePlugin")
        # os.path.relpath uses platform separators — accept both
        assert ap.relative_path.replace("\\", "/") == "Marketplace/AwesomePlugin/AwesomePlugin.uplugin"

    def test_full_path(self, fake_plugins_root):
        scanner = UPluginScanner()
        plugins = scanner.scan(fake_plugins_root)
        ap = next(p for p in plugins if p.name == "AwesomePlugin")
        assert ap.full_path.endswith("AwesomePlugin.uplugin")
        assert os.path.isfile(ap.full_path)

    def test_missing_plugins_dir_raises(self, tmp_path):
        scanner = UPluginScanner()
        with pytest.raises(FileNotFoundError, match="Plugins directory not found"):
            scanner.scan(str(tmp_path / "nonexistent"))

    def test_ignores_known_subfolders(self, tmp_path):
        """Directories named Binaries, Config, Content etc. should be skipped."""
        root = tmp_path / "UE_Test"
        plugins_root = root / "Engine" / "Plugins"
        ignored = {"Binaries", "Config", "Content", "Intermediate"}

        # Create a real plugin dir
        (plugins_root / "Marketplace" / "RealPlugin").mkdir(parents=True)
        _write_uplugin(
            str(plugins_root / "Marketplace" / "RealPlugin"),
            "RealPlugin",
        )

        # Create ignored dirs with nested .uplugin files (should NOT be found)
        for ig in ignored:
            ig_dir = plugins_root / "Marketplace" / ig
            ig_dir.mkdir(parents=True)
            _write_uplugin(str(ig_dir), f"{ig}Plugin")

        scanner = UPluginScanner()
        plugins = scanner.scan(str(root))
        names = {p.name for p in plugins}
        assert "RealPlugin" in names
        for ig in ignored:
            assert f"{ig}Plugin" not in names

    def test_default_ebd_and_installed(self, fake_plugins_root):
        """Plugins without EnabledByDefault/Installed should default to False."""
        scanner = UPluginScanner()
        plugins = scanner.scan(fake_plugins_root)
        ip = next(p for p in plugins if p.name == "WithIcon")
        assert ip.enabled_by_default is False
        assert ip.installed is False


class TestUPluginScannerErrors:
    """Error handling in plugin scanning."""

    def test_broken_json_gets_error_description(self, tmp_path):
        root = tmp_path / "UE_Test"
        plugins_root = root / "Engine" / "Plugins"
        (plugins_root / "Broken").mkdir(parents=True)
        bad_path = os.path.join(str(plugins_root / "Broken"), "Broken.uplugin")
        with open(bad_path, "w") as f:
            f.write("this is not json")

        scanner = UPluginScanner()
        plugins = scanner.scan(str(root))
        assert len(plugins) == 1
        assert "Parse error" in plugins[0].description

    def test_empty_uplugin_file(self, tmp_path):
        root = tmp_path / "UE_Test"
        plugins_root = root / "Engine" / "Plugins"
        (plugins_root / "Empty").mkdir(parents=True)
        empty_path = os.path.join(str(plugins_root / "Empty"), "Empty.uplugin")
        with open(empty_path, "wb"):
            pass  # empty file

        scanner = UPluginScanner()
        plugins = scanner.scan(str(root))
        assert len(plugins) == 1
        assert "Parse error" in plugins[0].description

    def test_ignores_files_in_plugin_dir(self, tmp_path):
        """A .txt file inside a plugin dir should not register as a plugin."""
        root = tmp_path / "UE_Test"
        plugins_root = root / "Engine" / "Plugins"
        (plugins_root / "NotAPlugin").mkdir(parents=True)
        (plugins_root / "NotAPlugin" / "readme.txt").write_text("hello")

        scanner = UPluginScanner()
        plugins = scanner.scan(str(root))
        assert len(plugins) == 0


class TestReadUPlugin:
    """Static read_uplugin method."""

    def test_read_uplugin_static(self, fake_plugins_root):
        path = fake_plugins_root + "/Engine/Plugins/Marketplace/AwesomePlugin/AwesomePlugin.uplugin"
        plugins_root = fake_plugins_root + "/Engine/Plugins"
        plugin = UPluginScanner.read_uplugin(path, plugins_root)
        assert plugin.name == "AwesomePlugin"
        assert plugin.friendly_name == "Awesome Plugin"
