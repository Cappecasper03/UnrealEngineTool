import hashlib
import os
import shutil
import sys
from pathlib import Path

import pytest


def _find_project_root() -> Path:
    """Walk up from this file to find the project root (has .git/)."""
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / ".git").is_dir():
            return p
        p = p.parent
    raise RuntimeError("Could not find project root")


PROJECT_ROOT = _find_project_root()
TEST_ENGINES = PROJECT_ROOT / "tests" / "test-data"

# Patches are stored under LOCALAPPDATA
_PATCHES_ROOT = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "UnrealEngineTool" / "patches"
TEST_DATA = PROJECT_ROOT / "tests" / "test-data"

ORIGINAL_DIR = TEST_DATA / "UE_5.7-Original"
CUSTOM_DIR = TEST_DATA / "UE_5.7-Custom"
UE_INSTALL_DIR = TEST_DATA / "UE_5.7"

# Patch info
PATCH_NAME = "UE_5.7-Test"

SCRIPT = PROJECT_ROOT / "src" / "main.py"

# Key files
TARGET_RELPATH = "Engine/Source/Editor/MainFrame/Private/HomeScreen/SHomeScreen.cpp"
TARGET_FILE = UE_INSTALL_DIR / "Engine" / "Source" / "Editor" / "MainFrame" / "Private" / "HomeScreen" / "SHomeScreen.cpp"
MARKER_FILE = UE_INSTALL_DIR / "Engine" / "Binaries" / ".uepatcher_version"

CUSTOM_SRC = CUSTOM_DIR / "Engine" / "Source" / "Editor" / "MainFrame" / "Private" / "HomeScreen" / "SHomeScreen.cpp"
ORIGINAL_SRC = ORIGINAL_DIR / "Engine" / "Source" / "Editor" / "MainFrame" / "Private" / "HomeScreen" / "SHomeScreen.cpp"


def md5(path: os.PathLike) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def hard_reset():
    """Hard-reset the test UE install to pristine default state.
    Directly copies the original file back and clears the marker,
    bypassing the patcher's backup chain to avoid cumulative corruption.
    """
    import stat as _stat

    # Copy original file to target (force, override readonly)
    src, dst = str(ORIGINAL_SRC), str(TARGET_FILE)
    if not os.path.isdir(os.path.dirname(dst)):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.isfile(dst):
        os.chmod(dst, _stat.S_IWRITE)
        os.remove(dst)
    shutil.copy2(src, dst)

    # Write default marker
    marker_dir = os.path.dirname(str(MARKER_FILE))
    if marker_dir and not os.path.isdir(marker_dir):
        os.makedirs(marker_dir, exist_ok=True)
    MARKER_FILE.write_text("default")


@pytest.fixture
def ue_install() -> Path:
    return UE_INSTALL_DIR


@pytest.fixture
def original_src() -> Path:
    return ORIGINAL_SRC


@pytest.fixture
def custom_src() -> Path:
    return CUSTOM_SRC


@pytest.fixture
def target_file() -> Path:
    return TARGET_FILE


@pytest.fixture
def marker_file() -> Path:
    return MARKER_FILE


@pytest.fixture
def patch_name() -> str:
    return PATCH_NAME


@pytest.fixture
def patches_root() -> Path:
    return _PATCHES_ROOT


@pytest.fixture
def target_relpath() -> str:
    return TARGET_RELPATH


@pytest.fixture(autouse=True)
def _ensure_clean_state():
    """Hard-reset test UE install before every test."""
    hard_reset()
    yield
    hard_reset()


def pytest_sessionstart():
    """Auto-create the test patch metadata and seed custom files before the session begins.

    This makes the test suite fully self-contained — no external fixtures needed.
    """
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    from patcher.patch_io import create_patch, write_info
    from models import EngineFile

    ver_dir = _PATCHES_ROOT / PATCH_NAME
    # Remove any stale leftover from a previous run
    if ver_dir.is_dir():
        shutil.rmtree(str(ver_dir), onerror=_remove_readonly)

    ver = create_patch(str(_PATCHES_ROOT), PATCH_NAME, unreal_version="5.7")

    target_rel = "Engine/Source/Editor/MainFrame/Private/HomeScreen/SHomeScreen.cpp"
    ver.files.append(EngineFile(
        path_custom=target_rel,
        path_default=target_rel,
        path_target=target_rel,
        local_name="SHomeScreen.cpp",
    ))
    write_info(ver)

    # Seed both custom and original files into the version directory
    custom_src = CUSTOM_DIR / target_rel
    ver_target = ver_dir / target_rel
    ver_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(custom_src), str(ver_target))

    original_src = ORIGINAL_DIR / target_rel
    original_target = ver_dir / "original" / target_rel
    original_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(str(original_src), str(original_target))


def _remove_readonly(func, path, exc_info):
    """Callback for shutil.rmtree(onerror=...) to make readonly files deletable on Windows."""
    import stat
    os.chmod(path, stat.S_IWRITE)
    func(path)


def pytest_sessionfinish():
    """Clean up the test patch after the session ends."""
    ver_dir = _PATCHES_ROOT / PATCH_NAME
    if ver_dir.is_dir():
        try:
            shutil.rmtree(str(ver_dir), onerror=_remove_readonly)
        except TypeError:
            # onexc is Python 3.12+; fall back to onerror for 3.11-
            pass
