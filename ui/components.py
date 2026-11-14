"""Reusable UI components for YT Video Downloader with clean, modern layout."""
from __future__ import annotations
import base64
from pathlib import Path
import streamlit as st
from config.settings import APP_NAME, TAGLINE, VERSION
from utils.helpers import fmt_size, fmt_time
from utils.network import get_network_url, generate_qr_code_base64


def render_brand_header(logo_path: Path) -> None:
    """Render clean, modern top hero branding without clutter."""
    logo_b64 = ""
    if logo_path.exists():
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()

    img_html = (
        f'<img src="data:image/png;base64,{logo_b64}" width="40" height="40" style="border-radius: 8px; object-fit: contain;" />'
        if logo_b64
        else '<span style="font-size:24px; color: var(--accent);">▶</span>'
    )

    st.markdown(
        f"""
        <div class="kuro-brand-wrap">
            {img_html}
            <div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <h1 class="kuro-brand-title">{APP_NAME}</h1>
                    <span class="kuro-badge-pill">v{VERSION}</span>
                </div>
                <p style="margin: 2px 0 0 0; font-size: 13.5px; color: var(--text-secondary); font-weight: 500;">
                    {TAGLINE}
                </p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_preview_card(meta: dict) -> None:
    """Render modern preview card with thumbnail duration overlay and resolution badges."""
    import html
    raw_t = meta.get("title", "Untitled Video")
    raw_ch = meta.get("channel", "Unknown Channel")
    t = html.escape(str(raw_t))
    ch = html.escape(str(raw_ch))
    dur_sec = meta.get("duration")
    dur = fmt_time(dur_sec) if dur_sec else "Live"
    thumb = meta.get("thumb", "")
    heights = meta.get("heights", [])

    chips_html = ""
    for i, h in enumerate(heights[:6]):
        cls = "kuro-chip kuro-chip-accent" if i == 0 else "kuro-chip"
        chips_html += f'<span class="{cls}">{h}p</span>'

    st.markdown(
        f"""
        <div class="kuro-preview">
            <div class="kuro-preview-thumb-wrap">
                <img class="kuro-preview-thumb" src="{thumb}" alt="Thumbnail" />
                <span class="kuro-thumb-duration">{dur}</span>
            </div>
            <div class="kuro-preview-info">
                <div>
                    <h3 class="kuro-preview-title">{t}</h3>
                    <div class="kuro-preview-channel">
                        <span>📺 {ch}</span>
                        <span>&bull;</span>
                        <span>{dur}</span>
                    </div>
                </div>
                <div>
                    <div style="font-size: 12px; font-weight: 600; color: var(--text-muted); margin-bottom: 6px;">
                        Available Stream Qualities
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                        {chips_html}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_phone_sync_panel(port: int = 8501) -> None:
    """Render 'Use on your phone' panel with clean QR code and instructions."""
    net_url = get_network_url(port)
    qr_b64 = generate_qr_code_base64(net_url)

    st.markdown("### 📱 Instant Mobile Sync (Same Wi-Fi)")
    st.caption("Access your download queue and transfer files directly to your phone over Wi-Fi.")

    c1, c2 = st.columns([1, 2])
    with c1:
        if qr_b64:
            st.markdown(
                f"""
                <div style="padding: 10px; background: white; border-radius: 14px; display: inline-block;">
                    <img src="{qr_b64}" width="150" height="150" style="display: block;" />
                </div>
                """,
                unsafe_allow_html=True,
            )
    with c2:
        st.markdown(
            f"""
            <div style="background: var(--bg-surface-raised); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 14px 18px; margin-bottom: 12px;">
                <div style="font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 700;">Direct Wi-Fi Address</div>
                <div style="font-size: 16px; font-weight: 700; color: var(--accent); font-family: monospace; margin-top: 4px;">{net_url}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            **How to connect:**
            1. Ensure your phone is connected to the same Wi-Fi.
            2. Scan the QR code with your phone's camera.
            3. Tap **'📥 To Device'** to save files directly to your phone!
            """
        )
