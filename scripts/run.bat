@echo off
setlocal
cd /d "%~dp0.."

REM Ensure WinGet Links directory is in current PATH so modern FFmpeg / Deno are available
if exist "%LOCALAPPDATA%\Microsoft\WinGet\Links" (
    set "PATH=%LOCALAPPDATA%\Microsoft\WinGet\Links;%PATH%"
)

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found.
    echo Please run START_DOWNLOADER.bat or scripts\install.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python -m streamlit run app.py
