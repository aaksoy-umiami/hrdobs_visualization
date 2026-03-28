# -*- coding: utf-8 -*-
"""
ui_viewer_controls.py
---------------------
All sidebar widget logic for the File Data Viewer tab.
"""

import math
import streamlit as st
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from config import EXPECTED_GROUPS, EXPECTED_META, AVAILABLE_COLORSCALES, GLOBAL_VAR_CONFIG, COLORSCALE_NAMES
from data_utils import load_data_from_h5, decode_metadata, compute_global_domain, compute_vert_bounds
from ui_layout import CLR_MUTED, CLR_SUCCESS, CLR_EXTRA, FS_TABLE, FS_BODY
from ui_components import section_divider, spacer, sidebar_label, init_state, sync_namespace, consume_flag
from ui_viewer_file import render_file_upload_section

@dataclass
class ViewerIntent:
    data_pack:        Optional[Dict]  = None
    sel_group:        Optional[str]   = None
    plot_var:         Optional[str]   = None   
    variable:         Optional[str]   = None   
    color_scale:      str             = "Linear scale"
    custom_colorscale:Optional[str]   = None
    show_cen:         bool            = True
    cen_mode:         str             = "Display Location Only"
    apply_thinning:   bool            = False
    thin_pct:         int             = 50
    z_con:            Optional[Dict]  = None
    track_mapping:    Dict            = field(default_factory=dict)
    plot_track:       bool            = False
    selected_platform:Optional[str]  = None
    track_proj:       str             = "Bottom Only"
    is_3d:            bool            = False
    plot_z_col:       Optional[str]   = None
    z_ratio:          float           = 0.3
    show_basemap:     bool            = False
    marker_sz:        int             = 100
    vec_scale:        float           = 1.0
    domain_bounds:    Optional[Dict]  = None
    time_bounds:      Optional[Dict]  = None
    plot_type:        str             = "Horizontal Cartesian"
    sr_up_convention: str             = "Relative to North"
    sr_track_grp:     Optional[str]   = None
    rh_z_col:         Optional[str]   = None
    default_lat_min:  float           = 0.0
    default_lat_max:  float           = 0.0
    default_lon_min:  float           = 0.0
    default_lon_max:  float           = 0.0

_VIEWER_STATE_KEYS = [
    'v_sel_group', 'v_variable', 'v_use_filter', 'v_vert_coord',
    'v_lvl_range', 'v_is_3d', 'v_3d_z', 'v_plot_track', 'v_sel_plat',
    'v_3d_ratio', 'v_apply_thinning', 'v_thin_pct', 'v_marker_size',
    'v_lat_range', 'v_lon_range', 'v_time_range', 'v_show_cen', 'v_cen_mode',
    'v_clat', 'v_clon', 'v_track_proj', 'v_vert_range', 'v_color_scale',
    'v_plot_err', 'v_vec_scale', 'v_show_basemap',
    'v_plot_type', 'v_sr_up', 'v_sr_track_grp', 'v_custom_colorscale'
]

def _extract_strict_bound(data_pack, key):
    for k, v in data_pack['meta'].get('info', {}).items():
        if str(k).strip("[]b'\" ").lower() == key.lower():
            try:
                return float(decode_metadata(v))
            except Exception:
                return None
    return None

