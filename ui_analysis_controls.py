# -*- coding: utf-8 -*-
"""
ui_analysis_controls.py
-----------------------
Sidebar widget logic for the Statistical Analysis tab.
"""

import streamlit as st
from dataclasses import dataclass, field
from typing import Optional, Dict

from ui_viewer_controls import render_file_upload_section
from config import DEFAULT_HIST_BINS
from ui_components import sidebar_label, section_divider

@dataclass
class AnalysisIntent:
    data_pack: Optional[Dict] = None
    analysis_type: str = "Histogram Analysis (1D)"
    sel_group: Optional[str] = None
    variable: Optional[str] = None
    coord_var: Optional[str] = None
    hist_bins_x: Optional[int] = None
    hist_bins_y: Optional[int] = None
    normalization: str = "None"  # <--- Added
    reverse_axes: bool = False

# Updated state keys for normalization
_ANALYSIS_STATE_KEYS = [
    'a_sel_group', 'a_variable', 'a_coord_var', 'a_analysis_type', 
    'a_bin_mode_x', 'a_bin_manual_x', 'a_bin_mode_y', 'a_bin_manual_y', 
    'a_hist_norm', 'a_reverse_axes', 'a_scatter_trendline', 'a_scatter_color'
]

def _render_analysis_variable_section(data_pack, plotter, analysis_type):
    """A streamlined version of the variable selector specifically for 1D/2D analysis."""
    available_groups = sorted(list(data_pack['data'].keys()))
    
    if ('a_sel_group' not in st.session_state or
            st.session_state.a_sel_group not in available_groups):
        st.session_state.a_sel_group = available_groups[0] if available_groups else None

    with st.sidebar.container(border=True):
        st.markdown("### 📈 Plot Variable")
        sel_group = st.selectbox(
            "Select Active Group to Plot", available_groups,
            key='a_sel_group'
        )

        variable = None
        coord_var = None
        
        if 'TRACK' in sel_group.upper():
            st.info("Statistical analysis not available for flight tracks.")
        else:
            is_scatter = (analysis_type == "Scatter Analysis")
            is_2d = (analysis_type == "Histogram Analysis (2D)")
            label_1 = "First Variable"
            label_2 = "Second Variable"

            if is_scatter:
                base_vars = plotter.get_plottable_variables(sel_group)
                coord_vars = plotter.get_coordinate_variables(sel_group)
                # Preserve tiered order from get_plottable_variables; append any
                # coord-only entries that aren't already in the list
                seen = set(base_vars)
                extra = [c for c in coord_vars if c not in seen]
                list_1 = base_vars + extra
                list_2 = list_1
            elif is_2d:
                list_1 = plotter.get_plottable_variables(sel_group, exclude_vectors=True)
                list_2 = list_1
            else:
                list_1 = plotter.get_plottable_variables(sel_group, exclude_vectors=True)
                list_2 = plotter.get_coordinate_variables(sel_group)

            if list_1:
                if ('a_variable' not in st.session_state or
                        st.session_state.a_variable not in list_1):
                    st.session_state.a_variable = list_1[0]

                variable = st.selectbox(
                    label_1, list_1,
                    key='a_variable',
                    format_func=lambda x: plotter._get_var_display_name(sel_group, x)
                )
            else:
                st.warning("No valid variables found.")

            if list_2:
                if ('a_coord_var' not in st.session_state or
                        st.session_state.a_coord_var not in list_2):
                    if (is_scatter or is_2d) and len(list_2) > 1:
                        st.session_state.a_coord_var = list_2[1]
                    else:
                        st.session_state.a_coord_var = list_2[0]

                coord_var = st.selectbox(
                    label_2, list_2,
                    key='a_coord_var',
                    format_func=lambda x: plotter._get_var_display_name(sel_group, x),
                    disabled=(analysis_type == "Histogram Analysis (1D)")
                )
            else:
                st.warning("No valid secondary variables found for this group.")

    return sel_group, variable, coord_var


