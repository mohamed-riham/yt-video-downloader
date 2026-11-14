"""Comprehensive test suite for YT Video Downloader v2.0."""
import os
import sys
from pathlib import Path
import pytest

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.helpers import classify, extract_urls, fmt_size, fmt_time, friendly, reveal
from utils import history as hist
from config import settings as cfg
from core.download_manager import Job, build_opts


def test_app_name():
    assert cfg.APP_NAME == "YT Video Downloader"


def test_classify_urls():
    assert classify("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "video"
    assert classify("https://youtu.be/dQw4w9WgXcQ") == "video"
    assert classify("https://www.youtube.com/shorts/dQw4w9WgXcQ") == "video"
    assert classify("https://www.youtube.com/playlist?list=PL1234567890") == "playlist"
    assert classify("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL1234567890") == "both"
    assert classify("https://google.com") == "invalid"
    assert classify("random garbage string") == "invalid"


def test_extract_urls():
    text = """
    Check out this video: https://www.youtube.com/watch?v=jNQXAC9IVRw
    and also this one https://youtu.be/dQw4w9WgXcQ
    and a playlist https://www.youtube.com/playlist?list=PLrEnWoR732-Bhre0x57UczN5cI_sV4K9H
    not a yt url: https://github.com
    """
    urls = extract_urls(text)
    assert len(urls) == 3
    assert "https://www.youtube.com/watch?v=jNQXAC9IVRw" in urls
    assert "https://youtu.be/dQw4w9WgXcQ" in urls


def test_fmt_helpers():
    assert fmt_size(1024) == "1.0 KB"
    assert fmt_size(1048576) == "1.0 MB"
    assert fmt_time(65) == "1:05"
    assert fmt_time(3665) == "1:01:05"


def test_history_operations(tmp_path, monkeypatch):
    test_file = tmp_path / "test_history.json"
    monkeypatch.setattr(hist, "FILE", test_file)

    hist.clear()
    assert hist.load() == []

    entry1 = {
        "id": "1",
        "title": "Alpha Video",
        "file": "alpha.mp4",
        "format": "MP4",
        "resolution": "1080p",
        "size": 5000000,
        "date": "2026-11-14 10:00",
    }
    entry2 = {
        "id": "2",
        "title": "Beta Audio Track",
        "file": "beta.mp3",
        "format": "MP3",
        "resolution": "320 kbps",
        "size": 3000000,
        "date": "2026-11-14 11:00",
    }

    hist.add(entry1)
    hist.add(entry2)

    loaded = hist.load()
    assert len(loaded) == 2

    # Test search & filter
    assert len(hist.search_and_filter(query="Alpha")) == 1
    assert len(hist.search_and_filter(kind="audio")) == 1
    assert len(hist.search_and_filter(kind="video")) == 1

    # Test stats
    stats = hist.get_stats()
    assert stats["total_downloads"] == 2
    assert stats["video_count"] == 1
    assert stats["audio_count"] == 1
    assert stats["total_bytes"] == 8000000

    # Test CSV export
    csv_str = hist.export_csv()
    assert "Alpha Video" in csv_str
    assert "Beta Audio Track" in csv_str


def test_build_opts():
    j = Job(
        id="test1",
        key="key1",
        url="https://www.youtube.com/watch?v=jNQXAC9IVRw",
        title="Test",
        channel="Test Channel",
        thumb="",
        kind="Video",
        quality="1080p",
        outdir=str(Path.home()),
        template="%(title)s",
        subtitles=True,
        subtitle_lang="en",
        start_time="00:01:00",
        end_time="00:02:00",
    )
    opts = build_opts(j, lambda d: None, lambda d: None)
    assert opts["merge_output_format"] == "mp4"
    assert opts["writesubtitles"] is True
    assert "download_ranges" in opts


def test_reveal_logic():
    # Empty path
    ok, msg = reveal("")
    assert not ok

    # Non-existent path
    ok, msg = reveal("C:\\non_existent_folder_xyz_123\\file.mp4")
    assert not ok