def _render_variable_section(data_pack, plotter, plot_type="Horizontal Cartesian"):
    available_groups = sorted(list(data_pack['data'].keys()))
    init_state('v_sel_group', available_groups[0] if available_groups else None)

    if st.session_state.v_sel_group not in available_groups:
        st.session_state.v_sel_group = available_groups[0] if available_groups else None

    def reset_group_dependencies():
        st.session_state.v_apply_thinning = False
        st.session_state.v_thin_pct = 50
        if 'show_auto_thin_msg' in st.session_state:
            st.session_state.show_auto_thin_msg = False
        for k in ['v_lvl_range', 'v_time_range', 'v_last_coord',
                  'v_vert_range', 'v_plot_err', 'v_vec_scale', '_last_dom_z_col', 'v_custom_colorscale']:
            if k in st.session_state:
                del st.session_state[k]

    def reset_var_dependencies():
        if 'v_plot_err' in st.session_state:
            del st.session_state['v_plot_err']
        if 'v_custom_colorscale' in st.session_state:
            del st.session_state['v_custom_colorscale']

    with st.sidebar.container(border=True):
        st.markdown("### 📈 Plot Variable")

        sel_group = st.selectbox(
            "Select Active Group to Plot", available_groups,
            key='v_sel_group', on_change=reset_group_dependencies
        )

        h_col = p_col = None
        df_sel = None
        cols_lower = {}

        if 'TRACK' not in sel_group.upper():
            df_sel     = data_pack['data'][sel_group]
            cols_lower = {c.lower(): c for c in df_sel.columns}
            h_col = next((cols_lower[c] for c in ['height', 'ght', 'altitude', 'elev'] if c in cols_lower), None)
            p_col = next((cols_lower[c] for c in ['pres', 'pressure', 'p'] if c in cols_lower), None)
        elif sel_group in data_pack['data']:
            df_sel     = data_pack['data'][sel_group]
            cols_lower = {c.lower(): c for c in df_sel.columns}

        exclude_col = (st.session_state.get('v_vert_coord') if st.session_state.get('v_use_filter') else None)

        rh_z_col = None
        if plot_type == "Radial-Height Profile":
            rh_z_options = [c for c in [h_col, p_col] if c]
            if rh_z_options:
                init_state('v_rh_z_col', rh_z_options[0])
                if st.session_state.v_rh_z_col not in rh_z_options:
                    st.session_state.v_rh_z_col = rh_z_options[0]
                rh_z_col = st.session_state.v_rh_z_col

        vars_list = plotter.get_plottable_variables(
            sel_group, active_z_col=exclude_col or rh_z_col, exclude_vectors=False
        )

        variable = plot_var = color_scale = None

        if vars_list:
            init_state('v_variable', vars_list[0])
            if st.session_state.v_variable not in vars_list:
                st.session_state.v_variable = vars_list[0]

            v_c1, v_c2 = st.columns([1.6, 1])
            with v_c1:
                variable = st.selectbox(
                    "Variable", vars_list, key='v_variable', on_change=reset_var_dependencies,
                    format_func=lambda x: plotter._get_var_display_name(sel_group, x)
                )
            with v_c2:
                init_state('v_color_scale', "Linear scale")
                color_scale = st.selectbox("Plot on:", ["Linear scale", "Log scale"], key='v_color_scale')
            
            plot_var  = variable
            var_lower = variable.lower()

            err_candidates = [f"{var_lower}err", f"{var_lower}_err", f"{var_lower}_error", f"{var_lower}error"]
            actual_err_col = next((cols_lower[c] for c in err_candidates if c in cols_lower), None)
            err_lbl = "Plot Error (Computed)" if "_comp" in var_lower else "Plot Error"

            if actual_err_col:
                err_vals = df_sel[actual_err_col].dropna().values
                if len(err_vals) == 0:
                    st.checkbox(err_lbl, disabled=True, value=False, key=f"err_na_{variable}")
                else:
                    e_min, e_max = float(np.min(err_vals)), float(np.max(err_vals))
                    if np.isclose(e_min, e_max, rtol=1e-5, atol=1e-8):
                        e_unit = decode_metadata(data_pack['var_attrs'].get(sel_group, {}).get(actual_err_col, {}).get('units', ''))
                        unit_str = f" {e_unit}" if e_unit else ""
                        st.checkbox(f"{err_lbl} (Constant at {e_min:g}{unit_str})", disabled=True, value=False, key=f"err_const_{variable}")
                    else:
                        init_state('v_plot_err', False)
                        if st.checkbox(err_lbl, key='v_plot_err'):
                            plot_var = actual_err_col
            else:
                st.checkbox(err_lbl, disabled=True, value=False, key=f"err_miss_{variable}")
        else:
            st.stop()

    return sel_group, variable, plot_var, color_scale, h_col, p_col, df_sel, cols_lower, rh_z_col


