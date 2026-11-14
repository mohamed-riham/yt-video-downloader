"""Background download queue: limited-concurrency workers, cancel, retry, resume, de-duplication."""
from __future__ import annotations
import os, queue, shutil, threading, time, uuid
from dataclasses import dataclass, field
from datetime import datetime
import streamlit as st
from yt_dlp import YoutubeDL
from config.settings import get_logger, load as load_settings
from utils import history
from utils.helpers import ffmpeg_path, friendly, fmt_size, sanitize_error

try:
    import winsound
except ImportError:
    winsound = None

log = get_logger()
ACTIVE = ("Queued", "Downloading", "Processing")


class Cancelled(Exception):
    pass


@dataclass
class Job:
    id: str
    key: str
    url: str
    title: str
    channel: str
    thumb: str
    kind: str
    quality: str
    outdir: str
    template: str
    group: str = ""
    group_title: str = ""
    status: str = "Queued"
    stage: str = "Queued"
    pct: float = 0.0
    speed: float = 0.0
    eta: int = 0
    done: int = 0
    total: int = 0
    error: str = ""
    raw_error: str = ""
    file: str = ""
    cancel: bool = False
    # Advanced options
    subtitles: bool = False
    subtitle_lang: str = "en"
    embed_subs: bool = False
    embed_metadata: bool = True
    embed_thumbnail: bool = True
    save_thumbnail: bool = False
    start_time: str = ""
    end_time: str = ""


def build_opts(j: Job, hook, pp_hook) -> dict:
    """Build yt-dlp options dict for *j*."""
    ffmpeg = ffmpeg_path()
    ss = load_settings()
    
    o: dict = {
        "outtmpl": os.path.join(j.outdir, j.template + ".%(ext)s"),
        "windowsfilenames": True,
        "trim_file_name": 150,
        "noplaylist": True,
        "nooverwrites": True,
        "continuedl": True,
        "concurrent_fragment_downloads": 4,
        "buffersize": 1024 * 64,
        "retries": int(ss.get("max_retries", 5)),
        "fragment_retries": int(ss.get("max_retries", 5)),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "progress_hooks": [hook],
        "postprocessor_hooks": [pp_hook],
        "ffmpeg_location": ffmpeg,
    }

    # Speed limit rate (e.g. 5M or 500K)
    rate_limit = ss.get("rate_limit", "")
    if rate_limit and str(rate_limit).strip() != "0" and str(rate_limit).strip().lower() != "unlimited":
        o["ratelimit"] = str(rate_limit).strip()

    # Cookies
    b = ss.get("cookies_browser", "None")
    cf = ss.get("cookies_file", "")
    from config.settings import COOKIES_FILE
    if cf and os.path.isfile(cf):
        o["cookiefile"] = cf
    elif b and str(b).lower() != "none":
        b_name = str(b).lower().split()[0]
        o["cookiesfrombrowser"] = (b_name,)
    elif COOKIES_FILE.is_file() and COOKIES_FILE.stat().st_size > 0:
        o["cookiefile"] = str(COOKIES_FILE)

    # Time range section (e.g. *00:01:00-00:02:30)
    if j.start_time.strip() or j.end_time.strip():
        s = j.start_time.strip() or "0"
        e = j.end_time.strip() or "inf"
        o["download_ranges"] = lambda info_dict, ytdl: [{"start_time": s, "end_time": e}]
        o["force_keyframes_at_cuts"] = True

    # Subtitles
    if j.subtitles or ss.get("download_subtitles", False):
        lang = j.subtitle_lang or ss.get("subtitle_lang", "en")
        o["writesubtitles"] = True
        o["writeautomaticsub"] = True
        o["subtitleslangs"] = [lang]
        if j.embed_subs and j.kind == "Video":
            o["postprocessors"] = o.get("postprocessors", []) + [
                {"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False}
            ]

    # Thumbnail download
    if j.save_thumbnail or (j.embed_thumbnail and ss.get("embed_thumbnail", True)):
        o["writethumbnail"] = True

    # Video or Audio format selection
    if j.kind == "Video":
        h = j.quality.rstrip("p")
        if not h.isdigit():
            o["format"] = "bv*+ba/b/best"
        else:
            o["format"] = f"bv*[height<={h}]+ba/b[height<={h}]/bv*+ba/b/best"
        o["merge_output_format"] = "mp4"
        o["prefer_free_formats"] = False

        pps = o.get("postprocessors", [])
        if j.embed_metadata and ss.get("embed_metadata", True):
            pps.append({"key": "FFmpegMetadata", "add_chapters": True, "add_metadata": True})
        if j.embed_thumbnail and ss.get("embed_thumbnail", True):
            pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
        if pps:
            o["postprocessors"] = pps
    else:
        # Audio-only
        o["format"] = "ba/b/best"
        pps = []
        if "MP3" in j.quality:
            bitrate = j.quality.split()[1] if len(j.quality.split()) > 1 else "320"
            pps.append({"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": bitrate})
        elif "M4A" in j.quality:
            pps.append({"key": "FFmpegExtractAudio", "preferredcodec": "m4a"})
        elif "WAV" in j.quality:
            pps.append({"key": "FFmpegExtractAudio", "preferredcodec": "wav"})
        
        if j.embed_metadata and ss.get("embed_metadata", True):
            pps.append({"key": "FFmpegMetadata", "add_chapters": True, "add_metadata": True})
        if j.embed_thumbnail and ss.get("embed_thumbnail", True):
            pps.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})
        if pps:
            o["postprocessors"] = pps

    return o


