# -*- coding: utf-8 -*-

import streamlit as st
from ui_layout import setup_page, render_header, render_footer
from ui_viewer import render_viewer_tab
from ui_explorer import render_explorer_tab

# Initialize Page Settings and Styles
setup_page()
render_header()

# Handle Tab State
if 'selected_tab_index' not in st.session_state:
    st.session_state.selected_tab_index = 0

tab_col_space1, tab_col1, tab_col2, tab_col_space2 = st.columns([0.05, 1, 1, 0.05])

with tab_col1:
    if st.button("📊 File Data Viewer", type="primary" if st.session_state.selected_tab_index == 0 else "secondary", use_container_width=True):
        st.session_state.selected_tab_index = 0
        st.rerun()

with tab_col2:
    if st.button("🌍 Global Dataset Explorer", type="primary" if st.session_state.selected_tab_index == 1 else "secondary", use_container_width=True):
        st.session_state.selected_tab_index = 1
        st.rerun()

# Route to the appropriate tab module
if st.session_state.selected_tab_index == 0:
    render_viewer_tab()
elif st.session_state.selected_tab_index == 1:
    render_explorer_tab()

render_footer()