def _render_plot_type_section(data_pack, sel_group, is_3d, h_col=None, p_col=None, plotter=None):
    available_tracks = []
    track_candidates = ['track_best_track', 'track_spline_track', 'track_vortex_message']
    for t in track_candidates:
        if t in data_pack['data'] and len(data_pack['data'][t]) >= 2:
            if not sel_group or t.lower() != sel_group.lower():
                available_tracks.append(t)

    _sr_available = (len(available_tracks) > 0 and not is_3d)
    _PLOT_TYPES = ["Horizontal Cartesian", "Horizontal Storm-Relative", "Radial-Height Profile"]

    init_state('v_plot_type', "Horizontal Cartesian")
    
    if not _sr_available and st.session_state.v_plot_type in ("Horizontal Storm-Relative", "Radial-Height Profile"):
        st.session_state.v_plot_type = "Horizontal Cartesian"

    current_plot_type = st.session_state.get('v_plot_type', "Horizontal Cartesian")
    if st.session_state.get('_prev_plot_type') != current_plot_type:
        if current_plot_type == "Horizontal Storm-Relative":
            st.session_state.v_show_cen = True
        elif current_plot_type == "Radial-Height Profile":
            st.session_state.v_show_cen = False
        st.session_state._prev_plot_type = current_plot_type

    with st.sidebar.container(border=True):
        st.markdown("### 🧭 Plot Type")
        plot_type = st.selectbox(
            "Plot Type", _PLOT_TYPES, key='v_plot_type', disabled=False, label_visibility="collapsed",
            help="Storm-Relative and Radial-Height Profile require an alternate track (≥2 points). Unavailable in 3D mode."
        )

        is_sr  = (plot_type == "Horizontal Storm-Relative")
        is_rh  = (plot_type == "Radial-Height Profile")
        requires_track = is_sr or is_rh

        if not _sr_available and st.session_state.v_plot_type == "Horizontal Cartesian":
            if is_3d:
                st.caption("ℹ️ Storm-Relative / Radial-Height unavailable in 3D mode.")
            elif len(available_tracks) == 0:
                st.caption("ℹ️ Storm-Relative / Radial-Height requires an alternate track group (≥2 points).")

        def format_track_name(t):
            if t == 'track_best_track': return 'Best Track'
            if t == 'track_spline_track': return 'Spline Track'
            if t == 'track_vortex_message': return 'Vortex Message'
            return t.replace('_', ' ').title()

        if available_tracks:
            init_state('v_sr_track_grp', 'track_spline_track' if 'track_spline_track' in available_tracks else available_tracks[0])
            if st.session_state.v_sr_track_grp not in available_tracks:
                st.session_state.v_sr_track_grp = 'track_spline_track' if 'track_spline_track' in available_tracks else available_tracks[0]

        sr_track_grp = st.selectbox(
            "Reference Track", options=available_tracks if available_tracks else ["No alternate track available"],
            key='v_sr_track_grp' if available_tracks else 'v_sr_track_grp_dummy',
            disabled=not requires_track or not available_tracks,
            format_func=lambda x: format_track_name(x) if x in available_tracks else x
        )

        if not requires_track or not available_tracks:
            sr_track_grp = None

        init_state('v_sr_up', "Relative to North")

        sub_c1, sub_c2 = st.columns([1.1, 1.3])
        if is_sr:
            with sub_c1: sidebar_label("Upward Direction Represents:", enabled=True, size='label')
            with sub_c2:
                sr_up_convention = st.selectbox("Up direction", ["Relative to North", "Relative to Storm Motion"], key='v_sr_up', disabled=False, label_visibility="collapsed")
            rh_z_col = None
        elif is_rh:
            rh_z_options = [c for c in [h_col, p_col] if c]
            init_state('v_rh_z_col', rh_z_options[0] if rh_z_options else None)
            if st.session_state.get('v_rh_z_col') not in rh_z_options:
                st.session_state.v_rh_z_col = rh_z_options[0] if rh_z_options else None
                
            with sub_c1: sidebar_label("Plot on Z axis:", enabled=bool(rh_z_options), size='label')
            with sub_c2:
                if rh_z_options and plotter:
                    rh_z_col = st.selectbox("RH Z axis", rh_z_options, key='v_rh_z_col', disabled=False, label_visibility="collapsed", format_func=lambda x: plotter._get_var_display_name(sel_group, x))
                else:
                    rh_z_col = st.session_state.get('v_rh_z_col')
            sr_up_convention = st.session_state.get('v_sr_up', "Relative to North")
        else:
            sr_up_convention = st.session_state.get('v_sr_up', "Relative to North")
            rh_z_col = None

    return plot_type, sr_up_convention, sr_track_grp, rh_z_col


