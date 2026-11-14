"""Formatting, FFmpeg detection, friendly errors, Windows helpers."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from utils.ffmpeg import find_ffmpeg

HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


def ffmpeg_path() -> str | None:
    """Return path to modern FFmpeg, delegating to utils.ffmpeg.find_ffmpeg()."""
    return find_ffmpeg()


def fmt_size(n: float | int | None) -> str:
    """Format a byte count into a human-readable string."""
    n = float(n or 0)
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} B" if u == "B" else f"{n:.1f} {u}"
        n /= 1024
    return "0 B"


def fmt_time(s: float | int | None) -> str:
    """Format seconds into H:MM:SS or M:SS."""
    h, r = divmod(int(s or 0), 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


def classify(url: str) -> str:
    """Return 'invalid', 'video', 'playlist' or 'both'.

    'both' means the URL has a video ID and a playlist ID simultaneously.
    Handles youtu.be short links, music.youtube.com, /shorts/, /live/, /embed/.
    """
    if not url or not isinstance(url, str):
        return "invalid"
    try:
        u = urlparse(url.strip() if "://" in url else "https://" + url.strip())
    except ValueError:
        return "invalid"

    host = (u.netloc or "").lower().split(":")[0]
    if host not in HOSTS:
        return "invalid"

    q = parse_qs(u.query)
    has_list = bool(q.get("list"))

    # youtu.be/<id>, /shorts/<id>, /live/<id>, /embed/<id>, or watch?v=...
    if host == "youtu.be":
        has_vid = bool(re.match(r"^/[\w-]{6,}$", u.path))
    else:
        has_vid = bool(q.get("v")) or bool(
            re.match(r"^/(shorts|live|embed)/[\w-]{6,}", u.path)
        )

    if has_vid and has_list:
        return "both"
    if has_list:
        return "playlist"
    if has_vid:
        return "video"
    return "invalid"


_RULES: list[tuple[str, str]] = [
    (r"cookie|dpapi", "Couldn't read browser cookies. Fully close that browser, or try Firefox."),
    (r"private video", "This video is private and requires sign-in."),
    (r"age.restricted|confirm your age", "Age-restricted video: sign-in is required via Cookie Guide."),
    (r"not available in your country|\bgeo\b|georestrict", "This video is blocked in your region."),
    (r"not a bot|bot check|confirm you(?:'re| are) not a bot", "YouTube asked for verification. If running on cloud, YouTube blocks cloud servers — run locally on your PC or add cookies in Cookie Guide."),
    (r"video unavailable|has been removed|does not exist", "This video is unavailable or was removed."),
    (r"getaddrinfo|timed out|\bconnection\b|\bnetwork\b|urlopen", "Network problem. Check your internet connection and retry."),
    (r"\bffmpeg\b|\bffprobe\b", "FFmpeg is missing or failed. Check Settings > System Diagnostics."),
    (r"no space|errno 28|disk space", "Not enough disk space in the destination folder."),
    (r"permission|errno 13|access is denied", "Permission denied for the output folder. Choose another folder in Settings."),
    (r"requested format is not available", "That format isn't available for this video (or requires YouTube Premium). Pick another quality target."),
    (r"unsupported url", "This link is not a recognized YouTube URL."),
    (r"unable to extract|http error 403|sign in to confirm", "YouTube blocked this cloud server connection (HTTP 403). Run the app locally on your PC (zero cookies needed), or upload cookies.txt on Cookie Guide."),
]

_COMPILED_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(pat, re.IGNORECASE), msg) for pat, msg in _RULES
]

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
_HEX_RE = re.compile(r"\b[0-9a-fA-F]{20,}\b")
_B64_RE = re.compile(r"\b[A-Za-z0-9+/]{30,}={0,2}\b")


def friendly(e: Exception | str) -> str:
    """Return a user-friendly error string, stripping ANSI codes."""
    m = _ANSI_RE.sub("", str(e))
    low = m.lower()
    for pat, msg in _COMPILED_RULES:
        if pat.search(low):
            return msg
    return f"Unexpected error: {m[:200]}"


def sanitize_error(e: Exception | str) -> str:
    """Return sanitized raw error message with ANSI escape codes removed and

    cookies, authorization headers, tokens, and long cryptographic keys redacted.
    This preserves the real error context for debugging in the expander.
    """
    raw = str(e)
    # Strip ANSI color/terminal escape sequences
    m = _ANSI_RE.sub("", raw)
    # Redact cookies in logs / headers: "Cookie: ...", "cookie=..."
    m = re.sub(r"(?i)(cookie(?:file)?\s*[:=]\s*)([^\r\n]+)", r"\1<redacted>", m)
    # Redact authorization headers / bearer tokens
    m = re.sub(r"(?i)(authorization\s*[:=]\s*(?:bearer\s+)?)([^\r\n]+)", r"\1<redacted>", m)
    # Redact sensitive query param tokens / signatures
    m = re.sub(r"(?i)([?&](?:token|sig|signature|key|session|auth)=)([^&\s]+)", r"\1<redacted>", m)
    # Redact standalone hex tokens (20+ chars) and long base64 segments
    m = _HEX_RE.sub("<token>", m)
    m = _B64_RE.sub("<token>", m)
    return m.strip() or "No technical details provided."


def safe_template(t: str | None) -> str:
    """Strip characters that are invalid in Windows filenames/paths from an outtmpl."""
    invalid = r'\/:*?"<>|'
    result = str(t or "%(title)s")
    for ch in invalid:
        result = result.replace(ch, "_")
    return result.strip() or "%(title)s"


def open_folder(p: str) -> None:
    """Open a folder in Explorer."""
    if p and os.path.isdir(p):
        if hasattr(os, "startfile"):
            os.startfile(p)
        else:
            subprocess.Popen(["explorer", os.path.normpath(p)])


def reveal(p: str) -> tuple[bool, str]:
    """Select a file in Windows Explorer or open its parent folder.
    
    Returns (success: bool, message: str).
    Uses proper explorer.exe quoting to handle spaces and OneDrive paths.
    """
    if not p:
        return False, "File path is empty."
    norm = os.path.normpath(p)
    if os.name == "nt":
        if os.path.isfile(norm):
            # explorer.exe /select,"C:\path with spaces\file.ext"
            # Note: Do not pass as list to Popen with /select because Python
            # wraps the whole argument in quotes which breaks Explorer parser.
            try:
                subprocess.Popen(f'explorer.exe /select,"{norm}"')
                return True, "Opened file in Explorer."
            except Exception as e:
                return False, f"Could not launch Explorer: {e}"
        parent = os.path.dirname(norm)
        if os.path.isdir(parent):
            try:
                os.startfile(parent)
                return False, f"File no longer exists. Opened folder instead: {parent}"
            except Exception:
                subprocess.Popen(f'explorer.exe "{parent}"')
                return False, f"File no longer exists. Opened folder: {parent}"
        return False, f"Path not found: {norm}"
    else:
        # Non-Windows fallback
        parent = norm if os.path.isdir(norm) else os.path.dirname(norm)
        if os.path.isdir(parent):
            subprocess.Popen(["xdg-open", parent])
            return True, f"Opened folder: {parent}"
        return False, f"Path not found: {norm}"


def extract_urls(text: str) -> list[str]:
    """Extract YouTube video or playlist URLs from multiline or mixed text."""
    if not text:
        return []
    # Match standard URLs starting with http:// or https://, or raw youtu.be / youtube.com links
    raw_tokens = re.split(r"[\s,\n;]+", text.strip())
    found: list[str] = []
    seen = set()
    for tok in raw_tokens:
        tok = tok.strip()
        if not tok:
            continue
        c = classify(tok)
        if c in ("video", "playlist", "both"):
            norm_url = tok if "://" in tok else "https://" + tok
            if norm_url not in seen:
                seen.add(norm_url)
                found.append(norm_url)
    return found


def check_clipboard_for_url() -> str | None:
    """Check if clipboard contains a valid YouTube URL. Returns the URL or None."""
    # Only check clipboard on desktop Windows
    if os.name != "nt" or not os.environ.get("USERPROFILE"):
        return None
    try:
        clip = clipboard()
        if clip and classify(clip) in ("video", "playlist", "both"):
            return clip.strip()
    except Exception:
        pass
    return None


def _tk(code: str) -> str:
    """Run a small isolated Tkinter script in a subprocess to avoid blocking the main thread."""
    if os.name != "nt" or not os.environ.get("USERPROFILE"):
        return ""
    try:
        res = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return res.stdout.strip()
    except Exception:
        return ""


def pick_folder() -> str:
    """Open a Tkinter folder-picker dialog and return the chosen path."""
    script = (
        "import tkinter as t, tkinter.filedialog as f\n"
        "r = t.Tk()\n"
        "r.withdraw()\n"
        "r.attributes('-topmost', 1)\n"
        "try:\n"
        "    print(f.askdirectory() or '')\n"
        "finally:\n"
        "    r.destroy()\n"
    )
    return _tk(script)


def clipboard() -> str:
    """Return the current clipboard text via Tkinter."""
    script = (
        "import tkinter as t\n"
        "r = t.Tk()\n"
        "r.withdraw()\n"
        "try:\n"
        "    print(r.clipboard_get() or '')\n"
        "except Exception:\n"
        "    pass\n"
        "finally:\n"
        "    r.destroy()\n"
    )
    return _tk(script)


def ensure_logo(path: Path) -> Path:
    """Generate the YT Video Downloader logo PNG if it doesn't exist yet."""
    if not path.exists():
        from PIL import Image, ImageDraw, ImageFont
        path.parent.mkdir(exist_ok=True, parents=True)
        im = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((8, 8, 248, 248), 56, fill="#151D31", outline="#65D6C4", width=8)
        try:
            f = ImageFont.truetype("arialbd.ttf", 100)
        except Exception:
            f = ImageFont.load_default(100)
        d.text((128, 128), "YT", fill="#65D6C4", font=f, anchor="mm")
        im.save(path)
    return path
