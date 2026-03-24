# -*- coding: utf-8 -*-
"""
ui_layout.py
------------
Page configuration, global CSS, and shared layout helpers.

Design tokens
-------------
All visual constants (colours, font sizes, spacing) are defined once here
as Python variables and injected into the global stylesheet via setup_page().
Any new UI file should import what it needs from here rather than hardcoding
values inline.  When a colour or size needs to change, this is the only file
that requires editing.

Colour palette
  CLR_PRIMARY          – black; tab borders, primary button outlines, plot axis lines and text
  CLR_ACCENT           – dark grey; secondary button fill, multiselect chip background
  CLR_MUTED            – mid grey; disabled widget labels, missing inventory items
  CLR_SUBTLE           – light grey; footer text, subtitle text
  CLR_SUCCESS          – green; present inventory items
  CLR_EXTRA            – blue; unexpected/extra inventory items
  CLR_BG_HEADER        – off-white; table header background
  CLR_PLOT_BG          – white; 2D plot canvas and paper background
  CLR_PLOT_GRID        – light grey; 2D plot axis grid lines
  CLR_BTN_LIGHT_BG     – light-gray shading
  CLR_BTN_LIGHT_BORDER – dark-gray border
  CLR_BTN_LIGHT_TEXT   – dark text

Font sizes (px)
  FS_LABEL      – 16   sidebar section labels, slider labels
  FS_BODY       – 13   widget labels, table cells, dropdown options, chip text
  FS_BUTTON     – 12   secondary button text
  FS_MICRO      – 11   ultra-compact button labels (auto-fit domain section)
  FS_TABLE      – 14   metadata/inventory HTML table rows
  FS_TITLE      – 32   page title
  FS_SUBTITLE   – 14   page subtitle
  FS_FOOTER     – 12   footer copyright line
  FS_PLOT_TITLE – 24   main title above Plotly figures
  FS_PLOT_AXIS  – 18   axis labels (e.g., Latitude, Longitude) on Plotly figures
  FS_PLOT_TICK  – 14   numeric tick marks on Plotly axes

Other controls
  TARGET_PLOT_TICKS - number of horizontal ticks/grid lines to plot in 2d/3d plots
"""

import streamlit as st
from datetime import datetime

# ---------------------------------------------------------------------------
# Design tokens — edit here, applies everywhere
# ---------------------------------------------------------------------------

# Colours
CLR_PRIMARY   = "#000000"
CLR_ACCENT    = "#555555"
CLR_MUTED     = "#999999"   # unified: was both #999 and #a0a0a0 in different files
CLR_SUBTLE    = "#666666"
CLR_SUCCESS   = "#0c7b20"
CLR_EXTRA     = "#005bb5"
CLR_BG_HEADER = "#f0f2f6"
# Alternate Button Styles (Select All / Deselect All)
CLR_BTN_LIGHT_BG     = "#e4e6eb"   # light-gray shading
CLR_BTN_LIGHT_BORDER = "#888888"   # dark-gray border
CLR_BTN_LIGHT_TEXT   = "#333333"   # dark text

# Font sizes (integer px values for easy arithmetic; CSS strings built below)
FS_LABEL    = 16
FS_BODY     = 13
FS_BUTTON   = 12
FS_MICRO    = 11   # intentionally smaller: auto-fit domain button labels
FS_TABLE    = 14   # slightly larger than body for HTML table readability
FS_TITLE    = 40
FS_SUBTITLE = 20
FS_FOOTER   = 12

# Plotly figure sizes
FS_PLOT_TITLE = 24
FS_PLOT_AXIS  = 18
FS_PLOT_TICK  = 14

# Plotly colors
CLR_PLOT_BG   = "#ffffff"
CLR_PLOT_GRID = "#e0e0e0" # light gray

# Number of ticks/grid lines to plot on 2d/3d plots
TARGET_PLOT_TICKS = 15

# Title y position (fraction of container height, from top)
PLOT_TITLE_Y = 0.96


# ---------------------------------------------------------------------------
# Page setup and global stylesheet
# ---------------------------------------------------------------------------