def _render_plotting_options(data_pack, sel_group, h_col, p_col, df_sel, cols_lower, plot_var, plot_type="Horizontal Cartesian"):
    with st.sidebar.container(border=True):
        st.markdown("### ⚙️ Plotting Options")
        
        default_cmap = GLOBAL_VAR_CONFIG.get(plot_var.lower() if plot_var else "", {}).get('colorscale', 'Turbo')
        cmaps = sorted(list(set(AVAILABLE_COLORSCALES + [default_cmap])))
        init_state('v_custom_colorscale', default_cmap)
        
        # Clean two-column layout for Colorscale
        c_cs1, c_cs2 = st.columns([1.1, 1.8])
        with c_cs1:
            sidebar_label("Colorscale:", size='label')
        with c_cs2:
            custom_colorscale = st.selectbox(
                "Colorscale", cmaps, 
                key='v_custom_colorscale', label_visibility="collapsed",
                format_func=lambda x: COLORSCALE_NAMES.get(x, x)
            )

        section_divider()

        is_rh  = (plot_type == "Radial-Height Profile")
        is_sr  = (plot_type == "Horizontal Storm-Relative")

        init_state('v_show_cen', True)
        init_state('v_cen_mode', "Display Location Only")

        if is_rh: st.session_state.v_show_cen = False

        c_cen1, c_cen2 = st.columns([1, 1.5])
        with c_cen1:
            spacer('sm')
            show_cen = st.checkbox("Storm Center", key='v_show_cen', disabled=is_rh)
        with c_cen2:
            cen_mode = st.selectbox("Center Mode", ["Display Location Only", "Display As Motion Vector"], key='v_cen_mode', disabled=not show_cen or is_rh, label_visibility="collapsed")

        is_3d_state = st.session_state.get('v_is_3d', False)
        disable_map = is_3d_state or is_sr or is_rh

        init_state('v_show_basemap', False)
        if disable_map and st.session_state.v_show_basemap:
            st.session_state.v_show_basemap = False
            
        show_basemap = st.checkbox("Show Map Underlay", key='v_show_basemap', disabled=disable_map)
        
        if is_3d_state: st.caption("ℹ️ Map underlay is disabled in 3D mode.")
        elif is_sr: st.caption("ℹ️ Map underlay is disabled in Storm-Relative mode.")
        elif is_rh: st.caption("ℹ️ Map underlay is disabled in Radial-Height mode.")
            
        section_divider()

        if consume_flag('_force_thinning'):
            st.session_state.v_apply_thinning = True
            st.session_state.v_thin_pct = consume_flag('_force_thin_pct') or 50

        init_state('v_apply_thinning', False)
        apply_thinning = st.checkbox("Apply thinning?", key='v_apply_thinning')

        thin_color = "inherit" if apply_thinning else CLR_MUTED
        t_c1, t_c2, t_c3 = st.columns([0.8, 2.8, 1.2])
        with t_c1: st.markdown(f"<div style='margin-top: 6px; font-size: {FS_BODY}px; font-weight: 500; color:{thin_color}; text-align:right;'>Show</div>", unsafe_allow_html=True)
        with t_c2:
            init_state('v_thin_pct', 50)
            thin_pct = st.slider("Thinning", min_value=5, max_value=100, step=5, key='v_thin_pct', disabled=not apply_thinning, label_visibility="collapsed")
        with t_c3: st.markdown(f"<div style='margin-top: 6px; font-size: {FS_BODY}px; font-weight: 500; color:{thin_color};'>% of obs.</div>", unsafe_allow_html=True)

        section_divider()

        z_con       = None
        target_col  = None
        options     = [c for c in [h_col, p_col] if c]

        init_state('v_use_filter', False)
        if is_rh and st.session_state.v_use_filter: st.session_state.v_use_filter = False
        if not options and st.session_state.v_use_filter: st.session_state.v_use_filter = False
            
        use_filter = st.checkbox("Filter by Level?", key='v_use_filter', disabled=not options or is_rh)

        if options:
            c_c, c_s = st.columns([1.2, 2.0])
            if st.session_state.get('v_vert_coord') not in options:
                st.session_state.v_vert_coord = options[0]
            with c_c:
                sidebar_label("Vertical Coord.", enabled=use_filter)
                def _fmt_vert(x):
                    meta = data_pack.get('var_attrs', {}).get(sel_group, {}).get(x, {})
                    long = decode_metadata(meta.get('long_name', '')) or x.replace('_', ' ').title()
                    units = decode_metadata(meta.get('units', ''))
                    return f"{long.title()} ({units})" if units else long.title()
                target_col = st.selectbox("VCoord", options, key='v_vert_coord', disabled=not use_filter, label_visibility="collapsed", format_func=_fmt_vert)
            
            v_unit = decode_metadata(data_pack['var_attrs'].get(sel_group, {}).get(target_col, {}).get('units', ''))
            convert = 'Pa' in v_unit and 'hPa' not in v_unit
            if convert: v_unit = 'hPa'

            raw_vals = df_sel[target_col].dropna().values
            if len(raw_vals) > 0:
                if convert: raw_vals = raw_vals / 100.0
                dmin, dmax = float(np.nanmin(raw_vals)), float(np.nanmax(raw_vals))
                if dmin == dmax: dmax = dmin + 1.0
                with c_s:
                    sidebar_label(f"Range ({v_unit})", enabled=use_filter)
                    if st.session_state.get('v_last_coord') != target_col:
                        st.session_state.v_lvl_range  = (dmin, dmax)
                        st.session_state.v_last_coord = target_col
                    elif 'v_lvl_range' not in st.session_state:
                        st.session_state.v_lvl_range = (dmin, dmax)
                    else:
                        c_min, c_max = st.session_state.v_lvl_range
                        c_min = max(dmin, min(c_min, dmax))
                        c_max = max(dmin, min(c_max, dmax))
                        if c_min > c_max: c_min = c_max
                        st.session_state.v_lvl_range = (c_min, c_max)

                    lvl_range = st.slider("Range", min_value=dmin, max_value=dmax, key='v_lvl_range', disabled=not use_filter, label_visibility="collapsed")
                if use_filter:
                    z_con = {'col': target_col, 'val': (lvl_range[1] + lvl_range[0]) / 2.0, 'tol': abs(lvl_range[1] - lvl_range[0]) / 2.0, 'convert_pa_to_hpa': convert}

        section_divider()

        available_groups  = sorted(list(data_pack['data'].keys()))
        flight_track_grps = [g for g in available_groups if g.lower().startswith('flight_level_hdobs')]
        track_mapping     = {g.split('_')[-1].upper(): g for g in flight_track_grps}

        track_col1, track_col2 = st.columns([1.1, 1])
        with track_col1:
            spacer('sm')
            init_state('v_plot_track', False)
            plot_track = st.checkbox("Plot flight track from:", key='v_plot_track', disabled=(len(track_mapping) == 0))
        with track_col2:
            init_state('v_sel_plat', list(track_mapping.keys())[0] if track_mapping else None)
            if st.session_state.v_sel_plat not in track_mapping:
                st.session_state.v_sel_plat = list(track_mapping.keys())[0] if track_mapping else None
                
            selected_platform = (st.selectbox("Platform", list(track_mapping.keys()), key='v_sel_plat', disabled=not plot_track, label_visibility="collapsed") if track_mapping else None)

        p_c1, p_c2 = st.columns([1.4, 1])
        with p_c1:
            is_3d_state   = st.session_state.get('v_is_3d', False)
            proj_disabled = True if is_rh else not (plot_track and is_3d_state)
            p_color       = "inherit" if not proj_disabled else CLR_MUTED
            st.markdown(f"<div style='margin-top: 8px; font-size: {FS_BODY}px; font-weight: 500; color: {p_color};'>Display track projection:</div>", unsafe_allow_html=True)
        with p_c2:
            init_state('v_track_proj', "Bottom Only")
            if is_rh:
                st.session_state.v_track_proj = "Show" if plot_track else "None"
                proj_options = ["Show"] if plot_track else ["None"]
            else:
                proj_options = ["None", "Bottom Only", "Sides Only", "Bottom + Sides"]
                if st.session_state.v_track_proj not in proj_options:
                    st.session_state.v_track_proj = proj_options[0]
            track_proj = st.selectbox("Projection", proj_options, key='v_track_proj', disabled=proj_disabled, label_visibility="collapsed")

        section_divider()

        can_do_3d = (h_col is not None or p_col is not None) and not is_rh
        if (not can_do_3d or is_rh) and st.session_state.get('v_is_3d', False):
            st.session_state.v_is_3d = False

        c3d_1, c3d_2 = st.columns([1.1, 1])
        with c3d_1:
            spacer('sm')
            init_state('v_is_3d', False)
            is_3d = st.checkbox("3D view with z axis:", key='v_is_3d', disabled=not can_do_3d)
        with c3d_2:
            options_3d = options if options else ["None"]
            if st.session_state.get('v_3d_z') not in options_3d:
                st.session_state.v_3d_z = options_3d[0]
            target_col_3d = st.selectbox("Select 3D Z-Axis", options_3d, key='v_3d_z', label_visibility="collapsed", disabled=not is_3d)

        plot_z_col = target_col if use_filter else (target_col_3d if options else None)

        r1, r2 = st.columns([1.1, 2.2])
        with r1:
            sidebar_label("Vert. Aspect Ratio:", enabled=is_3d)
        with r2:
            init_state('v_3d_ratio', 0.3)
            z_ratio = st.slider("VAR", min_value=0.05, max_value=1.5, step=0.05, key='v_3d_ratio', disabled=not is_3d, label_visibility="collapsed")

        section_divider()

        m1, m2    = st.columns([1.1, 2.2])
        is_vector = plot_var and "wind_vec" in plot_var.lower()
        with m1:
            sidebar_label("Vector Scale:" if is_vector else "Marker Size:", size='label')
        with m2:
            if is_vector:
                init_state('v_vec_scale', 1.0)
                vec_scale = st.slider("Vector Scale", min_value=0.1, max_value=5.0, step=0.1, key='v_vec_scale', label_visibility="collapsed")
                marker_sz = 100
            else:
                init_state('v_marker_size', 100)
                marker_sz = st.slider("Marker Size", min_value=10, max_value=200, step=10, format="%d%%", key='v_marker_size', label_visibility="collapsed")
                vec_scale = 1.0

    return (show_cen, cen_mode, apply_thinning, thin_pct, z_con, target_col,
            target_col_3d, track_mapping, plot_track, selected_platform,
            track_proj, is_3d, plot_z_col, z_ratio, marker_sz, vec_scale,
            can_do_3d, custom_colorscale)

