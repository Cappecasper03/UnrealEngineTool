"""Tests for UPluginPatcher (writing .uplugin changes) and BackupManager."""

import json
import os
import stat
import sys
from pathlib import Path
from typing import List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from models import PluginData
from plugin_manager.patcher import UPluginPatcher
from plugin_manager.backup_manager import BackupManager


# ── Helpers ──────────────────────────────────────────────


def _make_plugin(name: str, enabled: bool = False, installed: bool = False,
                 path: str = "") -> PluginData:
    """Create a PluginData for testing (no disk I/O)."""
    p = PluginData(
        name=name,
        friendly_name=name,
        enabled_by_default=enabled,
        installed=installed,
        relative_path=f"Marketplace/{name}/{name}.uplugin",
        full_path=path or f"D:/UE/Engine/Plugins/Marketplace/{name}/{name}.uplugin",
    )
    p.snapshot_original()
    return p


def _write_uplugin(path: str, **fields) -> None:
    """Write a .uplugin JSON file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {"FileVersion": 3}
    data.update(fields)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _read_uplugin(path: str) -> dict:
    """Read a .uplugin JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── PluginData Model Tests ───────────────────────────────


class TestPluginDataModel:
    """PluginData state tracking."""

    def test_is_modified_true_after_change(self):
        p = _make_plugin("TestP")
        p.enabled_by_default = True
        assert p.is_modified is True

    def test_is_modified_false_by_default(self):
        p = _make_plugin("TestP")
        assert p.is_modified is False

    def test_is_modified_false_after_restore(self):
        p = _make_plugin("TestP")
        p.enabled_by_default = True
        p.restore_original()
        assert p.is_modified is False


# ── UPluginPatcher Tests ─────────────────────────────────


