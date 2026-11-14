@echo off
title YT Video Downloader
color 0B
setlocal
cd /d "%~dp0"

echo ========================================================
echo                 YT Video Downloader
echo          Fast, High Quality Video & Audio
echo ========================================================
echo.

REM 1. Add WinGet links folder to PATH so FFmpeg and Deno are found
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links" set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"

REM 2. Check Python installation
python --version >nul 2>&1
if not errorlevel 1 goto :python_found

py --version >nul 2>&1
if not errorlevel 1 goto :python_found

echo [!] Python was not found on your computer.
echo [*] Attempting to install Python automatically via winget...
echo.
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto :python_install_failed

echo.
echo [OK] Python was installed successfully!
echo Please close this window and double-click START_DOWNLOADER.bat again.
pause
exit /b 0

:python_install_failed
echo.
echo [X] Could not install Python automatically.
echo Please download and install Python from: https://www.python.org/downloads/
echo IMPORTANT: During installation, check the box: "Add Python to PATH"
pause
exit /b 1

:python_found

REM 3. Setup Virtual Environment on first run if streamlit is missing
if exist ".venv\Scripts\streamlit.exe" goto :run_app

echo [*] First-time setup detected! Setting up YT Video Downloader for you...
echo [*] This will take about 1 minute on first launch only. Please wait...
echo.

if exist ".venv\Scripts\python.exe" goto :venv_created

echo [*] Creating isolated Python environment...
python -m venv .venv >nul 2>&1
if not errorlevel 1 goto :venv_created

py -m venv .venv >nul 2>&1
if not errorlevel 1 goto :venv_created

echo [X] Failed to create virtual environment.
echo Please make sure Python is installed and accessible.
pause
exit /b 1

:venv_created

echo [*] Installing required components (Streamlit, yt-dlp, Pillow, etc.)...
".venv\Scripts\python.exe" -m pip install -U pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :pip_failed
goto :check_tools

:pip_failed
echo.
echo [X] Package installation failed. Please check your internet connection and try again.
pause
exit /b 1

:check_tools

REM Check and install modern FFmpeg if missing
where ffmpeg >nul 2>&1
if not errorlevel 1 goto :check_deno

echo [*] Installing FFmpeg for 4K video merging and MP3 conversion...
winget install -e --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links" set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"

:check_deno

REM Check and install Deno if missing
where deno >nul 2>&1
if not errorlevel 1 goto :setup_complete

echo [*] Installing Deno JavaScript runtime needed by YouTube...
winget install -e --id DenoLand.Deno --accept-package-agreements --accept-source-agreements
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links" set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"

:setup_complete
echo.
echo [OK] All setup complete! Starting YT Video Downloader...
echo.

:run_app
echo [*] Starting YT Video Downloader...
echo [*] Your browser will open automatically at http://localhost:8501
echo [*] Keep this window open while using the app. Close it when you are done.
echo.

REM Launch Streamlit using the virtual environment
".venv\Scripts\streamlit.exe" run app.py --server.headless=false --server.port=8501

if errorlevel 1 (
    echo.
    echo [!] App stopped with an error code.
    pause
)