def render_viewer_controls(plotter) -> ViewerIntent:
    intent = ViewerIntent()
    init_state('viewer_state', {})

    data_pack = render_file_upload_section(
        data_pack_key='data_pack', 
        filename_key='last_uploaded_filename', 
        state_keys=_VIEWER_STATE_KEYS, 
        state_dict_key='viewer_state'
    )

    if data_pack is None: return intent
    intent.data_pack = data_pack

    from plotter import StormPlotter
    plotter = StormPlotter(data_pack['data'], data_pack['track'], data_pack['meta'], data_pack['var_attrs'])

    if data_pack['meta']['storm_center'] is None:
        with st.sidebar.container(border=True):
            st.warning("⚠️ Storm Center Missing from Metadata")
            init_state('v_clat', 20.0)
            init_state('v_clon', -50.0)
            c1, c2 = st.columns(2)
            clat = c1.number_input("Manual Lat", key='v_clat')
            clon = c2.number_input("Manual Lon", key='v_clon')
            data_pack['meta']['storm_center'] = (clat, clon)

    intent.default_lat_min = _extract_strict_bound(data_pack, 'geospatial_lat_min') or 0.0
    intent.default_lat_max = _extract_strict_bound(data_pack, 'geospatial_lat_max') or 0.0
    intent.default_lon_min = _extract_strict_bound(data_pack, 'geospatial_lon_min') or 0.0
    intent.default_lon_max = _extract_strict_bound(data_pack, 'geospatial_lon_max') or 0.0

    plot_type = st.session_state.get('v_plot_type', 'Horizontal Cartesian')
    (sel_group, variable, plot_var, color_scale, h_col, p_col, df_sel, cols_lower, rh_z_col) = _render_variable_section(data_pack, plotter, plot_type)
    intent.sel_group   = sel_group
    intent.variable    = variable
    intent.plot_var    = plot_var
    intent.color_scale = color_scale

    options = [c for c in [h_col, p_col] if c]

    _cur_is_3d = st.session_state.get('v_is_3d', False)
    plot_type, sr_up_convention, sr_track_grp, rh_z_col = _render_plot_type_section(
        data_pack, sel_group, _cur_is_3d, h_col=h_col, p_col=p_col, plotter=plotter
    )

    (show_cen, cen_mode, apply_thinning, thin_pct, z_con, target_col,
     target_col_3d, track_mapping, plot_track, selected_platform,
     track_proj, is_3d, plot_z_col, z_ratio, marker_sz, vec_scale,
     can_do_3d, custom_colorscale) = _render_plotting_options(
         data_pack, sel_group, h_col, p_col, df_sel, cols_lower, plot_var, plot_type
     )

    intent.custom_colorscale = custom_colorscale
    intent.show_cen          = show_cen
    intent.cen_mode          = cen_mode
    intent.show_basemap      = st.session_state.get('v_show_basemap', False)
    intent.apply_thinning    = apply_thinning
    intent.thin_pct          = thin_pct
    intent.z_con             = z_con
    intent.track_mapping     = track_mapping
    intent.plot_track        = plot_track
    intent.selected_platform = selected_platform
    intent.track_proj        = track_proj
    intent.is_3d             = is_3d
    intent.plot_z_col        = plot_z_col
    intent.z_ratio           = z_ratio
    intent.marker_sz         = marker_sz
    intent.vec_scale         = vec_scale
    intent.plot_type         = plot_type
    intent.sr_up_convention  = sr_up_convention
    intent.sr_track_grp      = sr_track_grp
    intent.rh_z_col          = rh_z_col

    from ui_viewer_domain import _render_domain_section, _render_time_section
    
    (domain_bounds, convert_dom, vert_range, domain_z_col) = _render_domain_section(
         data_pack, sel_group, df_sel, options, target_col, target_col_3d, is_3d,
         intent.default_lat_min, intent.default_lat_max, intent.default_lon_min, intent.default_lon_max,
         plot_type=plot_type, sr_track_grp=sr_track_grp, plotter=plotter, rh_z_col=rh_z_col
     )
    intent.domain_bounds = domain_bounds

    if df_sel is not None:
        intent.time_bounds = _render_time_section(
            data_pack, sel_group, df_sel, domain_bounds,
            plot_type=plot_type, sr_track_grp=sr_track_grp, plotter=plotter
        )

    sync_namespace('v_', 'viewer_state')
    return intent
