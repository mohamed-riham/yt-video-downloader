"""Download history stored as JSON with search, filter, stats, and CSV export."""
from __future__ import annotations
import csv
import io
import json
import threading
from datetime import datetime
from config.settings import APP_DIR

FILE = APP_DIR / "history.json"
_lock = threading.Lock()


def load() -> list[dict]:
    """Load history from disk; returns [] on any error."""
    try:
        if FILE.exists():
            return json.loads(FILE.read_text("utf-8"))
        return []
    except Exception:
        return []


def _save(items: list[dict]) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(items[:500], indent=1), "utf-8")


def add(entry: dict) -> None:
    """Prepend *entry* to history, capping at 500 entries."""
    with _lock:
        existing = load()
        _save([entry] + existing)


def remove(eid: str) -> None:
    """Remove single entry by id."""
    with _lock:
        existing = load()
        _save([e for e in existing if e.get("id") != eid])


def clear() -> None:
    """Clear all history items."""
    with _lock:
        _save([])


def search_and_filter(
    query: str = "",
    kind: str = "all",
    sort_by: str = "date_desc",
) -> list[dict]:
    """Search and filter history items.
    
    query: matches title or format.
    kind: 'all', 'video', 'audio'.
    sort_by: 'date_desc', 'date_asc', 'size_desc', 'size_asc', 'title_asc'.
    """
    items = load()
    
    # Filter by search query
    if query.strip():
        q = query.strip().lower()
        items = [i for i in items if q in str(i.get("title", "")).lower() or q in str(i.get("format", "")).lower()]
        
    # Filter by kind
    if kind == "video":
        items = [i for i in items if i.get("format", "").upper() in ("MP4", "MKV", "WEBM")]
    elif kind == "audio":
        items = [i for i in items if i.get("format", "").upper() in ("MP3", "M4A", "OPUS", "WAV", "FLAC")]

    # Sort
    if sort_by == "date_asc":
        items.sort(key=lambda x: str(x.get("date", "")))
    elif sort_by == "size_desc":
        items.sort(key=lambda x: float(x.get("size", 0)), reverse=True)
    elif sort_by == "size_asc":
        items.sort(key=lambda x: float(x.get("size", 0)))
    elif sort_by == "title_asc":
        items.sort(key=lambda x: str(x.get("title", "")).lower())
    else:  # date_desc
        items.sort(key=lambda x: str(x.get("date", "")), reverse=True)
        
    return items


def get_stats() -> dict:
    """Return aggregated history statistics."""
    items = load()
    total_downloads = len(items)
    total_size = sum(float(i.get("size", 0)) for i in items)
    video_count = sum(1 for i in items if i.get("format", "").upper() in ("MP4", "MKV", "WEBM"))
    audio_count = sum(1 for i in items if i.get("format", "").upper() in ("MP3", "M4A", "OPUS", "WAV", "FLAC"))
    return {
        "total_downloads": total_downloads,
        "total_bytes": total_size,
        "video_count": video_count,
        "audio_count": audio_count,
    }


def export_csv() -> str:
    """Export history to CSV string."""
    items = load()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Title", "File Path", "Format", "Resolution", "Size (Bytes)", "Date Downloaded"])
    for i in items:
        writer.writerow([
            i.get("id", ""),
            i.get("title", ""),
            i.get("file", ""),
            i.get("format", ""),
            i.get("resolution", ""),
            i.get("size", 0),
            i.get("date", ""),
        ])
    return output.getvalue()
