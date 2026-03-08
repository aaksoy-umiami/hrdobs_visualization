# -*- coding: utf-8 -*-
"""
ui_analysis.py
--------------
Main layout and rendering logic for the Statistical Analysis tab.
"""

import streamlit as st
from ui_layout import apply_viewer_compaction_css
from ui_analysis_controls import render_analysis_controls
from plotter import StormPlotter

def render_analysis_tab():
    apply_viewer_compaction_css()
    
    # ---> NEW: Restore a_ keys from the persistence dict on tab load
    if 'analysis_state' not in st.session_state:
        st.session_state.analysis_state = {}
    for k, v in st.session_state.analysis_state.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # <---
    
    # Render sidebar controls — plotter is built inside render_analysis_controls
    # after data_pack is resolved (including auto-inherit from Tab 2's session key).
    intent = render_analysis_controls()
    
    if not intent.data_pack:
        st.info("👈 Please upload an AI-Ready HDF5 file in the sidebar to begin analysis.")
        return

    data_pack = intent.data_pack
    plotter = StormPlotter(
        data_pack['data'], data_pack['track'],
        data_pack['meta'], data_pack['var_attrs']
    )
    
    if intent.sel_group and 'TRACK' in intent.sel_group.upper():
        return
        
    if intent.variable:
        if intent.analysis_type == "Histogram Analysis (1D)":
            fig = plotter.plot_histogram(
                intent.sel_group, 
                intent.variable, 
                nbins=intent.hist_bins_x,
                normalization=intent.normalization,
                reverse_axes=intent.reverse_axes,
                render_as_line=intent.render_as_line
            )
            
            if fig:
                col_left, col_center, col_right = st.columns([1, 8, 1])
                with col_center:
                    st.plotly_chart(fig, use_container_width=False)
            else:
                st.warning("Could not generate 1D histogram for this variable.")
                
        elif intent.analysis_type == "Histogram Analysis (2D)":
            if intent.coord_var:
                fig = plotter.plot_histogram_2d(
                    intent.sel_group, 
                    intent.variable, 
                    intent.coord_var, 
                    nbinsx=intent.hist_bins_x,
                    nbinsy=intent.hist_bins_y,
                    reverse_axes=intent.reverse_axes,
                    normalization=intent.normalization  # <--- Added
                )
                
                if fig:
                    col_left, col_center, col_right = st.columns([1, 8, 1])
                    with col_center:
                        st.plotly_chart(fig, use_container_width=False)
                else:
                    st.warning("Could not generate 2D histogram for these variables.")
            else:
                st.warning("No coordinate variable available to plot.")
            
    if intent.analysis_type == "Scatter Analysis":
        st.info("Scatter Analysis coming soon...")
