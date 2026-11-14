"""Playlist helpers — separated from metadata."""
from __future__ import annotations
from typing import Any


def filter_entries(entries: list[dict], selected_indices: list[int]) -> list[dict]:
    """Return only entries at the given 0-based indices."""
    return [entries[i] for i in selected_indices if 0 <= i < len(entries)]


def playlist_id(url: str) -> str:
    """Return a short hash of *url* for grouping downloads."""
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:8]
