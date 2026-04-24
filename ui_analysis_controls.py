# -*- coding: utf-8 -*-
"""
ui_analysis_controls.py
-----------------------
Sidebar widget logic for the Statistical Analysis tab.
"""

import re
import pandas as pd
import streamlit as st
from dataclasses import dataclass, field
from typing import Optional, Dict

from ui_viewer_file import render_file_upload_section
from config import DEFAULT_HIST_BINS, DEFAULT_HIST_BINS_AZIMUTH, DEFAULT_HIST_BINS_RADIAL, AVAILABLE_COLORSCALES, GLOBAL_VAR_CONFIG, COLORSCALE_NAMES
from ui_components import sidebar_label, section_divider, init_state, sync_namespace
from plotter import StormPlotter
from ui_layout import FS_BODY

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
    show_kde: bool = False
    show_marginals: bool = False
    scatter_color_var: Optional[str] = None
    scatter_marker_size: int = 100
    log_var: bool = False
    log_coord_var: bool = False
    custom_colorscale: Optional[str] = None
    coordinate_system: str = "Cartesian"
    map_option: str = "None"

_ANALYSIS_STATE_KEYS = [
    'a_sel_group', 'a_variable', 'a_coord_var', 'a_analysis_type', 
    'a_hist_norm', 'a_reverse_axes', 'a_render_as_line', 'a_show_kde', 'a_show_marginals',
    'a_scatter_color', 'a_scatter_color_var', 'a_scatter_marker_size',
    'a_scale_var', 'a_scale_coord_var', 'a_custom_colorscale', 'a_coord_sys', 'a_map_option', 'a_rev_cmap'
]