class Manager:
    def __init__(self) -> None:
        self.jobs: list[Job] = []
        self.q: queue.Queue = queue.Queue()
        self.lock = threading.Lock()
        self.running = 0
        self.limit = 2
        self.paused = False
        for _ in range(4):
            threading.Thread(target=self._worker, daemon=True).start()

    def add(self, j: Job) -> bool:
        """Enqueue *j*. Returns False if duplicate active job."""
        with self.lock:
            if any(x.key == j.key and x.status in ACTIVE for x in self.jobs):
                return False
            self.jobs.append(j)
        if not self.paused:
            self.q.put(j)
        return True

    def cancel(self, jid: str) -> None:
        with self.lock:
            for j in self.jobs:
                if j.id == jid and j.status in ACTIVE:
                    j.cancel = True
                    if j.status == "Queued":
                        j.status = j.stage = "Cancelled"

    def retry(self, jid: str) -> None:
        with self.lock:
            for j in self.jobs:
                if j.id == jid and j.status in ("Failed", "Cancelled"):
                    j.status = j.stage = "Queued"
                    j.cancel = False
                    j.error = ""
                    j.raw_error = ""
                    j.pct = 0
                    if not self.paused:
                        self.q.put(j)

    def pause_all(self) -> None:
        self.paused = True

    def resume_all(self) -> None:
        self.paused = False
        with self.lock:
            for j in self.jobs:
                if j.status == "Queued":
                    self.q.put(j)

    def move_up(self, jid: str) -> None:
        with self.lock:
            for i, j in enumerate(self.jobs):
                if j.id == jid and i > 0:
                    self.jobs[i - 1], self.jobs[i] = self.jobs[i], self.jobs[i - 1]
                    break

    def move_down(self, jid: str) -> None:
        with self.lock:
            for i, j in enumerate(self.jobs):
                if j.id == jid and i < len(self.jobs) - 1:
                    self.jobs[i + 1], self.jobs[i] = self.jobs[i], self.jobs[i + 1]
                    break

    def clear_finished(self) -> None:
        with self.lock:
            self.jobs = [j for j in self.jobs if j.status in ACTIVE]

    def _worker(self) -> None:
        while True:
            j = self.q.get()
            if self.paused or j.cancel or j.status != "Queued":
                continue
            while True:
                with self.lock:
                    if not self.paused and self.running < self.limit:
                        self.running += 1
                        break
                time.sleep(0.3)
            try:
                self._run(j)
            finally:
                with self.lock:
                    self.running -= 1

    def _run(self, j: Job) -> None:
        def hook(d: dict) -> None:
            if j.cancel:
                raise Cancelled()
            if d["status"] == "downloading":
                tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                j.done = d.get("downloaded_bytes") or 0
                j.total = tot
                j.pct = (j.done / tot * 100.0) if tot else 0.0
                j.speed = d.get("speed") or 0.0
                j.eta = int(d.get("eta") or 0)
                vc = (d.get("info_dict") or {}).get("vcodec")
                if vc not in (None, "none"):
                    j.stage = "Downloading video stream"
                else:
                    j.stage = "Downloading audio stream"
            elif d["status"] == "finished":
                j.stage = "Stream download complete"

        def pp(d: dict) -> None:
            if d["status"] == "started":
                j.status = "Processing"
                pname = d.get("postprocessor", "")
                if "Merger" in pname:
                    j.stage = "Merging video & audio with FFmpeg"
                elif "ExtractAudio" in pname:
                    j.stage = "Extracting & converting audio"
                elif "Metadata" in pname:
                    j.stage = "Embedding tags & chapters"
                elif "EmbedThumbnail" in pname:
                    j.stage = "Embedding cover art"
                else:
                    j.stage = f"Processing ({pname})"
            elif d["status"] == "finished":
                j.stage = "Post-processing complete"

        j.status = "Downloading"
        j.stage = "Connecting to YouTube"
        try:
            os.makedirs(j.outdir, exist_ok=True)
            if shutil.disk_usage(j.outdir).free < 200 * 2**20:
                raise OSError("Not enough disk space in the destination folder")

            with YoutubeDL(build_opts(j, hook, pp)) as y:
                info = y.extract_info(j.url, download=True)

            rd_list: list[dict] = info.get("requested_downloads") or []
            rd: dict = rd_list[0] if rd_list else {}

            filepath = rd.get("filepath") or info.get("_filename") or ""
            if not filepath or not os.path.exists(filepath):
                for entry in rd_list:
                    candidate = entry.get("filepath") or entry.get("_filename") or ""
                    if candidate and os.path.exists(candidate):
                        filepath = candidate
                        break

            # Fallback check if extension changed during post-processing
            if not filepath or not os.path.exists(filepath):
                base_cand = os.path.join(j.outdir, j.template)
                for ext in (".mp4", ".mp3", ".m4a", ".webm", ".mkv"):
                    cand = base_cand + ext
                    if os.path.exists(cand):
                        filepath = cand
                        break

            # Search outdir for the most recently completed file matching the media extensions
            if not filepath or not os.path.exists(filepath):
                try:
                    candidates = [
                        os.path.join(j.outdir, f) for f in os.listdir(j.outdir)
                        if f.endswith((".mp4", ".mp3", ".m4a", ".webm", ".mkv"))
                    ]
                    if candidates:
                        candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                        filepath = candidates[0]
                except Exception:
                    pass

            j.file = filepath
            j.status = "Done"
            j.stage = "Completed"
            j.pct = 100.0
            size = os.path.getsize(j.file) if j.file and os.path.exists(j.file) else 0
            res = f"{rd.get('height')}p" if j.kind == "Video" and rd.get("height") else j.quality

            history.add({
                "id": uuid.uuid4().hex[:8],
                "title": j.title,
                "file": j.file,
                "format": os.path.splitext(j.file)[1][1:].upper() if j.file else "",
                "resolution": res,
                "size": size,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            log.info("Done: %s (%s)", j.title, fmt_size(size))

            # Play completion sound if enabled on Windows
            ss = load_settings()
            if ss.get("sound_on_finish", True) and winsound:
                try:
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
                except Exception:
                    pass

        except Exception as e:
            if j.cancel or isinstance(e, Cancelled):
                j.status = j.stage = "Cancelled"
            else:
                j.status = j.stage = "Failed"
                j.error = friendly(e)
                j.raw_error = sanitize_error(e)
                log.error("Failed %s: %s", j.url, str(e)[:300])


@st.cache_resource
def get_manager() -> Manager:
    return Manager()
