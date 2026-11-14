"""YT Video Downloader — Settings, constants, directory migration and logging."""
from __future__ import annotations

import json
import logging
import os
import shutil
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_NAME = "YT Video Downloader"
TAGLINE = "Fast, High Quality Video & Audio Downloader"
VERSION = "2.0.0"

# Directories
OLD_APP_DIRS = [Path.home() / ".kuro-downloader", Path.home() / ".noir-downloader"]
APP_DIR = Path.home() / ".yt-video-downloader"
APP_DIR.mkdir(exist_ok=True, parents=True)
SETTINGS_FILE = APP_DIR / "settings.json"
COOKIES_FILE = APP_DIR / "cookies.txt"

# Automatic migration from older versions
def _migrate_old_data() -> None:
    for old_dir in OLD_APP_DIRS:
        if old_dir.exists() and old_dir.is_dir():
            for filename in ("settings.json", "history.json", "cookies.txt"):
                old_file = old_dir / filename
                new_file = APP_DIR / filename
                if old_file.is_file() and not new_file.exists():
                    try:
                        shutil.copy2(old_file, new_file)
                    except Exception:
                        pass

_migrate_old_data()

ACCENTS = {
    "Teal": "#00F2FE",
    "Violet": "#A78BFA",
    "Emerald": "#10B981",
    "Amber": "#F59E0B",
    "Rose": "#F472B6",
    "Cobalt": "#38BDF8",
    "Coral": "#FF6584",
}

VIDEO_Q = ["Best available", "2160p", "1440p", "1080p", "720p", "480p", "360p"]
AUDIO_Q = [
    "MP3 320 kbps",
    "MP3 256 kbps",
    "MP3 192 kbps",
    "MP3 128 kbps",
    "Best available (original)",
]

DEFAULTS = {
    "download_dir": str(Path.home() / "Downloads"),
    "template": "%(title)s",
    "video_quality": "1080p",
    "audio_quality": "MP3 320 kbps",
    "concurrent": 2,
    "cookies_browser": "None",
    "cookies_file": "",
    "accent": "Teal",
    "theme": "dark",
    "rate_limit": "",
    "max_retries": 5,
    "embed_metadata": True,
    "embed_thumbnail": True,
    "sound_on_finish": True,
    "phone_access": False,
    "download_subtitles": False,
    "subtitle_lang": "en",
}


def load() -> dict:
    """Load settings from ~/.yt-video-downloader/settings.json merged with defaults."""
    cfg = dict(DEFAULTS)
    if SETTINGS_FILE.is_file():
        try:
            stored = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                cfg.update(stored)
        except Exception:
            pass
    return cfg


def save(data: dict) -> None:
    """Persist settings dict to ~/.yt-video-downloader/settings.json."""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean = {k: data.get(k, DEFAULTS.get(k)) for k in DEFAULTS}
    SETTINGS_FILE.write_text(json.dumps(clean, indent=2), encoding="utf-8")


def get_logger() -> logging.Logger:
    """Configure rotating file logger at ~/.yt-video-downloader/downloader.log."""
    log = logging.getLogger("yt_downloader")
    if not log.handlers:
        log.setLevel(logging.INFO)
        APP_DIR.mkdir(parents=True, exist_ok=True)
        log_file = APP_DIR / "downloader.log"
        h = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        log.addHandler(h)
    return log