def setup_page():
    """Initialize page config and inject all global CSS rules."""
    st.set_page_config(
        page_title="HRDOBS Dataset Explorer & Visualizer | Altug Aksoy",
        page_icon="🌀",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Report a bug': "mailto:aaksoy@miami.edu",
            'Get help': "https://github.com/aaksoy-umiami/hrdobs_visualization",
            'About': """
            ### HRDOBS Dataset Explorer & Visualizer
            **Interactive tool for exploring AI-Ready HDF5 hurricane reconnaissance observations**

            Visualize, filter, and analyze the HRDOBS database — including flight-level,
            dropsonde, SFMR, and radar observations from NOAA and Air Force reconnaissance aircraft.

            **Author:** Altug Aksoy
            **Affiliation:** CIMAS/Rosenstiel School, University of Miami

            *For questions or bug reports, contact aaksoy@miami.edu*
            """
        }
    )

    st.markdown(f"""
    <style>
        /* ------------------------------------------------------------------ */
        /* Page layout                                                         */
        /* ------------------------------------------------------------------ */
        .block-container {{
            padding-top: 3.5rem !important;
            padding-bottom: 1rem !important;
        }}

        /* ------------------------------------------------------------------ */
        /* Tab navigation buttons                                              */
        /* ------------------------------------------------------------------ */
        div[data-testid="column"] button {{
            width: 100%; border-radius: 8px; padding: 10px;
            font-weight: 600; font-size: {FS_BODY}px;
            transition: all 0.3s ease;
            border: 2px solid {CLR_PRIMARY} !important;
        }}
        div[data-testid="column"] button[kind="secondary"] {{
            background-color: rgba(255, 255, 255, 0.05);
            color: rgba(255, 255, 255, 0.7);
        }}
        div[data-testid="column"] button[kind="primary"] {{
            background: linear-gradient(135deg, #2b2b2b 0%, {CLR_PRIMARY} 100%);
            color: white;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }}
        div[data-testid="column"] button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
        }}
        [data-testid="stHorizontalBlock"]:has(button[kind="primary"],
                                              button[kind="secondary"]) {{
            border-bottom: 2px solid {CLR_PRIMARY};
            padding-bottom: 0px; margin-bottom: 0px;
        }}
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {{
            border-bottom: none !important;
        }}

        /* ------------------------------------------------------------------ */
        /* Multiselect chips                                                   */
        /* ------------------------------------------------------------------ */
        span[data-baseweb="tag"] {{
            background-color: {CLR_ACCENT} !important;
            color: #ffffff !important;
            font-size: {FS_BODY}px !important;
        }}
        span[data-baseweb="tag"] svg {{ fill: #ffffff !important; }}
        div[data-baseweb="select"],
        ul[role="listbox"] li,
        li[role="option"] {{ font-size: {FS_BODY}px !important; }}

        /* ------------------------------------------------------------------ */
        /* Sidebar — labels, tooltips, buttons                                */
        /* ------------------------------------------------------------------ */
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
            font-size: {FS_LABEL}px !important;
        }}
        [data-testid="stSidebar"] [data-testid="stTooltipIcon"] {{
            margin-top: 4px;
        }}

        /* Primary sidebar button (white fill, black border) */
        [data-testid="stSidebar"] button[kind="primary"] {{
            background-color: #ffffff !important;
            color: {CLR_PRIMARY} !important;
            border: 3px solid {CLR_PRIMARY} !important;
            font-weight: 600;
        }}

        /* Secondary sidebar button (accent fill, compact) */
        [data-testid="stSidebar"] button[kind="secondary"],
        div[data-testid="stVerticalBlockBorderWrapper"]
            div[data-testid="stButton"] button[kind="secondary"],
        div[data-testid="stVerticalBlockBorderWrapper"]
            div[data-testid="stDownloadButton"] button[kind="secondary"] {{
            background-color: {CLR_ACCENT} !important;
            color: white !important;
            border: 2px solid {CLR_ACCENT} !important;
            padding: 0px 10px !important;
            min-height: 28px !important;
            height: 28px !important;
            border-radius: 6px !important;
        }}
        [data-testid="stSidebar"] button[kind="secondary"] *,
        div[data-testid="stVerticalBlockBorderWrapper"]
            div[data-testid="stButton"] button p,
        div[data-testid="stVerticalBlockBorderWrapper"]
            div[data-testid="stDownloadButton"] button p {{
            font-size: {FS_BUTTON}px !important;
            font-weight: 600 !important;
            line-height: 1 !important;
            margin: 0 !important;
            color: white !important;
        }}

        /* Auto-fit domain buttons: extra-compact label size */
        [data-testid="stSidebar"] div[data-testid="stButton"].domain-btn button p {{
            font-size: {FS_MICRO}px !important;
        }}
        [data-testid="stSidebar"] div[data-testid="stButton"].domain-btn button {{
            padding: 0px 2px !important;
            min-height: 24px !important;
        }}

        /* ------------------------------------------------------------------ */
        /* Alternate Button Style (Light shading, dark border)                */
        /* ------------------------------------------------------------------ */
        /* Hide the marker's parent container completely */
        [data-testid="stElementContainer"]:has(.light-btn-marker),
        .element-container:has(.light-btn-marker) {{
            display: none !important;
            height: 0px !important;
            margin: 0px !important;
            padding: 0px !important;
        }}

        /* Apply the alternate style to ANY button inside a column block containing the marker */
        [data-testid="stHorizontalBlock"]:has(.light-btn-marker) button[kind="secondary"] {{
            background-color: {CLR_BTN_LIGHT_BG} !important;
            border: 1px solid {CLR_BTN_LIGHT_BORDER} !important;
            box-shadow: none !important;
        }}
        [data-testid="stHorizontalBlock"]:has(.light-btn-marker) button[kind="secondary"] * {{
            color: {CLR_BTN_LIGHT_TEXT} !important;
        }}
        [data-testid="stHorizontalBlock"]:has(.light-btn-marker) button[kind="secondary"]:hover {{
            background-color: #e2e6f0 !important;
            border-color: #555555 !important;
        }}

        /* ------------------------------------------------------------------ */
        /* Table controls (explorer tab)                                       */
        /* ------------------------------------------------------------------ */
        div[data-testid="stSelectbox"] label p,
        div[data-testid="stRadio"] label p {{
            font-size: {FS_LABEL}px !important;
        }}
        [data-testid="stHorizontalBlock"]:has([data-testid="stDownloadButton"]) {{
            border-bottom: none !important;
            margin-bottom: 0px !important;
        }}
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Viewer-tab compaction override
# ---------------------------------------------------------------------------

def apply_viewer_compaction_css():
    """
    Tightens select-box and label sizes for the denser Viewer tab layout.
    Called once at the top of render_viewer_tab().
    """
    st.markdown(f"""
    <style>
        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div {{
            min-height: 32px !important;
            padding-top: 2px !important;
            padding-bottom: 2px !important;
        }}
        input, div[data-baseweb="select"] {{ font-size: {FS_BODY}px !important; }}
        label p, label span           {{ font-size: {FS_BODY}px !important; }}

        /* Close the gap between sliders and the buttons below them */
        [data-testid="stSidebar"] [data-testid="stSlider"] {{
            padding-bottom: 0px !important;
            margin-bottom: -10px !important;
        }}
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:has(button) {{
            margin-top: -15px !important;
        }}
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Page chrome
# ---------------------------------------------------------------------------

def render_header():
    """Renders the top title bar and separator."""
    st.markdown(f"""
    <div style='text-align: center; margin-bottom: 10px;'>
        <h3 style='color: {CLR_PRIMARY}; margin: 0; padding: 0;
                   font-size: {FS_TITLE}px;'>
            HRDOBS Dataset Explorer & Visualizer
        </h3>
        <p style='font-size: {FS_SUBTITLE}px; color: {CLR_SUBTLE}; margin: 0;'>
            Search, filter, map, and analyze AI-ready tropical cyclone observations
        </p>
    </div>
    <hr style='margin-top: 5px; margin-bottom: 60px;'>
    """, unsafe_allow_html=True)


def render_footer():
    """Renders the copyright line at the bottom of every page."""
    st.markdown("---")
    st.markdown(
        f"<div style='text-align: center; color: {CLR_SUBTLE}; "
        f"font-size: {FS_FOOTER}px;'>"
        f"© {datetime.now().year} Altug Aksoy  |  "
        f"University of Miami / Rosenstiel School / Cooperative Institute for Marine and Atmospheric Studies</div>",
        unsafe_allow_html=True
    )
