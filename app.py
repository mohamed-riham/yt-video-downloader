"""YT Video Downloader — Fast, High Quality Video & Audio Downloader.

Windows-first YouTube downloader built with Python 3.10+, Streamlit, yt-dlp, and FFmpeg.
"""
from __future__ import annotations

import base64
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from config import settings as cfg
from core import metadata as md
from core.download_manager import ACTIVE, Job, get_manager
from ui import components as comp
from ui import theme
from utils import history as hist
from utils.ffmpeg import find_ffmpeg, ffmpeg_version
from utils.helpers import (
    check_clipboard_for_url,
    classify,
    ensure_logo,
    extract_urls,
    ffmpeg_path,
    fmt_size,
    fmt_time,
    friendly,
    pick_folder,
    reveal,
    safe_template,
    sanitize_error,
)

ROOT = Path(__file__).parent
LOGO = ensure_logo(ROOT / "assets" / "logo.png")
FAVICON = ROOT / "assets" / "favicon.png"

st.set_page_config(
    page_title=cfg.APP_NAME,
    page_icon=str(FAVICON if FAVICON.exists() else LOGO),
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load settings and configure manager
S = cfg.load()
mgr = get_manager()
mgr.limit = int(S.get("concurrent", 2))

# Apply Custom Theme & CSS
accent_hex = cfg.ACCENTS.get(S.get("accent", "Teal"), "#65D6C4")
current_theme = S.get("theme", "dark")
st.markdown(theme.get_css(theme=current_theme, accent_color=accent_hex), unsafe_allow_html=True)


# ====================================================================
# PAGE 1: DASHBOARD
# ====================================================================
def page_dashboard() -> None:
    comp.render_brand_header(LOGO)

    ck_browser = S.get("cookies_browser", "None")
    ck_file = S.get("cookies_file", "").strip()

    # Top Hero Card
    with st.container(border=True):
        col_mode, col_clip = st.columns([3, 1])
        with col_mode:
            batch_mode = st.toggle("📋 Batch Mode (Multiple URLs)", value=False)
        with col_clip:
            clip_url = check_clipboard_for_url()
            if clip_url and not batch_mode:
                if st.button("📌 Paste Copied Link", use_container_width=True):
                    st.session_state["target_url"] = clip_url
                    st.rerun()

        if not batch_mode:
            url_input = st.text_input(
                "YouTube Video or Playlist URL",
                placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/...",
                key="target_url",
            )
            raw_url = url_input.strip()
        else:
            batch_text = st.text_area(
                "Paste multiple YouTube URLs (one per line)",
                placeholder="https://www.youtube.com/watch?v=...\nhttps://youtu.be/...\nhttps://www.youtube.com/playlist?list=...",
                height=110,
                key="batch_urls",
            )
            raw_url = ""
            batch_list = []
            batch_list = extract_urls(batch_text)
            if batch_list:
                st.caption(f"Detected **{len(batch_list)}** valid YouTube URL(s).")

    # Batch Mode Action
    if batch_mode:
        if batch_list:
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                b_kind = st.radio("Format", ["Video", "Audio"], horizontal=True, key="b_kind")
            with c2:
                b_qual = (
                    st.selectbox("Resolution", ["Best", "1080p", "720p", "480p"], key="b_q")
                    if b_kind == "Video"
                    else st.selectbox("Bitrate", ["MP3 320 kbps", "MP3 256 kbps", "MP3 192 kbps"], key="b_q")
                )
            with c3:
                st.write("")
                st.write("")
                if st.button("🚀 Enqueue All Links", type="primary", use_container_width=True):
                    added = 0
                    for u in batch_list:
                        j = Job(
                            id=uuid.uuid4().hex[:8],
                            key=f"{u}|{b_kind}|{b_qual}",
                            url=u,
                            title=f"Batch Item ({u[-11:] if len(u) >= 11 else u})",
                            channel="",
                            thumb="",
                            kind=b_kind,
                            quality=b_qual,
                            outdir=S.get("download_dir", str(Path.home() / "Downloads")),
                            template=safe_template(S.get("template", "%(title)s")),
                            embed_metadata=S.get("embed_metadata", True),
                            embed_thumbnail=S.get("embed_thumbnail", True),
                        )
                        if mgr.add(j):
                            added += 1
                    st.toast(f"Queued {added} downloads from batch!")
                    st.rerun()
        _render_queue()
        return

    # Single URL Inspection
    if not raw_url:
        _render_queue()
        return

    ctype = classify(raw_url)
    if ctype == "invalid":
        st.error("Please enter a valid YouTube video or playlist URL.")
        _render_queue()
        return

    # Fetch Metadata
    with st.spinner("Analyzing media stream..."):
        try:
            meta = md.fetch(raw_url, playlist=(ctype == "playlist"), browser=ck_browser, cfile=ck_file)
        except Exception as e:
            st.error(friendly(e))
            with st.expander("Technical details"):
                st.code(sanitize_error(e))
            _render_queue()
            return

    # Single Video / Playlist Configuration
    if meta.get("type") == "video":
        comp.render_preview_card(meta)

        with st.container(border=True):
            fcol1, fcol2, fcol3 = st.columns([1, 1, 1])

            with fcol1:
                kind = st.radio("Output Type", ["Video", "Audio"], horizontal=True)

            with fcol2:
                if kind == "Video":
                    available_h = [f"{h}p" for h in meta.get("heights", [])]
                    preset = ["Best (Max)"] + (available_h if available_h else ["1080p", "720p", "480p", "360p"])
                    qual = st.selectbox("Resolution Target", preset)
                else:
                    qual = st.selectbox("Audio Quality Preset", ["MP3 320 kbps", "MP3 256 kbps", "MP3 192 kbps", "M4A Original", "WAV"])

            with fcol3:
                st.write("")
                st.write("")
                dl_btn = st.button("⚡ Download Now", type="primary", use_container_width=True)

            # Advanced Trimming & Subtitles Expander
            with st.expander("✂️ Time Range & Subtitle Options"):
                tcol1, tcol2, scol1, scol2 = st.columns(4)
                with tcol1:
                    start_t = st.text_input("Start Time (e.g. 00:01:30)", placeholder="00:00:00")
                with tcol2:
                    end_t = st.text_input("End Time (e.g. 00:03:45)", placeholder="")
                with scol1:
                    sub_opt = st.checkbox("Download Subtitles", value=S.get("download_subtitles", False))
                with scol2:
                    embed_sub = st.checkbox("Embed Subtitles into MP4", value=False, disabled=(not sub_opt or kind != "Video"))

            if dl_btn:
                j = Job(
                    id=uuid.uuid4().hex[:8],
                    key=f"{meta['id']}|{kind}|{qual}|{start_t}-{end_t}",
                    url=raw_url,
                    title=meta.get("title", "Video"),
                    channel=meta.get("channel", ""),
                    thumb=meta.get("thumb", ""),
                    kind=kind,
                    quality=qual,
                    outdir=S.get("download_dir", str(Path.home() / "Downloads")),
                    template=safe_template(S.get("template", "%(title)s")),
                    subtitles=sub_opt,
                    embed_subs=embed_sub,
                    start_time=start_t,
                    end_time=end_t,
                    embed_metadata=S.get("embed_metadata", True),
                    embed_thumbnail=S.get("embed_thumbnail", True),
                )
                if mgr.add(j):
                    st.toast(f"Queued: {j.title}")
                    st.rerun()
                else:
                    st.warning("This item is already active in the queue.")

    elif meta.get("type") == "playlist":
        st.subheader(f"📑 Playlist: {meta.get('title')}")
        st.caption(f"Channel: {meta.get('channel')} &bull; {meta.get('count')} item(s)")

        pcol1, pcol2, pcol3 = st.columns([1, 1, 1])
        with pcol1:
            p_kind = st.radio("Format", ["Video", "Audio"], horizontal=True, key="p_kind")
        with pcol2:
            p_qual = (
                st.selectbox("Resolution", ["Best", "1080p", "720p", "480p"], key="p_q")
                if p_kind == "Video"
                else st.selectbox("Bitrate", ["MP3 320 kbps", "MP3 256 kbps", "MP3 192 kbps"], key="p_q")
            )
        with pcol3:
            st.write("")
            st.write("")
            if st.button("🚀 Download Entire Playlist", type="primary", use_container_width=True):
                added = 0
                for it in meta.get("entries", []):
                    j = Job(
                        id=uuid.uuid4().hex[:8],
                        key=f"{it['id']}|{p_kind}|{p_qual}",
                        url=f"https://www.youtube.com/watch?v={it['id']}",
                        title=it.get("title", it["id"]),
                        channel=it.get("channel", meta.get("channel", "")),
                        thumb=f"https://i.ytimg.com/vi/{it['id']}/mqdefault.jpg",
                        kind=p_kind,
                        quality=p_qual,
                        outdir=S.get("download_dir", str(Path.home() / "Downloads")),
                        template=safe_template(S.get("template", "%(title)s")),
                        group=meta.get("title", ""),
                        group_title=meta.get("title", ""),
                        embed_metadata=S.get("embed_metadata", True),
                        embed_thumbnail=S.get("embed_thumbnail", True),
                    )
                    if mgr.add(j):
                        added += 1
                st.toast(f"Queued {added} playlist items!")
                st.rerun()

    _render_queue()


@st.fragment(run_every=1)
def _render_queue() -> None:
    """Render the active and finished jobs queue with live real-time auto-refresh."""
    st.markdown("---")
    qcol1, qcol2, qcol3 = st.columns([3, 1, 1])
    with qcol1:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 8px;">
                <h3 style="margin: 0; font-size: 20px; font-weight: 800;">⚡ Live Transfer Queue</h3>
                <span class="kuro-badge-pill">Live Sync</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with qcol2:
        if mgr.paused:
            if st.button("▶ Resume All", use_container_width=True):
                mgr.resume_all()
                st.rerun()
        else:
            if st.button("⏸ Pause All", use_container_width=True):
                mgr.pause_all()
                st.rerun()
    with qcol3:
        if st.button("🧹 Clear Finished", use_container_width=True):
            mgr.clear_finished()
            st.rerun()

    if not mgr.jobs:
        st.info("The transfer queue is currently empty. Paste a link above to begin.")
        return

    # Render each job
    for i, j in enumerate(list(mgr.jobs)):
        with st.container(border=True):
            c_info, c_action = st.columns([4, 1.2])
            with c_info:
                icon = "🎬" if j.kind == "Video" else "🎵"
                st.markdown(f"<div style='font-size: 16px; font-weight: 750; margin-bottom: 6px; color: var(--text-primary);'>{icon} {j.title}</div>", unsafe_allow_html=True)

                speed_str = f"⚡ {fmt_size(j.speed)}/s" if j.speed else ""
                eta_str = f"⏱️ ETA {fmt_time(j.eta)}" if j.eta else ""

                if j.status == "Done":
                    status_badge = '<span class="kuro-chip kuro-chip-accent">✨ Completed</span>'
                    file_size = os.path.getsize(j.file) if j.file and os.path.exists(j.file) else j.total
                    size_label = f" • <b>{fmt_size(file_size)}</b>" if file_size else ""
                    st.markdown(f"<div style='margin-bottom: 6px;'>{status_badge} &bull; <span style='color:var(--text-secondary); font-weight:600;'>{j.kind} ({j.quality}){size_label}</span></div>", unsafe_allow_html=True)
                    if j.file:
                        st.caption(f"💾 Saved to: `{j.file}`")
                    st.progress(1.0, text=f"100% • Completed & Ready ({fmt_size(file_size)})")
                elif j.status == "Failed":
                    status_badge = '<span class="kuro-chip" style="background: rgba(239, 68, 68, 0.16); color: var(--error); border-color: var(--error);">✖ Failed</span>'
                    st.markdown(f"<div style='margin-bottom: 6px;'>{status_badge} &bull; <span style='color:var(--text-secondary);'>{j.kind} ({j.quality})</span></div>", unsafe_allow_html=True)
                elif j.status == "Queued":
                    status_badge = f'<span class="kuro-chip kuro-chip-warning">⏳ {j.stage}</span>'
                    st.markdown(f"<div style='margin-bottom: 6px;'>{status_badge} &bull; <span style='color:var(--text-secondary);'>{j.kind} ({j.quality})</span></div>", unsafe_allow_html=True)
                    st.progress(0.0, text="⏳ In Queue — Waiting for download slot...")
                else:
                    # Downloading or Processing
                    badge_class = "kuro-chip-success" if j.status == "Downloading" else "kuro-chip-warning"
                    status_badge = f'<span class="kuro-chip {badge_class}">🟢 {j.stage}</span>'
                    details = f"{status_badge} &bull; <span style='font-weight:600; color:var(--text-secondary);'>{j.kind} ({j.quality})</span>"
                    if speed_str or eta_str:
                        details += f" &bull; <span style='color:var(--accent); font-weight:700;'>{speed_str} {eta_str}</span>"
                    st.markdown(f"<div style='margin-bottom: 8px;'>{details}</div>", unsafe_allow_html=True)

                    pct_val = max(0.0, min(1.0, (j.pct or 0.0) / 100.0))
                    prog_text = f"{j.pct:.1f}% • {j.stage}"
                    if j.done and j.total and ("(" not in j.stage):
                        prog_text += f" ({fmt_size(j.done)} / {fmt_size(j.total)})"
                    if speed_str:
                        prog_text += f" • {speed_str}"
                    if eta_str:
                        prog_text += f" • {eta_str}"
                    st.progress(pct_val, text=prog_text)

                if j.error:
                    st.error(j.error)
                    if j.raw_error:
                        with st.expander("Technical Error Details"):
                            st.code(j.raw_error)

            with c_action:
                if j.status == "Done" and j.file:
                    if st.button("📂 Locate File", key=f"rev_{j.id}", use_container_width=True):
                        ok, msg = reveal(j.file)
                        st.toast(msg)

                    # Direct phone/browser file download button
                    if os.path.exists(j.file):
                        try:
                            with open(j.file, "rb") as f:
                                st.download_button(
                                    "📥 To Device",
                                    data=f.read(),
                                    file_name=os.path.basename(j.file),
                                    key=f"dl_dev_{j.id}",
                                    use_container_width=True,
                                )
                        except Exception:
                            pass

                elif j.status in ACTIVE:
                    if st.button("✖ Cancel", key=f"cnc_{j.id}", use_container_width=True):
                        mgr.cancel(j.id)
                        st.rerun()
                elif j.status in ("Failed", "Cancelled"):
                    if st.button("🔄 Retry", key=f"rt_{j.id}", use_container_width=True):
                        mgr.retry(j.id)
                        st.rerun()


# ====================================================================
# PAGE 2: DOWNLOAD HISTORY
# ====================================================================
def page_history() -> None:
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 26px; font-weight: 800;">📜 Download History & Library</h1>
            <p style="margin: 4px 0 0 0; color: var(--text-secondary); font-size: 13.5px;">Inspect, filter, play, and export your captured media records.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    stats = hist.get_stats()
    sc1, sc2, sc3, sc4 = st.columns(4)
    sc1.metric("📥 Total Downloads", stats["total_downloads"])
    sc2.metric("💾 Total Captured", fmt_size(stats["total_bytes"]))
    sc3.metric("🎬 Video Files", stats["video_count"])
    sc4.metric("🎵 Audio Tracks", stats["audio_count"])

    st.markdown("---")
    hcol1, hcol2, hcol3 = st.columns([2, 1, 1])
    with hcol1:
        search_q = st.text_input("🔍 Search library", placeholder="Search by video title, extension or channel...")
    with hcol2:
        kind_filter = st.selectbox("Media Type", ["all", "video", "audio"], format_func=lambda x: {"all": "✨ All Types", "video": "🎬 Video Only", "audio": "🎵 Audio Only"}.get(x, x))
    with hcol3:
        sort_choice = st.selectbox(
            "Sort Order",
            ["date_desc", "date_asc", "size_desc", "size_asc", "title_asc"],
            format_func=lambda x: {
                "date_desc": "⏱️ Newest First",
                "date_asc": "📅 Oldest First",
                "size_desc": "📦 Largest Size",
                "size_asc": "🪶 Smallest Size",
                "title_asc": "🔤 Title (A-Z)",
            }.get(x, x),
        )

    records = hist.search_and_filter(query=search_q, kind=kind_filter, sort_by=sort_choice)

    act_col1, act_col2 = st.columns([3, 1])
    with act_col2:
        if records:
            csv_data = hist.export_csv()
            st.download_button(
                "📥 Export CSV Log",
                data=csv_data,
                file_name=f"yt_download_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

    if not records:
        st.info("No downloads match your current search or filter criteria.")
        return

    for item in records:
        with st.container(border=True):
            c_t, c_f, c_s, c_d, c_b = st.columns([4, 1.2, 1.2, 1.8, 1.8])
            fmt_str = str(item.get("format", "")).upper()
            fmt_badge = f'<span class="kuro-chip kuro-chip-accent">{fmt_str}</span>'
            c_t.markdown(f"**{item.get('title', 'Unknown')}**")
            c_f.markdown(fmt_badge, unsafe_allow_html=True)
            c_s.markdown(f"<span style='color:var(--text-secondary); font-weight:650;'>{fmt_size(item.get('size', 0))}</span>", unsafe_allow_html=True)
            c_d.markdown(f"<span style='color:var(--text-muted); font-size:12px;'>{item.get('date', '')}</span>", unsafe_allow_html=True)
            with c_b:
                fpath = item.get("file", "")
                if fpath:
                    if st.button("📂 Locate", key=f"loc_{item.get('id')}", use_container_width=True):
                        ok, msg = reveal(fpath)
                        st.toast(msg)

    if st.button("🗑️ Clear Entire History", type="secondary"):
        hist.clear()
        st.toast("Download history cleared.")
        st.rerun()


# ====================================================================
# PAGE 3: COOKIE GUIDE
# ====================================================================
def page_cookie_guide() -> None:
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 26px; font-weight: 800;">🍪 In-App Cookie & Bot Verification Guide</h1>
            <p style="margin: 4px 0 0 0; color: var(--text-secondary); font-size: 13.5px;">Bypass YouTube bot checks and unlock private / age-restricted streams safely.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Status banner
    ck_browser = S.get("cookies_browser", "None")
    ck_file = S.get("cookies_file", "")
    has_file = ck_file and Path(ck_file).is_file() and Path(ck_file).stat().st_size > 0

    if ck_browser != "None":
        st.success(f"✅ Active cookie source: **{ck_browser.title()} Browser Session**")
    elif has_file:
        st.success(f"✅ Active cookie source: **Exported cookies.txt file** (`{ck_file}`)")
    else:
        st.warning("⚠️ No active cookie source. Follow Method A (Firefox) or Method B (cookies.txt) below to ensure seamless downloads.")

    # Test connection button
    if st.button("🧪 Test YouTube Connection with Active Session"):
        with st.spinner("Connecting to YouTube CDN with your cookie credentials..."):
            try:
                res = md._fetch_uncached("https://www.youtube.com/watch?v=jNQXAC9IVRw", playlist=False, browser=ck_browser, cfile=ck_file)
                st.success(f"🎉 Connection test passed! Successfully verified with YouTube. Stream title: '{res.get('title')}'")
            except Exception as e:
                st.error(f"❌ Connection test failed: {friendly(e)}")
                with st.expander("Technical Error Details"):
                    st.code(sanitize_error(e))

    st.markdown("---")

    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            st.markdown("### 🦊 Method A: Firefox (Recommended)")
            st.markdown("**100% Automatic — No files, No extensions needed**")
            st.markdown(
                """
1. Log into **YouTube.com** inside **Mozilla Firefox**.
2. Click the button below to link Firefox cookies directly.
3. yt-dlp will read Firefox session cookies automatically without exporting anything!

*Why Firefox? Firefox does not lock its cookie database or encrypt sessions with App-Bound locks. It just works seamlessly.*
                """
            )
            if ck_browser.lower() == "firefox":
                st.success("✅ **Firefox cookies are currently ACTIVE!**")
                if st.button("Disable Firefox Cookies", use_container_width=True):
                    S["cookies_browser"] = "None"
                    cfg.save(S)
                    st.rerun()
            else:
                if st.button("🦊 Enable Firefox Cookies (1-Click)", type="primary", use_container_width=True):
                    S["cookies_browser"] = "Firefox"
                    cfg.save(S)
                    st.toast("Firefox cookies activated!")
                    st.rerun()

    with col_b:
        with st.container(border=True):
            st.markdown("### 📄 Method B: Export cookies.txt")
            st.markdown("**Chrome, Edge, Brave, Opera & Vivaldi**")
            st.markdown(
                """
1. Install the free browser extension: [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc).
2. Open **YouTube.com** in your browser.
3. Click the extension icon and tap **Export**.
4. Upload the exported `.txt` file right below!

*Privacy note: Netscape format files are stored and parsed 100% locally on your PC.*
                """
            )

    with st.container(border=True):
        st.markdown("### 📤 Add cookies.txt (Upload or Paste)")
        tab_up, tab_paste = st.tabs(["📁 Upload File", "📝 Paste Text"])

        with tab_up:
            up_file = st.file_uploader("Choose your exported cookies.txt file", type=["txt"], key="cookie_file_uploader")
            if up_file is not None:
                st.info(f"📄 Selected file: **{up_file.name}** ({up_file.size} bytes)")
                if st.button("💾 Save & Activate Uploaded Cookies", type="primary", use_container_width=True, key="btn_save_up_cookie"):
                    target_path = cfg.APP_DIR / "cookies.txt"
                    target_path.write_bytes(up_file.getvalue())
                    S["cookies_file"] = str(target_path)
                    S["cookies_browser"] = "None"
                    cfg.save(S)
                    st.toast("✅ Cookies successfully saved and activated!")
                    st.rerun()

        with tab_paste:
            cookie_text = st.text_area(
                "Paste raw Netscape cookie text here",
                placeholder="# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE...",
                height=130,
                key="raw_cookie_paste",
            )
            if st.button("💾 Save & Activate Pasted Cookies", type="primary", use_container_width=True, key="btn_save_paste_cookie"):
                if cookie_text.strip():
                    target_path = cfg.APP_DIR / "cookies.txt"
                    target_path.write_text(cookie_text.strip(), encoding="utf-8")
                    S["cookies_file"] = str(target_path)
                    S["cookies_browser"] = "None"
                    cfg.save(S)
                    st.toast("✅ Pasted cookies saved and activated!")
                    st.rerun()
                else:
                    st.warning("Please paste valid cookie text before saving.")

        if has_file:
            st.markdown("---")
            cc1, cc2 = st.columns([3, 1])
            with cc1:
                f_size = os.path.getsize(ck_file) if os.path.exists(ck_file) else 0
                st.caption(f"💾 Active file: `{ck_file}` ({f_size} bytes)")
            with cc2:
                if st.button("🗑️ Delete Saved cookies.txt", type="secondary", use_container_width=True, key="btn_del_cookie"):
                    try:
                        if os.path.exists(ck_file):
                            os.remove(ck_file)
                    except Exception:
                        pass
                    S["cookies_file"] = ""
                    cfg.save(S)
                    st.toast("Deleted saved cookie file.")
                    st.rerun()

    is_cloud = os.environ.get("STREAMLIT_SERVER_HEADLESS") == "true" or "/home/appuser" in str(cfg.APP_DIR)
    if is_cloud:
        st.warning(
            "⚠️ **Cloud Instance Notice:** You are viewing this app hosted on Streamlit Community Cloud. "
            f"Files and cookies uploaded here are stored inside this temporary cloud container (`{cfg.APP_DIR}`). "
            "For **100% private and secure** downloads with your personal YouTube account, run the app locally on your Windows PC via `START.bat`."
        )
    else:
        st.info(f"🔒 **Privacy Guarantee:** Your session cookies are stored exclusively on your local computer (`{cfg.APP_DIR}\\cookies.txt`). They are never uploaded or transmitted to any external server.")


# ====================================================================
# PAGE 4: SETTINGS
# ====================================================================
def page_settings() -> None:
    st.markdown(
        """
        <div style="margin-bottom: 20px;">
            <h1 style="margin: 0; font-size: 26px; font-weight: 800;">⚙️ Application Settings</h1>
            <p style="margin: 4px 0 0 0; color: var(--text-secondary); font-size: 13.5px;">Configure your downloading pipeline, visual themes, and local sync.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Appearance & Theme Card
    with st.container(border=True):
        st.markdown("### 🎨 Visual Theme & Vibrant Accents")
        c_th, c_ac = st.columns(2)
        with c_th:
            theme_opt = st.selectbox("Interface Theme", ["dark", "light"], index=0 if S.get("theme", "dark") == "dark" else 1, format_func=lambda x: "🌙 Midnight Glass (Dark)" if x == "dark" else "☀️ Arctic Frost (Light)")
        with c_ac:
            accent_opt = st.selectbox("Accent Glow Color", list(cfg.ACCENTS.keys()), index=list(cfg.ACCENTS.keys()).index(S.get("accent", "Teal")) if S.get("accent") in cfg.ACCENTS else 0)

    # 2. Cookie Authentication Source Card
    with st.container(border=True):
        st.markdown("### 🍪 Browser Cookie Authentication")
        st.caption("Allow yt-dlp to read session cookies directly from your installed browser to bypass bot verification.")
        browsers = ["None", "firefox", "chrome", "edge", "brave", "opera", "vivaldi"]
        curr_b = S.get("cookies_browser", "None").lower()
        b_idx = browsers.index(curr_b) if curr_b in browsers else 0
        browser_opt = st.selectbox("Read Cookies From Browser", browsers, index=b_idx, format_func=lambda x: f"🦊 {x.title()} (Recommended)" if x == "firefox" else f"🌐 {x.title()}" if x != "None" else "🚫 None (Disabled)")

    # 3. File Storage & Templates Card
    with st.container(border=True):
        st.markdown("### 📁 Storage Destination & Naming")
        ocol1, ocol2 = st.columns([3, 1])
        with ocol1:
            default_dir = st.session_state.get("out_dir_val", S.get("download_dir", str(Path.home() / "Downloads")))
            out_dir = st.text_input("Download Destination Folder", value=default_dir)
        with ocol2:
            st.write("")
            st.write("")
            if st.button("📂 Browse Folder", use_container_width=True):
                chosen = pick_folder()
                if chosen:
                    out_dir = chosen
                    st.session_state["out_dir_val"] = chosen
                    st.rerun()

        tmpl = st.text_input("Filename Format Template", value=S.get("template", "%(title)s"))
        st.caption("Available tokens: `%(title)s`, `%(id)s`, `%(channel)s`, `%(resolution)s`")

    # 4. Download Engine Options Card
    with st.container(border=True):
        st.markdown("### 🚀 Engine Preferences & Limits")
        dcol1, dcol2 = st.columns(2)
        with dcol1:
            conc = st.slider("Concurrent Downloads", min_value=1, max_value=5, value=int(S.get("concurrent", 2)))
            retries = st.number_input("Max Network Retries", min_value=1, max_value=20, value=int(S.get("max_retries", 5)))
            rate_lim = st.text_input("Speed Limit (e.g. 5M or leave empty for Unlimited)", value=S.get("rate_limit", ""))
        with dcol2:
            embed_meta = st.checkbox("Embed Metadata, Chapters & Tags into files", value=S.get("embed_metadata", True))
            embed_thumb = st.checkbox("Embed High-Res Cover Art / Thumbnail", value=S.get("embed_thumbnail", True))
            sound_fin = st.checkbox("Play Notification Bell on Completion", value=S.get("sound_on_finish", True))

    # 5. Mobile / Phone Access Card
    with st.container(border=True):
        st.markdown("### 📱 Mobile Access over Local Wi-Fi")
        phone_acc = st.checkbox("Enable Wi-Fi phone access", value=S.get("phone_access", False))
        if phone_acc:
            comp.render_phone_sync_panel(port=8501)

    # 6. Diagnostic System Check Card
    with st.container(border=True):
        st.markdown("### 🩺 System Diagnostics")
        ff_path = find_ffmpeg()
        ff_ver = ffmpeg_version() if ff_path else "Not found"
        js_runtime = "Deno Engine (Active)" if shutil.which("deno") else "Node.js (Active)" if shutil.which("node") else "None detected"

        st.markdown(
            f"""
            <div style="font-size: 13.5px; line-height: 1.8;">
                <div><b>FFmpeg Engine:</b> <code style="color:var(--accent);">{ff_path or '❌ Missing'}</code> (<i>{ff_ver}</i>)</div>
                <div><b>JavaScript Engine:</b> <code style="color:var(--success);">{js_runtime}</code></div>
                <div><b>Output Storage Accessible:</b> {'<span style="color:var(--success); font-weight:700;">✅ Yes</span>' if os.path.isdir(out_dir) else '<span style="color:var(--error); font-weight:700;">❌ Directory does not exist</span>'}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.button("💾 Save All Settings", type="primary", use_container_width=True):
        S["theme"] = theme_opt
        S["accent"] = accent_opt
        S["cookies_browser"] = browser_opt
        S["download_dir"] = out_dir
        S["template"] = tmpl
        S["concurrent"] = conc
        S["max_retries"] = retries
        S["rate_limit"] = rate_lim
        S["embed_metadata"] = embed_meta
        S["embed_thumbnail"] = embed_thumb
        S["sound_on_finish"] = sound_fin
        S["phone_access"] = phone_acc
        cfg.save(S)
        st.toast("Settings saved successfully!")
        st.rerun()


# ====================================================================
# PAGE 5: ABOUT
# ====================================================================
def page_about() -> None:
    comp.render_brand_header(LOGO)
    with st.container(border=True):
        st.markdown(f"### About {cfg.APP_NAME}")
        st.markdown(
            f"**{cfg.APP_NAME}** is an ultra-fast, local-first media capture utility designed for Windows 10 & 11."
        )

        st.markdown("#### 👨‍💻 Creator & Developer")
        st.markdown(
            """
Designed and developed with ❤️ by **Mohamed Riham**.
- **GitHub:** [github.com/mohamed-riham](https://github.com/mohamed-riham)
- **Profile:** [@mohamed-riham](https://github.com/mohamed-riham)
            """
        )

        st.markdown("#### 💎 Core Principles")
        st.markdown(
            """
- **100% Local & Private:** Zero telemetry, zero external trackers, zero accounts required.
- **Studio Precision:** Full 4K 60FPS merging with modern FFmpeg, 320 kbps MP3 conversion, and original Opus/M4A streams.
- **Direct CDN Acceleration:** Direct connection from YouTube's distribution servers to your storage.
            """
        )

        st.markdown("#### ⚡ Open-Source Stack")
        st.markdown(
            """
Built on industry-standard open-source components:
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — High performance media extractor
- [FFmpeg](https://ffmpeg.org/) — Audio & video transcoding and stream merging
- [Streamlit](https://streamlit.io/) — Modern interactive local web interface
- [Pillow](https://python-pillow.org/) — Cover art and thumbnail embedding
            """
        )


# ====================================================================
# NAVIGATION DISPATCH
# ====================================================================
pg = st.navigation(
    [
        st.Page(page_dashboard, title="Dashboard", icon="⚡"),
        st.Page(page_history, title="History", icon="📜"),
        st.Page(page_cookie_guide, title="Cookie Guide", icon="🍪"),
        st.Page(page_settings, title="Settings", icon="⚙️"),
        st.Page(page_about, title="About", icon="ℹ️"),
    ]
)

# Sidebar Creator Branding
with st.sidebar:
    st.markdown("---")
    st.markdown(
        """
        <div style="font-size: 13px; color: var(--text-secondary); text-align: center; padding: 4px 0 8px 0;">
            Created by <a href="https://github.com/mohamed-riham" target="_blank" style="color: var(--accent); font-weight: 700; text-decoration: none;">Mohamed Riham</a>
            <div style="font-size: 11px; opacity: 0.7; margin-top: 3px;">⚡ github.com/mohamed-riham</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

pg.run()
