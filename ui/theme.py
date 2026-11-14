"""Design system and CSS styles for YT Video Downloader.

Features:
- Ultra-modern dark glassmorphism & light theme design
- High-contrast WCAG AA accessible color hierarchy
- Ambient glow & vibrant accent color integration
- Squircle border radii, smooth micro-interactions & hover lifts
- Fully responsive mobile stacking (360-430px) with 44px touch targets
- Clean native layout with zero floating artifacts or unknown shapes
"""
from __future__ import annotations


def get_css(theme: str = "dark", accent_color: str = "#65D6C4") -> str:
    """Return comprehensive custom CSS matching the selected theme and accent."""
    is_dark = theme != "light"

    # Theme Color Tokens
    if is_dark:
        bg_base = "#080B14"
        bg_surface = "rgba(16, 24, 44, 0.78)"
        bg_surface_raised = "rgba(25, 36, 64, 0.85)"
        bg_card_hover = "rgba(22, 33, 58, 0.92)"
        border_subtle = "rgba(255, 255, 255, 0.08)"
        border_hover = "rgba(255, 255, 255, 0.18)"
        text_primary = "#F8FAFC"
        text_secondary = "#94A3B8"
        text_muted = "#64748B"
        input_bg = "rgba(11, 17, 33, 0.85)"
        accent_glow = f"{accent_color}33"
        accent_soft = f"{accent_color}1A"
        shadow_card = "0 8px 30px -4px rgba(0, 0, 0, 0.5), inset 0 1px 0 0 rgba(255, 255, 255, 0.08)"
    else:
        bg_base = "#F4F7FB"
        bg_surface = "rgba(255, 255, 255, 0.90)"
        bg_surface_raised = "rgba(241, 245, 249, 0.95)"
        bg_card_hover = "#FFFFFF"
        border_subtle = "rgba(0, 0, 0, 0.08)"
        border_hover = "rgba(0, 0, 0, 0.18)"
        text_primary = "#0F172A"
        text_secondary = "#475569"
        text_muted = "#94A3B8"
        input_bg = "#FFFFFF"
        accent_glow = f"{accent_color}2B"
        accent_soft = f"{accent_color}14"
        shadow_card = "0 6px 20px -2px rgba(15, 23, 42, 0.06), inset 0 1px 0 0 rgba(255, 255, 255, 0.8)"

    return f"""
    <style>
    /* ====================================================================
       YT VIDEO DOWNLOADER DESIGN SYSTEM
       ==================================================================== */
    :root {{
        --bg-base: {bg_base};
        --bg-surface: {bg_surface};
        --bg-surface-raised: {bg_surface_raised};
        --bg-card-hover: {bg_card_hover};
        --border-subtle: {border_subtle};
        --border-hover: {border_hover};
        --text-primary: {text_primary};
        --text-secondary: {text_secondary};
        --text-muted: {text_muted};
        --input-bg: {input_bg};
        --accent: {accent_color};
        --accent-glow: {accent_glow};
        --accent-soft: {accent_soft};
        --success: #10B981;
        --warning: #F59E0B;
        --error: #EF4444;
        --info: #38BDF8;
        --radius-xs: 6px;
        --radius-sm: 10px;
        --radius-md: 16px;
        --radius-lg: 22px;
        --radius-full: 9999px;
        --shadow-card: {shadow_card};
        --transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    /* Global Base & Ambient Light */
    .stApp {{
        background-color: var(--bg-base) !important;
        background-image: 
            radial-gradient(circle at 10% 0%, {accent_color}12 0%, transparent 40%),
            radial-gradient(circle at 90% 10%, #6366F112 0%, transparent 40%) !important;
        background-attachment: fixed !important;
        color: var(--text-primary) !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", system-ui, sans-serif !important;
        -webkit-font-smoothing: antialiased;
    }}

    /* Clean Streamlit Default Chrome */
    #MainMenu, footer, .stDeployButton, [data-testid="stToolbarActions"] {{
        display: none !important;
    }}

    /* Header styling - Clean sidebar toggle */
    header[data-testid="stHeader"] {{
        background: transparent !important;
    }}
    button[data-testid="stSidebarCollapseButton"] {{
        color: var(--text-primary) !important;
        background: transparent !important;
        border: none !important;
        border-radius: var(--radius-sm) !important;
        transition: var(--transition) !important;
    }}
    button[data-testid="stSidebarCollapseButton"]:hover {{
        background: var(--bg-surface-raised) !important;
        color: var(--accent) !important;
    }}

    /* Sidebar Glass Styling */
    section[data-testid="stSidebar"] {{
        background-color: var(--bg-surface) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }}
    section[data-testid="stSidebar"] hr {{
        border-color: var(--border-subtle) !important;
    }}

    /* Modern Glass Containers and Cards */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: var(--radius-md) !important;
        border: 1px solid var(--border-subtle) !important;
        background: var(--bg-surface) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        box-shadow: var(--shadow-card) !important;
        transition: var(--transition) !important;
        margin-bottom: 16px !important;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
        border-color: var(--border-hover) !important;
        background: var(--bg-card-hover) !important;
    }}
    div[data-testid="stVerticalBlockBorderWrapper"] > div {{
        border: none !important;
        background: transparent !important;
        padding: 16px 20px !important;
    }}

    .kuro-card {{
        background: var(--bg-surface);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 20px 22px;
        margin-bottom: 16px;
        box-shadow: var(--shadow-card);
        transition: var(--transition);
    }}
    .kuro-card:hover {{
        border-color: var(--border-hover);
        background: var(--bg-card-hover);
    }}

    /* Brand Header Aesthetics */
    .kuro-brand-wrap {{
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 16px;
    }}
    .kuro-brand-title {{
        margin: 0;
        font-size: 26px;
        font-weight: 800;
        letter-spacing: -0.5px;
        color: var(--text-primary);
        line-height: 1.2;
    }}
    .kuro-badge-pill {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 2px 10px;
        border-radius: var(--radius-full);
        background: var(--accent-soft);
        border: 1px solid var(--accent);
        color: var(--accent);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
        vertical-align: middle;
    }}

    /* Buttons: Primary, Secondary, Ghost */
    .stButton > button {{
        min-height: 44px !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 650 !important;
        font-size: 14px !important;
        transition: var(--transition) !important;
        border: 1px solid var(--border-subtle) !important;
        background: var(--bg-surface-raised) !important;
        color: var(--text-primary) !important;
    }}
    .stButton > button:hover {{
        border-color: var(--accent) !important;
        color: var(--text-primary) !important;
        transform: translateY(-1px) !important;
    }}

    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, var(--accent) 0%, #38BDF8 100%) !important;
        color: #060913 !important;
        border: none !important;
        font-weight: 800 !important;
        box-shadow: 0 4px 16px var(--accent-glow) !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        filter: brightness(1.08) !important;
        box-shadow: 0 6px 20px var(--accent-glow) !important;
        transform: translateY(-1px) !important;
    }}

    /* Download Button Specific */
    .stDownloadButton > button {{
        min-height: 40px !important;
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
        transition: var(--transition) !important;
    }}
    .stDownloadButton > button:hover {{
        filter: brightness(1.1) !important;
        transform: translateY(-1px) !important;
    }}

    /* Streamlit Input Fields */
    .stTextInput > div > div, 
    .stTextArea > div > div {{
        background-color: var(--input-bg) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-primary) !important;
        transition: var(--transition) !important;
    }}
    .stTextInput > div > div:focus-within, 
    .stTextArea > div > div:focus-within {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px var(--accent-glow) !important;
    }}
    .stTextInput input, 
    .stTextArea textarea {{
        color: var(--text-primary) !important;
        font-size: 14px !important;
    }}

    /* Selectboxes and Dropdowns */
    .stSelectbox > div > div {{
        background-color: var(--input-bg) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-sm) !important;
        color: var(--text-primary) !important;
        transition: var(--transition) !important;
    }}
    .stSelectbox > div > div:hover {{
        border-color: var(--accent) !important;
    }}

    /* Progress Bar */
    div[data-testid="stProgressBar"] {{
        background-color: rgba(255, 255, 255, 0.08) !important;
        border-radius: var(--radius-full) !important;
        height: 10px !important;
        overflow: hidden !important;
    }}
    div[data-testid="stProgressBar"] > div {{
        background: linear-gradient(90deg, var(--accent) 0%, #38BDF8 100%) !important;
        border-radius: var(--radius-full) !important;
        height: 10px !important;
    }}
    div[data-testid="stProgress"] p {{
        font-size: 13px !important;
        font-weight: 650 !important;
        color: var(--text-primary) !important;
        margin-top: 4px !important;
    }}

    /* Chips and Badges */
    .kuro-chip {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: var(--bg-surface-raised);
        border: 1px solid var(--border-subtle);
        padding: 4px 12px;
        border-radius: var(--radius-full);
        font-size: 12px;
        font-weight: 600;
        color: var(--text-secondary);
        transition: var(--transition);
    }}
    .kuro-chip:hover {{
        border-color: var(--accent);
        color: var(--text-primary);
    }}
    .kuro-chip-accent {{
        background: var(--accent-soft);
        border-color: var(--accent);
        color: var(--accent);
    }}
    .kuro-chip-success {{
        background: rgba(16, 185, 129, 0.15);
        border-color: var(--success);
        color: var(--success);
    }}
    .kuro-chip-warning {{
        background: rgba(245, 158, 11, 0.15);
        border-color: var(--warning);
        color: var(--warning);
    }}

    /* Video Preview Showcase Card */
    .kuro-preview {{
        display: flex;
        flex-direction: row;
        gap: 20px;
        background: var(--bg-surface);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--border-subtle);
        border-radius: var(--radius-md);
        padding: 18px;
        margin-top: 16px;
        box-shadow: var(--shadow-card);
        transition: var(--transition);
    }}
    .kuro-preview:hover {{
        border-color: var(--border-hover);
    }}
    .kuro-preview-thumb-wrap {{
        position: relative;
        width: 250px;
        height: 140px;
        flex-shrink: 0;
        border-radius: var(--radius-sm);
        overflow: hidden;
    }}
    .kuro-preview-thumb {{
        width: 100%;
        height: 100%;
        object-fit: cover;
    }}
    .kuro-thumb-duration {{
        position: absolute;
        bottom: 6px;
        right: 6px;
        background: rgba(0, 0, 0, 0.85);
        color: #FFFFFF;
        font-size: 11px;
        font-weight: 700;
        padding: 2px 6px;
        border-radius: var(--radius-xs);
    }}
    .kuro-preview-info {{
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        flex: 1;
        min-width: 0;
    }}
    .kuro-preview-title {{
        margin: 0 0 6px 0;
        font-size: 17px;
        font-weight: 700;
        line-height: 1.35;
        color: var(--text-primary);
    }}
    .kuro-preview-channel {{
        margin: 0 0 10px 0;
        font-size: 13px;
        color: var(--text-secondary);
        display: flex;
        align-items: center;
        gap: 6px;
    }}

    /* Stat Metric Boxes */
    div[data-testid="stMetric"] {{
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: var(--radius-md) !important;
        padding: 16px 20px !important;
        box-shadow: var(--shadow-card) !important;
        backdrop-filter: blur(12px) !important;
        transition: var(--transition) !important;
    }}
    div[data-testid="stMetric"]:hover {{
        border-color: var(--accent) !important;
    }}
    div[data-testid="stMetricValue"] {{
        font-size: 24px !important;
        font-weight: 800 !important;
        color: var(--text-primary) !important;
    }}

    /* Clean Custom Scrollbar */
    ::-webkit-scrollbar {{
        width: 7px;
        height: 7px;
    }}
    ::-webkit-scrollbar-track {{
        background: var(--bg-base);
    }}
    ::-webkit-scrollbar-thumb {{
        background: rgba(255, 255, 255, 0.18);
        border-radius: var(--radius-full);
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: var(--accent);
    }}

    /* Mobile Responsiveness (360px - 768px) */
    @media (max-width: 768px) {{
        .kuro-preview {{
            flex-direction: column !important;
            padding: 14px !important;
        }}
        .kuro-preview-thumb-wrap {{
            width: 100% !important;
            height: auto !important;
            aspect-ratio: 16 / 9;
        }}
        .stButton > button,
        .stDownloadButton > button {{
            width: 100% !important;
            margin-bottom: 8px !important;
        }}
    }}
    </style>
    """
