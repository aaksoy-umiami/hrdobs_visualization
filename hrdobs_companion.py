# -*- coding: utf-8 -*-
"""
hrdobs_companion.py
--------------
App entry point: configures the page, detects viewport width, and routes between the four main tabs.
"""

import streamlit as st
from ui_layout import setup_page, render_header, render_footer
from ui_viewer import render_viewer_tab
from ui_explorer import render_explorer_tab
from ui_analysis import render_analysis_tab
from ui_info import render_info_tab
try:
    from streamlit_js_eval import streamlit_js_eval
    _JS_EVAL_AVAILABLE = True
except ImportError:
    _JS_EVAL_AVAILABLE = False

# Initialize Page Settings and Styles
setup_page()
render_header()

# === VIEWPORT WIDTH DETECTION ===
if _JS_EVAL_AVAILABLE and 'viewport_width' not in st.session_state:
    try:
        vw = streamlit_js_eval(
            js_expressions="window.innerWidth",
            key="viewport_width_js",
            want_output=True,
        )
        if vw is not None:
            st.session_state.viewport_width = vw
    except Exception:
        st.session_state.viewport_width = None

def _is_mobile():
    vw = st.session_state.get("viewport_width", None)
    if vw is None:
        return False
    return vw < 768

# === MOBILE WARNING (one-time dialog) ===
@st.dialog("📱 Mobile Device Detected")
def _show_mobile_warning():
    st.write("This app involves complex interactive visualizations that are best experienced on a **Desktop or Laptop**.")
    st.write("You may encounter layout issues or reduced performance on smaller screens.")
    if st.button("I Understand"):
        st.session_state.mobile_warning_acknowledged = True
        st.rerun()

if _is_mobile() and 'mobile_warning_acknowledged' not in st.session_state:
    _show_mobile_warning()

# Handle Tab State
if 'selected_tab_index' not in st.session_state:
    st.session_state.selected_tab_index = 0

# Updated layout for 4 columns
tab_col_space1, tab_col1, tab_col2, tab_col3, tab_col4, tab_col_space2 = st.columns([0.05, 1, 1, 1, 0.6, 0.05])

with tab_col1:
    if st.button("🌍 Dataset Explorer", type="primary" if st.session_state.selected_tab_index == 0 else "secondary", width="stretch"):
        st.session_state.selected_tab_index = 0
        st.rerun()

with tab_col2:
    if st.button("📊 Individual File Plotter", type="primary" if st.session_state.selected_tab_index == 1 else "secondary", width="stretch"):
        st.session_state.selected_tab_index = 1
        st.rerun()

with tab_col3:
    if st.button("📈 Individual File Statistical Analysis", type="primary" if st.session_state.selected_tab_index == 2 else "secondary", width="stretch"):
        st.session_state.selected_tab_index = 2
        st.rerun()

with tab_col4:
    if st.button("ℹ️ Info", type="primary" if st.session_state.selected_tab_index == 3 else "secondary", width="stretch"):
        st.session_state.selected_tab_index = 3
        st.rerun()

# Route to the appropriate tab module based on the new indices
if st.session_state.selected_tab_index == 0:
    render_explorer_tab()
elif st.session_state.selected_tab_index == 1:
    render_viewer_tab()
elif st.session_state.selected_tab_index == 2:
    render_analysis_tab()
elif st.session_state.selected_tab_index == 3:
    render_info_tab()

render_footer()
