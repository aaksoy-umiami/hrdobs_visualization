# -*- coding: utf-8 -*-

import streamlit as st
from datetime import datetime

def setup_page():
    """Initializes standard page layout and global CSS rules."""
    st.set_page_config(
        # Updated Browser Tab Title
        page_title="HRDOBS Dataset Explorer & Visualizer | Altug Aksoy",
        page_icon="🌪️",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Report a bug': "mailto:aaksoy@miami.edu",
            'About': """
            ### HRDOBS Dataset Explorer & Visualizer
            **Search, filter, and map AI-Ready tropical cyclone observations**
            
            This tool explores and visualizes the HRDOBS AI-Ready HDF5 database.
            
            **Author:** Altug Aksoy
            **Affiliation:** CIMAS/Rosenstiel School, University of Miami & NOAA/AOML/HRD
            """
        }
    )

    st.markdown("""
    <style>
        .block-container { padding-top: 3.5rem !important; padding-bottom: 1rem !important; }
        
        /* === TAB NAVIGATION STYLING === */
        div[data-testid="column"] button {
            width: 100%; border-radius: 8px; padding: 10px; font-weight: 600;
            font-size: 14px; transition: all 0.3s ease; border: 2px solid #000000 !important;
        }
        div[data-testid="column"] button[kind="secondary"] {
            background-color: rgba(255, 255, 255, 0.05); color: rgba(255, 255, 255, 0.7);
        }
        div[data-testid="column"] button[kind="primary"] {
            background: linear-gradient(135deg, #2b2b2b 0%, #000000 100%);
            color: white; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }
        div[data-testid="column"] button:hover {
            transform: translateY(-2px); box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4);
        }
        [data-testid="stHorizontalBlock"]:has(button[kind="primary"], button[kind="secondary"]) {
            border-bottom: 2px solid #000000; padding-bottom: 0px; margin-bottom: 0px;
        }
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
            border-bottom: none !important;
        }

        /* === MULTISELECT DROPDOWN CHIPS === */
        span[data-baseweb="tag"] { background-color: #555555 !important; color: #ffffff !important; font-size: 12px !important; }
        span[data-baseweb="tag"] svg { fill: #ffffff !important; }
        
        div[data-baseweb="select"], ul[role="listbox"] li, li[role="option"] { font-size: 13px !important; }
        
        /* === SIDEBAR STYLING === */
        [data-testid="stSidebar"] { display: block !important; min-width: 320px !important; }
        [data-testid="stSidebar"] label, [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { font-size: 16px !important; }
        [data-testid="stSidebar"] [data-testid="stTooltipIcon"] { margin-top: 4px; }
        
        [data-testid="stSidebar"] button[kind="primary"] {
            background-color: #ffffff !important; color: #000000 !important;
            border: 3px solid #000000 !important; font-weight: 600;
        }
        [data-testid="stSidebar"] button[kind="secondary"] {
            background-color: #555555 !important; color: white !important;
            border: 2px solid #555555 !important; padding: 0px 10px !important;
            min-height: 28px !important; height: 28px !important;
        }
        [data-testid="stSidebar"] button[kind="secondary"] * {
            font-size: 12px !important; font-weight: 600 !important; line-height: 1 !important; margin: 0 !important;
        }
    </style>
    """, unsafe_allow_html=True)

def render_header():
    """Renders the top title and standard separator."""
    st.markdown("""
    <div style='text-align: center; margin-bottom: 10px;'>
        <h3 style='color: #000000; margin: 0; padding: 0; font-size: 32px;'>🌪️ HRDOBS Dataset Explorer & Visualizer</h3>
        <p style='font-size: 14px; color: #666; margin: 0;'>
            Search, filter, and map AI-Ready tropical cyclone observations
        </p>
    </div>
    <hr style='margin-top: 5px; margin-bottom: 60px;'>
    """, unsafe_allow_html=True)

def render_footer():
    """Renders the standard copyright text at the bottom."""
    st.markdown("---")
    st.markdown(
        f"<div style='text-align: center; color: #666; font-size: 12px;'>"
        f"© {datetime.now().year} Altug Aksoy | University of Miami & NOAA/AOML</div>", 
        unsafe_allow_html=True
    )

def apply_viewer_compaction_css():
    """Compacts select boxes for the Viewer tab specifically."""
    st.markdown("""
        <style>
        div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
            min-height: 32px !important; padding-top: 2px !important; padding-bottom: 2px !important;
        }
        input, div[data-baseweb="select"] { font-size: 13px !important; }
        label p, label span { font-size: 13px !important; }
        
        /* ---> NEW: Tame the Streamlit Flexbox gap between sliders and buttons <--- */
        [data-testid="stSidebar"] [data-testid="stSlider"] {
            padding-bottom: 0px !important;
            margin-bottom: -10px !important;
        }
        [data-testid="stSidebar"] [data-testid="stHorizontalBlock"]:has(button) {
            margin-top: -15px !important;
        }
        </style>
    """, unsafe_allow_html=True)