class TestUPluginPatcher:
    """Writing .uplugin file changes."""

    @pytest.fixture
    def patcher(self) -> UPluginPatcher:
        return UPluginPatcher()

    @pytest.fixture
    def original_plugins(self, tmp_path) -> List[PluginData]:
        """Create a few .uplugin files with defined state."""
        root = tmp_path / "Engine" / "Plugins"
        _write_uplugin(
            str(root / "Marketplace" / "Alpha" / "Alpha.uplugin"),
            FriendlyName="Alpha",
            EnabledByDefault=True,
            Installed=False,
        )
        _write_uplugin(
            str(root / "BuiltIn" / "Beta" / "Beta.uplugin"),
            FriendlyName="Beta",
            EnabledByDefault=False,
        )
        _write_uplugin(
            str(root / "Marketplace" / "Gamma" / "Gamma.uplugin"),
            FriendlyName="Gamma",
        )
        from plugin_manager.scanner import UPluginScanner
        scanned = UPluginScanner().scan(str(tmp_path))
        # Return a snapshot (deep copy) for the originals list
        import copy
        return copy.deepcopy(scanned)

    def _modify_and_apply(self, plugins, originals, patcher, fn):
        """Helper: modify a copy of originals, then apply_changes against the snapshot."""
        import copy
        working = copy.deepcopy(originals)
        fn(working)
        result = patcher.apply_changes(working, originals, "")
        return result, working

    def test_apply_toggle_enabled(self, patcher, original_plugins):
        def modify(plugs):
            p = next(x for x in plugs if x.name == "Alpha")
            p.enabled_by_default = False

        result, working = self._modify_and_apply(original_plugins, original_plugins, patcher, modify)
        assert result.modified_count == 1

        p = next(x for x in working if x.name == "Alpha")
        data = _read_uplugin(p.full_path)
        assert data["EnabledByDefault"] is False

    def test_apply_injects_missing_fields(self, patcher, original_plugins):
        def modify(plugs):
            p = next(x for x in plugs if x.name == "Gamma")
            p.enabled_by_default = True

        result, working = self._modify_and_apply(original_plugins, original_plugins, patcher, modify)
        assert result.modified_count == 1

        p = next(x for x in working if x.name == "Gamma")
        data = _read_uplugin(p.full_path)
        assert data["EnabledByDefault"] is True

    def test_unmodified_plugin_not_touched(self, patcher, original_plugins):
        def modify(plugs):
            p = next(x for x in plugs if x.name == "Alpha")
            p.enabled_by_default = False

        result, working = self._modify_and_apply(original_plugins, original_plugins, patcher, modify)
        assert result.modified_count == 1

        # Beta should be unchanged
        beta = next(x for x in working if x.name == "Beta")
        data = _read_uplugin(beta.full_path)
        assert data.get("EnabledByDefault") is False

    def test_apply_multiple_changes(self, patcher, original_plugins):
        """Alpha already True, Beta False→True, Gamma missing→True = 2 actual changes."""
        def modify(plugs):
            for p in plugs:
                p.enabled_by_default = True

        result, working = self._modify_and_apply(original_plugins, original_plugins, patcher, modify)
        assert result.modified_count == 2

        for p in working:
            data = _read_uplugin(p.full_path)
            assert data.get("EnabledByDefault") is True

    def test_readonly_file_is_unset(self, patcher, original_plugins):
        # Make file readonly before patching
        p_orig = next(x for x in original_plugins if x.name == "Alpha")
        os.chmod(p_orig.full_path, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

        def modify(plugs):
            p = next(x for x in plugs if x.name == "Alpha")
            p.enabled_by_default = False

        result, working = self._modify_and_apply(original_plugins, original_plugins, patcher, modify)
        assert result.modified_count == 1
        assert os.access(p_orig.full_path, os.W_OK), "File should be writable after patching"

    def test_missing_file_reported_as_error(self, patcher, original_plugins):
        def modify(plugs):
            p = next(x for x in plugs if x.name == "Alpha")
            p.enabled_by_default = False
            p.full_path = "D:/nonexistent/Alpha.uplugin"

        result, working = self._modify_and_apply(original_plugins, original_plugins, patcher, modify)
        assert result.modified_count == 0
        assert result.error_count >= 1


# ── BackupManager Tests ──────────────────────────────────


class TestBackupManager:
    """Backup/restore and template operations."""

    @pytest.fixture
    def bm(self) -> BackupManager:
        return BackupManager()

    @pytest.fixture
    def plugins(self) -> List[PluginData]:
        return [
            _make_plugin("Alpha", enabled=True),
            _make_plugin("Beta", enabled=False),
            _make_plugin("Gamma", enabled=True),
            _make_plugin("Delta", enabled=False),
        ]

    def test_save_load_backup(self, bm, plugins, tmp_path):
        ue_root = str(tmp_path / "UE_Test")
        plugins_root = os.path.join(ue_root, "Engine", "Plugins")
        # Create the absolute paths on disk so save_backup can resolve them
        for p in plugins:
            abs_dir = Path(plugins_root) / "Marketplace" / p.name
            abs_dir.mkdir(parents=True, exist_ok=True)
            (abs_dir / f"{p.name}.uplugin").write_text("{}")

        backup_file = str(tmp_path / "backup.txt")
        bm.save_backup(backup_file, plugins, ue_root)

        # Load into a fresh set (all disabled)
        fresh = [_make_plugin("Alpha"), _make_plugin("Beta"),
                 _make_plugin("Gamma"), _make_plugin("Delta")]
        count = bm.load_backup(backup_file, fresh, ue_root)
        assert count == 2
        assert fresh[0].enabled_by_default is True  # Alpha was enabled
        assert fresh[1].enabled_by_default is False  # Beta was disabled
        assert fresh[2].enabled_by_default is True   # Gamma was enabled
        assert fresh[3].enabled_by_default is False  # Delta was disabled

    def test_save_load_template(self, bm, plugins, tmp_path):
        template_file = str(tmp_path / "template.txt")
        bm.save_template(template_file, plugins)

        fresh = [_make_plugin("Alpha"), _make_plugin("Beta"),
                 _make_plugin("Gamma"), _make_plugin("Delta")]
        count = bm.load_template(template_file, fresh)
        assert count == 2
        assert fresh[0].enabled_by_default is True
        assert fresh[1].enabled_by_default is False
        assert fresh[2].enabled_by_default is True
        assert fresh[3].enabled_by_default is False

    def test_load_backup_missing_file_raises(self, bm, plugins):
        with pytest.raises(FileNotFoundError):
            bm.load_backup("D:/nonexistent_backup.txt", plugins, "D:/UE_Test")

    def test_load_template_missing_file_raises(self, bm, plugins):
        with pytest.raises(FileNotFoundError):
            bm.load_template("D:/nonexistent_template.txt", plugins)

    def test_save_backup_empty(self, bm, tmp_path):
        """No enabled plugins → empty backup file."""
        all_disabled = [_make_plugin("A", enabled=False), _make_plugin("B", enabled=False)]
        backup_file = str(tmp_path / "empty_backup.txt")
        bm.save_backup(backup_file, all_disabled, "D:/UE_Test")
        with open(backup_file) as f:
            content = f.read().strip()
        assert content == ""

    def test_load_backup_empty_file(self, bm, plugins, tmp_path):
        backup_file = str(tmp_path / "empty.txt")
        backup_file = Path(backup_file)
        backup_file.write_text("\n")
        count = bm.load_backup(str(backup_file), plugins, "D:/UE_Test")
        assert count == 0

    def test_apply_minimal_enables_core_plugins(self, bm):
        """apply_minimal should return count and set states."""
        plugins = [
            _make_plugin("AISupport"),
            _make_plugin("SomeRandomPlugin"),
            _make_plugin("PluginBrowser"),
        ]
        count = bm.apply_minimal(plugins)
        assert count == 2  # AISupport + PluginBrowser
        assert plugins[0].enabled_by_default is True   # AISupport in minimal set
        assert plugins[1].enabled_by_default is False  # not in minimal set
        assert plugins[2].enabled_by_default is True   # PluginBrowser in minimal set

    def test_apply_minimal_all_disabled_if_no_match(self, bm):
        plugins = [_make_plugin("Unknown1"), _make_plugin("Unknown2")]
        count = bm.apply_minimal(plugins)
        assert count == 0
        assert all(p.enabled_by_default is False for p in plugins)

    def test_load_template_relative_paths(self, bm, tmp_path):
        """Template uses relative paths, works from any UE root."""
        template_file = str(tmp_path / "template.txt")
        with open(template_file, "w") as f:
            f.write("Marketplace/Alpha/Alpha.uplugin\n")
            f.write("Marketplace/Gamma/Gamma.uplugin\n")

        fresh = [_make_plugin("Alpha"), _make_plugin("Beta"),
                 _make_plugin("Gamma"), _make_plugin("Delta")]
        count = bm.load_template(template_file, fresh)
        assert count == 2
        assert fresh[0].enabled_by_default is True
        assert fresh[2].enabled_by_default is True
        assert fresh[1].enabled_by_default is False
        assert fresh[3].enabled_by_default is False
