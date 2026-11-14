"""FFmpeg and FFprobe detection and path resolution."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path


def _candidate_ffmpeg_paths() -> list[Path]:
    """Return priority list of modern FFmpeg install locations on Windows."""
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    program_files = Path(os.environ.get("ProgramFiles", "C:\\Program Files"))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"))

    return [
        local_app_data / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe",
        Path("C:/ProgramData/chocolatey/bin/ffmpeg.exe"),
        program_files / "ffmpeg" / "bin" / "ffmpeg.exe",
        program_files / "ffmpeg" / "ffmpeg.exe",
        program_files_x86 / "ffmpeg" / "bin" / "ffmpeg.exe",
        Path.home() / "ffmpeg" / "bin" / "ffmpeg.exe",
        Path.home() / "AppData" / "Local" / "ffmpeg" / "bin" / "ffmpeg.exe",
    ]


def find_ffmpeg() -> str | None:
    """Return path to modern FFmpeg executable, prioritizing WinGet / standard locations over PATH."""
    for candidate in _candidate_ffmpeg_paths():
        if candidate.is_file():
            return str(candidate)
    return shutil.which("ffmpeg")


def find_ffprobe() -> str | None:
    """Return path to ffprobe executable, prioritizing one alongside the resolved ffmpeg."""
    ff = find_ffmpeg()
    if ff:
        probe = Path(ff).parent / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if probe.is_file():
            return str(probe)
    return shutil.which("ffprobe")


def ffmpeg_version(path: str | None = None) -> str:
    """Return short FFmpeg version string (e.g. '9.0.1') or 'unknown'."""
    exe = path or find_ffmpeg()
    if not exe:
        return "unknown"
    try:
        out = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=5).stdout
        m = re.search(r"ffmpeg version ([^\s]+)", out)
        return m.group(1) if m else "unknown"
    except Exception:
        return "unknown"
