@echo off
setlocal
cd /d "%~dp0.."

echo ========================================================
echo YT Video Downloader - Environment Setup
echo ========================================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python 3.10+ is required: https://python.org
    pause
    exit /b 1
)

REM Create .venv if missing
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Upgrade pip and install requirements
echo Installing Python dependencies...
python -m pip install -U pip
pip install -r requirements.txt

REM Ensure WinGet Links directory is in current PATH
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links" (
    set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
)

REM Check for modern FFmpeg
where ffmpeg >nul 2>&1
if errorlevel 1 (
    echo Installing FFmpeg via winget...
    winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
    if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links" (
        set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
    )
)

REM Check for Deno (JavaScript runtime)
where deno >nul 2>&1
if errorlevel 1 (
    echo Installing Deno JS runtime via winget...
    winget install -e --id DenoLand.Deno --accept-package-agreements --accept-source-agreements
    if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links" (
        set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
    )
)

echo.
echo ========================================================
echo YT Video Downloader setup complete!
echo Launch with: START_DOWNLOADER.bat (or scripts\run.bat)
echo ========================================================
echo.
pause
