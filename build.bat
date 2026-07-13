@echo off
REM ================================================================
REM  Build script for UnrealEngineTool
REM  Compiles into two executables:
REM   1. UnrealEngineTool.exe  — Full GUI + headless CLI
REM   2. UnrealEngineTool-CLI.exe — Headless-only (no PySide6 bundled)
REM ================================================================
setlocal enabledelayedexpansion

set PROJECT_ROOT=%~dp0
set VENV_DIR=%PROJECT_ROOT%.venv
set DIST_DIR=%PROJECT_ROOT%dist
set BUILD_DIR=%PROJECT_ROOT%build

REM ---- Activate virtual environment ----
if exist "%VENV_DIR%\Scripts\activate.bat" (
    call "%VENV_DIR%\Scripts\activate.bat"
) else (
    echo [ERROR] Virtual environment not found at %VENV_DIR%
    echo Run: python -m venv .venv
    exit /b 1
)

REM ---- Ensure PyInstaller is installed ----
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [BUILD] Installing PyInstaller...
    pip install pyinstaller
)

REM ================================================================
REM  Build 1: Full GUI + Headless CLI
REM ================================================================
echo.
echo ========================================
echo  BUILD 1/2: UnrealEngineTool.exe (GUI + CLI)
echo ========================================
echo.

pyinstaller ^
    --name "UnrealEngineTool" ^
    --onefile ^
    --noconfirm ^
    --clean ^
    --paths "%PROJECT_ROOT%src" ^
    --hidden-import patcher ^
    --hidden-import patcher.file_patcher ^
    --hidden-import patcher.version_dialog ^
    --hidden-import patcher.version_io ^
    --hidden-import plugin_manager ^
    --hidden-import plugin_manager.backup_manager ^
    --hidden-import plugin_manager.scanner ^
    --hidden-import plugin_manager.patcher ^
    --collect-all PySide6 ^
    "%PROJECT_ROOT%src\main.py"

if errorlevel 1 (
    echo [ERROR] Full build failed!
    exit /b 1
)

echo.
echo [BUILD 1/2] Done!
for %%f in ("%DIST_DIR%\UnrealEngineTool.exe") do (
    set FILESIZE=%%~zf
    set /a FILESIZE_MB=!FILESIZE! / 1024 / 1024
    set FILESIZE_KB=!FILESIZE! / 1024
    echo   dist\UnrealEngineTool.exe  (!FILESIZE_KB! KB = !FILESIZE_MB! MB)
)

REM ================================================================
REM  Build 2: Headless-only CLI (no PySide6)
REM ================================================================
echo.
echo ========================================
echo  BUILD 2/2: UnrealEngineTool-CLI.exe (headless)
echo ========================================
echo.

pyinstaller ^
    --name "UnrealEngineTool-CLI" ^
    --onefile ^
    --noconfirm ^
    --clean ^
    --console ^
    --paths "%PROJECT_ROOT%src" ^
    --hidden-import patcher ^
    --hidden-import patcher.file_patcher ^
    --hidden-import patcher.version_dialog ^
    --hidden-import patcher.version_io ^
    --hidden-import plugin_manager ^
    --hidden-import plugin_manager.backup_manager ^
    --hidden-import plugin_manager.scanner ^
    --hidden-import plugin_manager.patcher ^
    --exclude-module PySide6 ^
    --exclude-module shiboken6 ^
    --exclude-module PySide6.QtCore ^
    --exclude-module PySide6.QtGui ^
    --exclude-module PySide6.QtWidgets ^
    --exclude-module PySide6.QtNetwork ^
    --exclude-module PySide6.QtSvg ^
    --exclude-module PySide6.QtXml ^
    "%PROJECT_ROOT%src\main.py"

if errorlevel 1 (
    echo [ERROR] CLI-only build failed!
    exit /b 1
)

REM ---- Report results ----
echo.
echo ========================================
echo  BUILD COMPLETE
echo ========================================
echo.
for %%f in ("%DIST_DIR%\UnrealEngineTool.exe") do (
    set /a FILESIZE=%%~zf / 1024
)
for %%f in ("%DIST_DIR%\UnrealEngineTool-CLI.exe") do (
    set /a CLI_FILESIZE=%%~zf / 1024
)
echo   dist\UnrealEngineTool.exe         (!FILESIZE! KB)
echo   dist\UnrealEngineTool-CLI.exe     (!CLI_FILESIZE! KB)
echo.
echo Usage:
echo   dist\UnrealEngineTool.exe              # Launch GUI
echo   dist\UnrealEngineTool.exe list          # CLI: list patches
echo   dist\UnrealEngineTool-CLI.exe list      # CLI only (smaller)
echo   dist\UnrealEngineTool-CLI.exe apply ^<ver^> ^<dir^>
echo.

endlocal
