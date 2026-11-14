"""Metadata extraction (no media downloaded). Cached to avoid repeat requests."""
from __future__ import annotations
from pathlib import Path
import streamlit as st
from yt_dlp import YoutubeDL


@st.cache_data(ttl=900, show_spinner=False, max_entries=64)
def _fetch_cached(url: str, playlist: bool, browser: str, cfile: str) -> dict:
    """Inner cached function — only reached on a cache miss, never caches exceptions."""
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": not playlist,
        "extract_flat": "in_playlist" if playlist else False,
        "socket_timeout": 15,
        "check_formats": False,
    }
    if not playlist:
        opts["playlistend"] = 1
    from config.settings import COOKIES_FILE
    if cfile and Path(cfile).is_file():
        opts["cookiefile"] = cfile
    elif Path(COOKIES_FILE).is_file() and Path(COOKIES_FILE).stat().st_size > 0:
        opts["cookiefile"] = str(COOKIES_FILE)
    elif browser and str(browser).lower() != "none":
        b_name = str(browser).lower().split()[0]
        opts["cookiesfrombrowser"] = (b_name,)
    try:
        with YoutubeDL(opts) as y:
            info = y.extract_info(url, download=False)
    except Exception as e:
        if "requested format is not available" in str(e).lower():
            opts["format"] = "b/bv*+ba/best"
            opts["check_formats"] = False
            with YoutubeDL(opts) as y:
                info = y.extract_info(url, download=False)
        else:
            raise
    if not playlist and info.get("_type") == "playlist":
        entries = info.get("entries") or []
        info = next((e for e in entries if e and e.get("id")), info)
    if playlist or info.get("_type") == "playlist":
        ents = [
            {
                "id": e["id"],
                "title": e.get("title") or e["id"],
                "duration": e.get("duration"),
                "channel": e.get("channel") or e.get("uploader") or "",
            }
            for e in (info.get("entries") or [])
            if e and e.get("id")
        ]
        return {
            "type": "playlist",
            "title": info.get("title") or "Playlist",
            "channel": info.get("channel") or info.get("uploader") or "",
            "count": info.get("playlist_count") or len(ents),
            "entries": ents,
        }
    hs = sorted(
        {f["height"] for f in info.get("formats", []) if f.get("height") and f.get("vcodec") != "none"},
        reverse=True,
    )
    # Extract available subtitle languages (subtitles + auto captions)
    subs = list((info.get("subtitles") or {}).keys())
    autos = list((info.get("automatic_captions") or {}).keys())
    all_subs = sorted(set(subs + autos))
    
    return {
        "type": "video",
        "id": info["id"],
        "title": info.get("title", ""),
        "channel": info.get("channel") or info.get("uploader") or "",
        "duration": info.get("duration"),
        "thumb": info.get("thumbnail"),
        "heights": hs,
        "subtitles": all_subs,
    }


def fetch(url: str, playlist: bool, browser: str = "None", cfile: str = "") -> dict:
    """Fetch metadata for *url*.

    Errors are NOT cached — only successful results are stored by the inner
    cached function.  Callers receive the exception directly.
    """
    try:
        return _fetch_cached(url, playlist, browser, cfile)
    except Exception:
        try:
            _fetch_cached.clear()
        except Exception:
            pass
        raise


def _fetch_uncached(url: str, playlist: bool, browser: str = "None", cfile: str = "") -> dict:
    """Non-cached fetch, used for connection testing in Settings."""
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": not playlist,
        "extract_flat": "in_playlist" if playlist else False,
        "socket_timeout": 15,
        "check_formats": False,
    }
    from config.settings import COOKIES_FILE
    if cfile and Path(cfile).is_file():
        opts["cookiefile"] = cfile
    elif Path(COOKIES_FILE).is_file() and Path(COOKIES_FILE).stat().st_size > 0:
        opts["cookiefile"] = str(COOKIES_FILE)
    elif browser and str(browser).lower() != "none":
        b_name = str(browser).lower().split()[0]
        opts["cookiesfrombrowser"] = (b_name,)
    with YoutubeDL(opts) as y:
        info = y.extract_info(url, download=False)
    if not playlist and info.get("_type") == "playlist":
        entries = info.get("entries") or []
        info = next((e for e in entries if e and e.get("id")), info)
    if playlist or info.get("_type") == "playlist":
        ents = [
            {"id": e["id"], "title": e.get("title") or e["id"], "duration": e.get("duration"),
             "channel": e.get("channel") or e.get("uploader") or ""}
            for e in (info.get("entries") or []) if e and e.get("id")
        ]
        return {
            "type": "playlist", "title": info.get("title") or "Playlist",
            "channel": info.get("channel") or info.get("uploader") or "",
            "count": info.get("playlist_count") or len(ents), "entries": ents
        }
    hs = sorted({f["height"] for f in info.get("formats", []) if f.get("height") and f.get("vcodec") != "none"}, reverse=True)
    subs = list((info.get("subtitles") or {}).keys())
    autos = list((info.get("automatic_captions") or {}).keys())
    all_subs = sorted(set(subs + autos))
    return {
        "type": "video", "id": info["id"], "title": info.get("title", ""),
        "channel": info.get("channel") or info.get("uploader") or "",
        "duration": info.get("duration"), "thumb": info.get("thumbnail"),
        "heights": hs, "subtitles": all_subs
    }
