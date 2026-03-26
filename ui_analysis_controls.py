# -*- coding: utf-8 -*-
"""
ui_analysis_controls.py
-----------------------
Sidebar widget logic for the Statistical Analysis tab.
"""

import streamlit as st
from dataclasses import dataclass, field
from typing import Optional, Dict

from ui_viewer_file import render_file_upload_section
from config import DEFAULT_HIST_BINS, AVAILABLE_COLORSCALES, GLOBAL_VAR_CONFIG, COLORSCALE_NAMES
from ui_components import sidebar_label, section_divider, init_state, sync_namespace
from plotter import StormPlotter

@dataclass
class AnalysisIntent:
    data_pack: Optional[Dict] = None
    analysis_type: str = "Histogram Analysis (1D)"
    sel_group: Optional[str] = None
    variable: Optional[str] = None
    coord_var: Optional[str] = None
    hist_bins_x: Optional[int] = None
    hist_bins_y: Optional[int] = None
    normalization: str = "None"
    reverse_axes: bool = False
    render_as_line: bool = False
    scatter_trendline: bool = False
    scatter_color_var: Optional[str] = None
    scatter_marker_size: int = 100
    log_var: bool = False
    log_coord_var: bool = False
    custom_colorscale: Optional[str] = None

_ANALYSIS_STATE_KEYS = [
    'a_sel_group', 'a_variable', 'a_coord_var', 'a_analysis_type', 
    'a_bin_mode_x', 'a_bin_manual_x', 'a_bin_mode_y', 'a_bin_manual_y', 
    'a_hist_norm', 'a_reverse_axes', 'a_render_as_line', 'a_scatter_trendline',
    'a_scatter_color', 'a_scatter_color_var', 'a_scatter_marker_size',
    'a_scale_var', 'a_scale_coord_var', 'a_custom_colorscale'
]

def _render_analysis_variable_section(data_pack, plotter, analysis_type):
    available_groups = sorted(list(data_pack['data'].keys()))
    
    init_state('a_sel_group', available_groups[0] if available_groups else None)
    if st.session_state.a_sel_group not in available_groups:
        st.session_state.a_sel_group = available_groups[0] if available_groups else None

    def reset_a_var_dependencies():
        if 'a_custom_colorscale' in st.session_state:
            del st.session_state['a_custom_colorscale']

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
            is_2d_hist = (analysis_type == "Histogram Analysis (2D)")

            label_1 = "First Variable" if is_scatter else ("Primary Variable" if is_2d_hist else "Variable")
            label_2 = "Second Variable" if is_scatter else ("Secondary Variable" if is_2d_hist else "Coordinate Variable")

            ordered = []
            base_vars  = plotter.get_plottable_variables(sel_group)
            coord_vars = plotter.get_coordinate_variables(sel_group)
            extra_coords = [c for c in coord_vars if c not in base_vars]
            if base_vars and extra_coords:
                ordered = base_vars[:-1] + extra_coords + base_vars[-1:]
            else:
                ordered = base_vars + extra_coords
                
            list_1 = ordered
            list_2 = ordered if (is_scatter or is_2d_hist) else plotter.get_coordinate_variables(sel_group)

            if list_1:
                init_state('a_variable', list_1[0])
                if st.session_state.a_variable not in list_1:
                    st.session_state.a_variable = list_1[0]

                v1_col1, v1_col2 = st.columns([1.6, 1])
                with v1_col1:
                    variable = st.selectbox(label_1, list_1, key='a_variable', on_change=reset_a_var_dependencies, format_func=lambda x: plotter._get_var_display_name(sel_group, x))
                with v1_col2:
                    init_state('a_scale_var', "Linear scale")
                    st.selectbox("Scale:", ["Linear scale", "Log scale"], key='a_scale_var', label_visibility="collapsed")
            else:
                st.warning("No valid variables found.")

            if list_2:
                init_state('a_coord_var', list_2[0])
                if st.session_state.a_coord_var not in list_2:
                    st.session_state.a_coord_var = list_2[0]

                v2_col1, v2_col2 = st.columns([1.6, 1])
                with v2_col1:
                    coord_var = st.selectbox(label_2, list_2, key='a_coord_var', format_func=lambda x: plotter._get_var_display_name(sel_group, x), disabled=(analysis_type == "Histogram Analysis (1D)"))
                with v2_col2:
                    init_state('a_scale_coord_var', "Linear scale")
                    st.selectbox("Scale:", ["Linear scale", "Log scale"], key='a_scale_coord_var', disabled=(analysis_type == "Histogram Analysis (1D)"), label_visibility="collapsed")
            else:
                st.warning("No valid secondary variables found for this group.")

    _ordered = ordered if (is_scatter or is_2d_hist) else []
    return sel_group, variable, coord_var, _ordered