def render_analysis_controls(plotter) -> AnalysisIntent:
    intent = AnalysisIntent()
    
    if 'analysis_state' not in st.session_state:
        st.session_state.analysis_state = {}

    data_pack = render_file_upload_section(
        data_pack_key='data_pack_analysis',
        filename_key='last_uploaded_filename_analysis',
        state_keys=_ANALYSIS_STATE_KEYS,
        state_dict_key='analysis_state'
    )

    intent.data_pack = data_pack
    if data_pack is None or plotter is None:
        return intent

    with st.sidebar.container(border=True):
        st.markdown("### ⚙️ Analysis Type")
        if 'a_analysis_type' not in st.session_state:
            st.session_state.a_analysis_type = "Histogram Analysis (1D)"
            
        analysis_type = st.selectbox(
            "Select Analysis Mode", 
            ["Histogram Analysis (1D)", "Histogram Analysis (2D)", "Scatter Analysis"],
            key='a_analysis_type'
        )
        intent.analysis_type = analysis_type
        
    sel_group, variable, coord_var = _render_analysis_variable_section(data_pack, plotter, analysis_type)
    intent.sel_group = sel_group
    intent.variable = variable
    intent.coord_var = coord_var
        
    with st.sidebar.container(border=True):
        st.markdown("### ⚙️ Plotting Options")
        
        is_hist = "Histogram" in intent.analysis_type
        is_2d = (intent.analysis_type == "Histogram Analysis (2D)")
        is_scatter = (intent.analysis_type == "Scatter Analysis")

        # -------------------------------------------------------------
        # HISTOGRAM CONTROLS
        # -------------------------------------------------------------
        st.markdown("#### Histogram Controls")

        c1, c2, c3 = st.columns([1.4, 1.0, 0.8])
        with c1:
            sidebar_label("Num. of Intervals (X):", size='label', enabled=is_hist)
        with c2:
            if 'a_bin_mode_x' not in st.session_state: st.session_state.a_bin_mode_x = "Default"
            bin_mode_x = st.selectbox("X Intervals Option", ["Default", "Manual:"], key='a_bin_mode_x', label_visibility="collapsed", disabled=not is_hist)
        with c3:
            if bin_mode_x == "Default" or not is_hist:
                st.number_input("Bins Dummy X", value=DEFAULT_HIST_BINS, disabled=True, key='dummy_bin_x', label_visibility="collapsed")
                intent.hist_bins_x = DEFAULT_HIST_BINS if is_hist else None
            else:
                if 'a_bin_manual_x' not in st.session_state: st.session_state.a_bin_manual_x = DEFAULT_HIST_BINS
                intent.hist_bins_x = st.number_input("Bins X", min_value=1, max_value=1000, step=1, key='a_bin_manual_x', label_visibility="collapsed", disabled=not is_hist)

        c4, c5, c6 = st.columns([1.4, 1.0, 0.8])
        with c4:
            sidebar_label("Num. of Intervals (Y):", size='label', enabled=is_2d)
        with c5:
            if 'a_bin_mode_y' not in st.session_state: st.session_state.a_bin_mode_y = "Default"
            bin_mode_y = st.selectbox("Y Intervals Option", ["Default", "Manual:"], key='a_bin_mode_y', label_visibility="collapsed", disabled=not is_2d)
        with c6:
            if bin_mode_y == "Default" or not is_2d:
                st.number_input("Bins Dummy Y", value=DEFAULT_HIST_BINS, disabled=True, key='dummy_bin_y', label_visibility="collapsed")
                intent.hist_bins_y = DEFAULT_HIST_BINS if is_2d else None
            else:
                if 'a_bin_manual_y' not in st.session_state: st.session_state.a_bin_manual_y = DEFAULT_HIST_BINS
                intent.hist_bins_y = st.number_input("Bins Y", min_value=1, max_value=1000, step=1, key='a_bin_manual_y', label_visibility="collapsed", disabled=not is_2d)

        # ---> NEW: Normalization Control
        c7, c8 = st.columns([0.9, 2.3])
        with c7:
            sidebar_label("Normalization:", size='label', enabled=is_hist)
        with c8:
            if 'a_hist_norm' not in st.session_state:
                st.session_state.a_hist_norm = "None"
                
            norm_opts = ["None", "Row Normalization (fix Y, sum X to 100%)", "Column Normalization (fix X, sum Y to 100%)", "Full Normalization (all bins sum to 100%)"] if is_2d else ["None", "Full Normalization (all bins sum to 100%)"]
            
            if st.session_state.a_hist_norm not in norm_opts:
                st.session_state.a_hist_norm = "None"
                
            norm_val = st.selectbox(
                "Normalization Option", norm_opts, 
                key='a_hist_norm', label_visibility="collapsed", disabled=not is_hist
            )
            intent.normalization = norm_val if is_hist else "None"
        # <---

        # -------------------------------------------------------------
        # COMMON CONTROLS
        # -------------------------------------------------------------
        section_divider()
        st.markdown("#### Common Controls")

        if 'a_reverse_axes' not in st.session_state: st.session_state.a_reverse_axes = False
        if not is_2d and not is_scatter and st.session_state.a_reverse_axes: st.session_state.a_reverse_axes = False
        st.checkbox("Reverse X and Y axes", key="a_reverse_axes", disabled=not (is_2d or is_scatter))
        intent.reverse_axes = st.session_state.a_reverse_axes if (is_2d or is_scatter) else False

        # -------------------------------------------------------------
        # SCATTER CONTROLS
        # -------------------------------------------------------------
        section_divider()
        st.markdown("#### Scatter Controls")
        
        if 'a_scatter_trendline' not in st.session_state: st.session_state.a_scatter_trendline = False
        st.checkbox("Show Trendline", key="a_scatter_trendline", disabled=not is_scatter)
        
        if 'a_scatter_color' not in st.session_state: st.session_state.a_scatter_color = "Density"
        st.selectbox("Color Mapping", ["Density", "Z-Coordinate", "Variable"], key="a_scatter_color", disabled=not is_scatter)


    for k in list(st.session_state.keys()):
        if k.startswith('a_'):
            st.session_state.analysis_state[k] = st.session_state[k]

    return intent