def _render_analysis_variable_section(data_pack, plotter, analysis_type):
    # --- Filter out scalar SHIPS parameters from analyzable groups ---
    available_groups = sorted([
        g for g in data_pack['data'].keys() 
        if g.lower() != 'ships_params' and 'track' not in g.lower()
    ])
    
    init_state('a_sel_group', available_groups[0] if available_groups else None)
    if st.session_state.a_sel_group not in available_groups:
        st.session_state.a_sel_group = available_groups[0] if available_groups else None

    def reset_a_var_dependencies():
        if 'a_custom_colorscale' in st.session_state:
            del st.session_state['a_custom_colorscale']
        if 'a_rev_cmap' in st.session_state:
            del st.session_state['a_rev_cmap']

    with st.sidebar.container(border=True):
        st.markdown("### 📈 Plot Variable")
        sel_group = st.selectbox(
            "Select Aircraft/Platform to Plot", available_groups,
            key='a_sel_group'
        )

        variable = None
        coord_var = None
        scatter_color_var = None
        scatter_marker_size = 100
        reverse_axes = False
        ordered = []
        
        is_scatter = (analysis_type == "Scatter Analysis")
        is_1d_hist = (analysis_type == "Histogram Analysis (1D)")
        is_2d_hist = (analysis_type == "Histogram Analysis (2D)")

        label_1 = "First Variable" if is_scatter else ("Primary Variable" if is_2d_hist else "Variable")
        label_2 = "Second Variable" if is_scatter else ("Secondary Variable" if is_2d_hist else "Variable (not active for 1D plots)")

        base_vars  = plotter.get_plottable_variables(sel_group, exclude_vectors=True)
        coord_vars = plotter.get_coordinate_variables(sel_group)
        extra_coords = [c for c in coord_vars if c not in base_vars]
        
        combined_vars = base_vars + extra_coords
        
        # =================================================================
        # STRICT AZIMUTH VALIDATION (Checks for BOTH Speed and Direction)
        # =================================================================
        valid_azimuths = ['azimuth_north']
        
        # 1. Storm Motion (Extract numbers to verify vector completeness)
        sm_raw = data_pack.get('meta', {}).get('info', {}).get('storm_motion')
        if sm_raw is not None:
            nums = re.findall(r'[-+]?\d*\.?\d+', str(sm_raw))
            if len(nums) >= 2:  # Must have at least two numerical values
                valid_azimuths.append('azimuth_motion')
                
        # 2. SHIPS Shear Vectors
        if 'ships_params' in data_pack.get('data', {}):
            ships_df = data_pack['data']['ships_params']
            # Deep Layer
            if 'shrd_kt' in ships_df.columns and 'shtd_deg' in ships_df.columns:
                if pd.notna(ships_df['shrd_kt'].iloc[0]) and pd.notna(ships_df['shtd_deg'].iloc[0]):
                    valid_azimuths.append('azimuth_shear_deep')
            # Vortex Removed
            if 'shdc_kt' in ships_df.columns and 'sddc_deg' in ships_df.columns:
                if pd.notna(ships_df['shdc_kt'].iloc[0]) and pd.notna(ships_df['sddc_deg'].iloc[0]):
                    valid_azimuths.append('azimuth_shear_vortex')

        # --- THE FIX: Force inject valid azimuths so the UI sees them ---
        for az in valid_azimuths:
            if az not in combined_vars:
                combined_vars.append(az)
        # ----------------------------------------------------------------

        # NOW sort them, after we've guaranteed the valid azimuths are inside
        ordered_raw   = plotter.sort_variables(combined_vars, sel_group)

        # Filter the ordered lists so invalid azimuths NEVER appear in the dropdowns
        ordered = [v for v in ordered_raw if not (v.lower().startswith('azimuth_') and v.lower() not in valid_azimuths)]
        
        list_1 = ordered
        if (is_scatter or is_2d_hist):
            list_2 = ordered
        else:
            coord_list_raw = plotter.get_coordinate_variables(sel_group)
            list_2 = [v for v in coord_list_raw if not (v.lower().startswith('azimuth_') and v.lower() not in valid_azimuths)]
        # =================================================================

        v1_state = st.session_state.get('a_variable', list_1[0] if list_1 else "")
        v2_state = st.session_state.get('a_coord_var', list_2[0] if list_2 else "")
        v1_lower = v1_state.lower() if v1_state else ""
        v2_lower = v2_state.lower() if v2_state else ""
        
        # Dynamically check if any selected variable is an azimuth
        has_az   = any(v.startswith("azimuth_") for v in [v1_lower, v2_lower])
        has_dist = "dist_from_center" in [v1_lower, v2_lower]
        is_polar_eligible = has_az and has_dist and not is_1d_hist
        is_polar = is_polar_eligible and st.session_state.get('a_coord_sys') == "Polar"

        if list_1:
            init_state('a_variable', list_1[0])
            if st.session_state.a_variable not in list_1:
                st.session_state.a_variable = list_1[0]

            v1_col1, v1_col2 = st.columns([1.6, 1])
            with v1_col1:
                variable = st.selectbox(label_1, list_1, key='a_variable', on_change=reset_a_var_dependencies, format_func=lambda x: plotter._get_var_display_name(sel_group, x))
            with v1_col2:
                init_state('a_scale_var', "Linear scale")
                if is_polar and st.session_state.a_scale_var != "Linear scale":
                    st.session_state.a_scale_var = "Linear scale"
                st.selectbox("Plot on:", ["Linear scale", "Log scale"], key='a_scale_var', disabled=is_polar)
        else:
            st.warning("No valid variables found.")

        if list_2:
            init_state('a_coord_var', list_2[0])
            if st.session_state.a_coord_var not in list_2:
                st.session_state.a_coord_var = list_2[0]

            v2_col1, v2_col2 = st.columns([1.6, 1])
            with v2_col1:
                coord_var = st.selectbox(label_2, list_2, key='a_coord_var', format_func=lambda x: plotter._get_var_display_name(sel_group, x), disabled=is_1d_hist)
            with v2_col2:
                init_state('a_scale_coord_var', "Linear scale")
                if is_polar and st.session_state.a_scale_coord_var != "Linear scale":
                    st.session_state.a_scale_coord_var = "Linear scale"
                st.selectbox("Plot on:", ["Linear scale", "Log scale"], key='a_scale_coord_var', disabled=(is_1d_hist or is_polar))
            
            init_state('a_reverse_axes', False)
            if is_polar and st.session_state.a_reverse_axes:
                st.session_state.a_reverse_axes = False
            st.checkbox("Reverse X and Y axes", key="a_reverse_axes", disabled=(is_polar or is_1d_hist))
            reverse_axes = st.session_state.a_reverse_axes
        else:
            st.warning("No valid secondary variables found for this group.")

        section_divider()
        
        color_opts = ["None", "Variable:"]
        init_state('a_scatter_color', "None")
        if st.session_state.a_scatter_color not in color_opts: st.session_state.a_scatter_color = "None"
        scatter_color_mode = st.selectbox("Scatter Color by:", color_opts, key="a_scatter_color", disabled=not is_scatter)

        color_by_var = (is_scatter and scatter_color_mode == "Variable:")
        
        def reset_scatter_color_dep():
            if 'a_custom_colorscale' in st.session_state:
                del st.session_state['a_custom_colorscale']
            if 'a_rev_cmap' in st.session_state:
                del st.session_state['a_rev_cmap']
                
        if ordered:
            init_state('a_scatter_color_var', ordered[0])
            if st.session_state.a_scatter_color_var not in ordered: st.session_state.a_scatter_color_var = ordered[0]
            st.selectbox("Color Variable", ordered, key="a_scatter_color_var", on_change=reset_scatter_color_dep, format_func=lambda x: plotter._get_var_display_name(sel_group or "", x), disabled=not color_by_var, label_visibility="collapsed")

        sidebar_label("Marker Size:", size='label', enabled=is_scatter)
        init_state('a_scatter_marker_size', 100)
        st.slider("Scatter Marker Size", min_value=10, max_value=200, step=10, format="%d%%", key="a_scatter_marker_size", disabled=not is_scatter, label_visibility="collapsed")

        scatter_color_var = st.session_state.get('a_scatter_color_var') if color_by_var else None
        scatter_marker_size = st.session_state.get('a_scatter_marker_size', 100) if is_scatter else 100

    _ordered = ordered if (not 'TRACK' in sel_group.upper() and (is_scatter or analysis_type == "Histogram Analysis (2D)")) else []
    return sel_group, variable, coord_var, scatter_color_var, scatter_marker_size, _ordered, reverse_axes


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
        
    sel_group, variable, coord_var, scatter_color_var, scatter_marker_size, scatter_var_list, reverse_axes = _render_analysis_variable_section(data_pack, plotter, analysis_type)
    intent.sel_group = sel_group
    intent.variable = variable
    intent.coord_var = coord_var
    intent.scatter_color_var = scatter_color_var
    intent.scatter_marker_size = scatter_marker_size
    intent.reverse_axes = reverse_axes
        
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
        
        c_cs1, c_cs2 = st.columns([1.1, 1.8])
        with c_cs1:
            sidebar_label("Colorscale:", size='label', enabled=not is_1d_hist)
        with c_cs2:
            custom_colorscale = st.selectbox(
                "Colorscale", cmaps, 
                key='a_custom_colorscale', label_visibility="collapsed", disabled=is_1d_hist,
                format_func=lambda x: COLORSCALE_NAMES.get(x, x)
            )

        intent.custom_colorscale = custom_colorscale

        v1_lower = intent.variable.lower() if intent.variable else ""
        v2_lower = intent.coord_var.lower() if intent.coord_var else ""
        
        # Dynamically checks for ANY azimuth flag matching the new generalized string pattern
        has_az   = any(v.startswith("azimuth_") for v in [v1_lower, v2_lower])
        has_dist = "dist_from_center" in [v1_lower, v2_lower]
        is_polar_eligible = has_az and has_dist and not is_1d_hist

        if not is_polar_eligible and st.session_state.get('a_coord_sys') == "Polar":
            st.session_state.a_coord_sys = "Cartesian"

        c_sys1, c_sys2 = st.columns([1.4, 1.8])
        with c_sys1:
            sidebar_label("Coordinate System:", size='label', enabled=is_polar_eligible)
        with c_sys2:
            init_state('a_coord_sys', "Cartesian")
            coord_sys = st.selectbox(
                "Coordinate System", ["Cartesian", "Polar"],
                key='a_coord_sys', label_visibility="collapsed", disabled=not is_polar_eligible
            )
        intent.coordinate_system = coord_sys
        is_polar = (coord_sys == "Polar")
        
        lons = ['lon', 'longitude', 'clon']
        lats = ['lat', 'latitude', 'clat']
        is_lat_lon = ((v1_lower in lons and v2_lower in lats) or 
                      (v1_lower in lats and v2_lower in lons))
        map_eligible = is_lat_lon and not is_1d_hist
        
        c_map1, c_map2 = st.columns([1.4, 1.8])
        with c_map1:
            sidebar_label("Map Option:", size='label', enabled=map_eligible)
        with c_map2:
            init_state('a_map_option', "None")
            if not map_eligible and st.session_state.a_map_option != "None":
                st.session_state.a_map_option = "None"
            map_option = st.selectbox(
                "Map Option", ["None", "Show Map"],
                key='a_map_option', label_visibility="collapsed", disabled=not map_eligible
            )
        intent.map_option = map_option
        
        section_divider()

        st.markdown("#### Histogram Controls")

        effective_reverse = False if is_polar else st.session_state.get('a_reverse_axes', False)
        x_var_lower = v1_lower if effective_reverse else v2_lower
        y_var_lower = v2_lower if effective_reverse else v1_lower

        is_x_az = 'azimuth' in x_var_lower
        is_y_az = 'azimuth' in y_var_lower

        lbl_x = "Bins (Az):" if (is_polar and is_x_az) else ("Bins (Rad):" if is_polar else "Bins (X):")
        lbl_y = "Bins (Az):" if (is_polar and is_y_az) else ("Bins (Rad):" if is_polar else "Bins (Y):")

        def_x = DEFAULT_HIST_BINS
        def_y = DEFAULT_HIST_BINS
        if is_polar:
            def_x = DEFAULT_HIST_BINS_AZIMUTH if is_x_az else DEFAULT_HIST_BINS_RADIAL
            def_y = DEFAULT_HIST_BINS_AZIMUTH if is_y_az else DEFAULT_HIST_BINS_RADIAL

        c_lx, c_ix, c_ly, c_iy = st.columns([0.8, 1.2, 0.8, 1.2])
        
        with c_lx:
            sidebar_label(lbl_x, size='label', enabled=not is_scatter)
        with c_ix:
            val_x = st.number_input(
                "Bins X Input", min_value=1, max_value=1000, value=def_x, step=1, 
                key=f"bin_x_auto_{is_polar}_{is_x_az}", label_visibility="collapsed", disabled=is_scatter
            )
            intent.hist_bins_x = val_x

        with c_ly:
            sidebar_label(lbl_y, size='label', enabled=not (is_1d_hist or is_scatter))
        with c_iy:
            val_y = st.number_input(
                "Bins Y Input", min_value=1, max_value=1000, value=def_y, step=1, 
                key=f"bin_y_auto_{is_polar}_{is_y_az}", disabled=(is_1d_hist or is_scatter), label_visibility="collapsed"
            )
            intent.hist_bins_y = val_y if not is_1d_hist else None

        c7, c8 = st.columns([1.4, 1.8])
        with c7: sidebar_label("Normalization:", size='label', enabled=not is_scatter)
        with c8:
            init_state('a_hist_norm', "None")
            norm_opts = ["None", "Normalize within each Primary bin", "Normalize within each Secondary bin", "Normalize Fully"] if is_2d else ["None", "Normalize Fully"]
            if st.session_state.a_hist_norm not in norm_opts: st.session_state.a_hist_norm = "None"
            norm_val = st.selectbox("Normalization Option", norm_opts, key='a_hist_norm', label_visibility="collapsed", disabled=is_scatter)
            intent.normalization = norm_val if not is_scatter else "None"

        init_state('a_render_as_line', False)
        if not is_1d_hist and st.session_state.a_render_as_line: st.session_state.a_render_as_line = False
        st.checkbox("Render as line plot", key="a_render_as_line", disabled=not is_1d_hist)
        intent.render_as_line = st.session_state.a_render_as_line if is_1d_hist else False
        
        init_state('a_show_kde', False)
        if is_scatter and st.session_state.a_show_kde: st.session_state.a_show_kde = False
        st.checkbox("Overlay Density Curve/Contours (KDE)", key="a_show_kde", disabled=is_scatter)
        intent.show_kde = st.session_state.a_show_kde if not is_scatter else False

        init_state('a_show_marginals', False)
        marginals_allowed = not (is_1d_hist or is_scatter)
        if not marginals_allowed:
            st.session_state.a_show_marginals = False

        st.checkbox(
            "Show Marginal Distributions", 
            key="a_show_marginals", 
            disabled=not marginals_allowed,
            help="Available for 2D Histogram Analysis only." if is_scatter else None
        )
        intent.show_marginals = st.session_state.a_show_marginals if marginals_allowed else False
                
    intent.log_var       = (st.session_state.get('a_scale_var', 'Linear scale') == 'Log scale')
    intent.log_coord_var = (st.session_state.get('a_scale_coord_var', 'Linear scale') == 'Log scale')

    sync_namespace('a_', 'analysis_state')
    return intent