def render_analysis_controls() -> AnalysisIntent:
    intent = AnalysisIntent()
    init_state('analysis_state', {})

    data_pack = render_file_upload_section(
        data_pack_key='data_pack_analysis', filename_key='last_uploaded_filename_analysis',
        state_keys=_ANALYSIS_STATE_KEYS, state_dict_key='analysis_state'
    )

    intent.data_pack = data_pack
    if data_pack is None: return intent

    from plotter import StormPlotter
    plotter = StormPlotter(data_pack['data'], data_pack['track'], data_pack['meta'], data_pack['var_attrs'])

    with st.sidebar.container(border=True):
        st.markdown("### ⚙️ Analysis Type")
        init_state('a_analysis_type', "Histogram Analysis (1D)")
        analysis_type = st.selectbox("Select Analysis Mode", ["Histogram Analysis (1D)", "Histogram Analysis (2D)", "Scatter Analysis"], key='a_analysis_type')
        intent.analysis_type = analysis_type
        
    sel_group, variable, coord_var, scatter_var_list = _render_analysis_variable_section(data_pack, plotter, analysis_type)
    intent.sel_group = sel_group
    intent.variable = variable
    intent.coord_var = coord_var
        
    with st.sidebar.container(border=True):
        st.markdown("### ⚙️ Plotting Options")
        
        is_1d_hist = (intent.analysis_type == "Histogram Analysis (1D)")
        is_2d = (intent.analysis_type == "Histogram Analysis (2D)")
        is_scatter = (intent.analysis_type == "Scatter Analysis")
        
        color_var_for_default = intent.variable
        if is_scatter and st.session_state.get('a_scatter_color') == "Variable:":
            color_var_for_default = st.session_state.get('a_scatter_color_var', intent.variable)
        
        default_cmap = GLOBAL_VAR_CONFIG.get(color_var_for_default.lower() if color_var_for_default else "", {}).get('colorscale', 'Viridis')
        cmaps = sorted(list(set(AVAILABLE_COLORSCALES + [default_cmap])))
        init_state('a_custom_colorscale', default_cmap)
        
        c_cs1, c_cs2 = st.columns([1.4, 1.8])
        with c_cs1:
            sidebar_label("Colorscale:", size='label', enabled=not is_1d_hist)
        with c_cs2:
            custom_colorscale = st.selectbox(
                "Colorscale", cmaps, 
                key='a_custom_colorscale', label_visibility="collapsed", disabled=is_1d_hist,
                format_func=lambda x: COLORSCALE_NAMES.get(x, x)
            )
        intent.custom_colorscale = custom_colorscale
        
        section_divider()

        st.markdown("#### Histogram Controls")

        c1, c2, c3 = st.columns([1.4, 1.0, 0.8])
        with c1: sidebar_label("Num. of Intervals (X):", size='label', enabled=not is_scatter)
        with c2:
            init_state('a_bin_mode_x', "Default")
            bin_mode_x = st.selectbox("X Intervals Option", ["Default", "Manual:"], key='a_bin_mode_x', label_visibility="collapsed", disabled=is_scatter)
        with c3:
            if bin_mode_x == "Default" or is_scatter:
                st.number_input("Bins Dummy X", value=DEFAULT_HIST_BINS, disabled=True, key='dummy_bin_x', label_visibility="collapsed")
                intent.hist_bins_x = DEFAULT_HIST_BINS if not is_scatter else None
            else:
                init_state('a_bin_manual_x', DEFAULT_HIST_BINS)
                intent.hist_bins_x = st.number_input("Bins X", min_value=1, max_value=1000, step=1, key='a_bin_manual_x', label_visibility="collapsed", disabled=is_scatter)

        c4, c5, c6 = st.columns([1.4, 1.0, 0.8])
        with c4: sidebar_label("Num. of Intervals (Y):", size='label', enabled=is_2d)
        with c5:
            init_state('a_bin_mode_y', "Default")
            bin_mode_y = st.selectbox("Y Intervals Option", ["Default", "Manual:"], key='a_bin_mode_y', label_visibility="collapsed", disabled=not is_2d)
        with c6:
            if bin_mode_y == "Default" or not is_2d:
                st.number_input("Bins Dummy Y", value=DEFAULT_HIST_BINS, disabled=True, key='dummy_bin_y', label_visibility="collapsed")
                intent.hist_bins_y = DEFAULT_HIST_BINS if is_2d else None
            else:
                init_state('a_bin_manual_y', DEFAULT_HIST_BINS)
                intent.hist_bins_y = st.number_input("Bins Y", min_value=1, max_value=1000, step=1, key='a_bin_manual_y', label_visibility="collapsed", disabled=not is_2d)

        c7, c8 = st.columns([1.4, 1.8])
        with c7: sidebar_label("Normalization:", size='label', enabled=not is_scatter)
        with c8:
            init_state('a_hist_norm', "None")
            norm_opts = ["None", "Normalize within each Primary bin", "Normalize within each Secondary bin", "Normalize Fully"] if is_2d else ["None", "Normalize Fully"]
            if st.session_state.a_hist_norm not in norm_opts: st.session_state.a_hist_norm = "None"
            norm_val = st.selectbox("Normalization Option", norm_opts, key='a_hist_norm', label_visibility="collapsed", disabled=is_scatter)
            intent.normalization = norm_val if not is_scatter else "None"
                
        init_state('a_reverse_axes', False)
        st.checkbox("Reverse X and Y axes", key="a_reverse_axes")
        intent.reverse_axes = st.session_state.a_reverse_axes

        init_state('a_render_as_line', False)
        if not is_1d_hist and st.session_state.a_render_as_line: st.session_state.a_render_as_line = False
        st.checkbox("Render as line plot", key="a_render_as_line", disabled=not is_1d_hist)
        intent.render_as_line = st.session_state.a_render_as_line if is_1d_hist else False
                
        section_divider()
        st.markdown("#### Scatter Controls")
        
        st.checkbox("Show Trendline", value=False, key="a_scatter_trendline", disabled=not is_scatter)

        color_opts = ["None", "Variable:"]
        init_state('a_scatter_color', "None")
        if st.session_state.a_scatter_color not in color_opts: st.session_state.a_scatter_color = "None"
        scatter_color_mode = st.selectbox("Color By", color_opts, key="a_scatter_color", disabled=not is_scatter)

        color_by_var = (is_scatter and scatter_color_mode == "Variable:")
        
        def reset_scatter_color_dep():
            if 'a_custom_colorscale' in st.session_state:
                del st.session_state['a_custom_colorscale']
                
        if scatter_var_list:
            init_state('a_scatter_color_var', scatter_var_list[0])
            if st.session_state.a_scatter_color_var not in scatter_var_list: st.session_state.a_scatter_color_var = scatter_var_list[0]
            st.selectbox("Color Variable", scatter_var_list, key="a_scatter_color_var", on_change=reset_scatter_color_dep, format_func=lambda x: plotter._get_var_display_name(intent.sel_group or "", x), disabled=not color_by_var, label_visibility="collapsed")

        sidebar_label("Marker Size:", size='label', enabled=is_scatter)
        init_state('a_scatter_marker_size', 100)
        st.slider("Scatter Marker Size", min_value=10, max_value=200, step=10, format="%d%%", key="a_scatter_marker_size", disabled=not is_scatter, label_visibility="collapsed")

        intent.scatter_trendline  = st.session_state.get('a_scatter_trendline', False) if is_scatter else False
        intent.scatter_color_var  = st.session_state.get('a_scatter_color_var') if color_by_var else None
        intent.scatter_marker_size = st.session_state.get('a_scatter_marker_size', 100) if is_scatter else 100

    intent.log_var       = (st.session_state.get('a_scale_var', 'Linear scale') == 'Log scale')
    intent.log_coord_var = (st.session_state.get('a_scale_coord_var', 'Linear scale') == 'Log scale')

    sync_namespace('a_', 'analysis_state')
    return intent
