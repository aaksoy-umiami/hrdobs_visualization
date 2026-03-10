# -*- coding: utf-8 -*-
"""
ui_viewer_controls.py
---------------------
All sidebar widget logic for the File Data Viewer tab.

render_viewer_controls() renders every sidebar section and returns a
ViewerIntent dataclass that the caller (ui_viewer.py) passes straight
to the plotter — no Streamlit state is read after this function returns.
"""

import math
import streamlit as st
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from config import EXPECTED_GROUPS, EXPECTED_META
from data_utils import load_data_from_h5, decode_metadata
from ui_layout import CLR_MUTED, CLR_SUCCESS, CLR_EXTRA, FS_TABLE, FS_BODY
from ui_components import section_divider, spacer, sidebar_label


# ---------------------------------------------------------------------------
# Return type — everything the viewer needs to render a plot
# ---------------------------------------------------------------------------

@dataclass
class ViewerIntent:
    """Plain data object produced by the sidebar controls."""
    data_pack:        Optional[Dict]  = None
    sel_group:        Optional[str]   = None
    plot_var:         Optional[str]   = None   # may differ from variable (error mode)
    variable:         Optional[str]   = None   # the base variable selected
    color_scale:      str             = "Linear scale"
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
    # Slider limits — needed by the main tab for auto-fit logic
    default_lat_min:  float           = 0.0
    default_lat_max:  float           = 0.0
    default_lon_min:  float           = 0.0
    default_lon_max:  float           = 0.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_strict_bound(data_pack, key):
    for k, v in data_pack['meta'].get('info', {}).items():
        if str(k).strip("[]b'\" ").lower() == key.lower():
            try:
                return float(decode_metadata(v))
            except Exception:
                return None
    return None


def _inject_derived_fields(raw_data_pack):
    """
    Post-load enrichment: adds SFMR altitude, derived wind speeds,
    propagated error estimates, and vector dummy variables in-place.
    """
    for grp in raw_data_pack['data'].keys():
        df_grp = raw_data_pack['data'][grp]
        if grp not in raw_data_pack['var_attrs']:
            raw_data_pack['var_attrs'][grp] = {}

        # SFMR: inject a nominal 10 m observation height
        if 'sfmr' in grp.lower():
            df_grp['altitude'] = 10.0
            raw_data_pack['var_attrs'][grp]['altitude'] = {
                'units': 'm', 'long_name': 'Assumed Observation Height'
            }

        cols_lower = {c.lower(): c for c in df_grp.columns}
        has_u = 'u' in cols_lower
        has_v = 'v' in cols_lower
        has_w = 'w' in cols_lower

        def get_err_col(var_name):
            cands = [f"{var_name}err", f"{var_name}_err",
                     f"{var_name}_error", f"{var_name}error"]
            return next((cols_lower[c] for c in cands if c in cols_lower), None)

        if not (has_u and has_v):
            continue

        u_c, v_c     = cols_lower['u'], cols_lower['v']
        u_vals       = df_grp[u_c]
        v_vals       = df_grp[v_c]
        u_units      = raw_data_pack['var_attrs'][grp].get(u_c, {}).get('units', 'm/s')
        u_err_c      = get_err_col('u')
        v_err_c      = get_err_col('v')

        # Horizontal wind speed
        wspd_hz = np.sqrt(u_vals**2 + v_vals**2)
        df_grp['wspd_hz_comp'] = wspd_hz
        raw_data_pack['var_attrs'][grp]['wspd_hz_comp'] = {
            'units': u_units, 'long_name': 'Horizontal Wind Speed (Computed)'
        }

        # Horizontal wind speed error
        if u_err_c and v_err_c:
            u_err_vals = df_grp[u_err_c]
            v_err_vals = df_grp[v_err_c]
            u_err_const = np.isclose(np.nanmin(u_err_vals), np.nanmax(u_err_vals))
            v_err_const = np.isclose(np.nanmin(v_err_vals), np.nanmax(v_err_vals))
            if u_err_const and v_err_const:
                hz_err      = np.sqrt(u_err_vals**2 + v_err_vals**2)
                hz_err_name = 'Horizontal Wind Speed Error (Static Computed)'
            else:
                hz_err = np.where(
                    wspd_hz > 0,
                    np.sqrt((u_vals * u_err_vals)**2 + (v_vals * v_err_vals)**2) / wspd_hz,
                    0.0
                )
                hz_err_name = 'Horizontal Wind Speed Error (Dynamic Computed)'
            df_grp['wspd_hz_comp_err'] = hz_err
            raw_data_pack['var_attrs'][grp]['wspd_hz_comp_err'] = {
                'units': u_units, 'long_name': hz_err_name
            }

        # 2-D wind vector placeholder
        df_grp['wind_vec_hz'] = wspd_hz
        raw_data_pack['var_attrs'][grp]['wind_vec_hz'] = {
            'units': u_units, 'long_name': 'Horizontal Wind Vectors'
        }

        if not has_w:
            continue

        w_c    = cols_lower['w']
        w_vals = df_grp[w_c]

        # 3-D wind speed
        wspd_3d = np.sqrt(u_vals**2 + v_vals**2 + w_vals**2)
        df_grp['wspd_3d_comp'] = wspd_3d
        raw_data_pack['var_attrs'][grp]['wspd_3d_comp'] = {
            'units': u_units, 'long_name': '3D Wind Speed (Computed)'
        }

        # 3-D wind speed error
        w_err_c = get_err_col('w')
        if u_err_c and v_err_c and w_err_c:
            u_err_vals = df_grp[u_err_c]
            v_err_vals = df_grp[v_err_c]
            w_err_vals = df_grp[w_err_c]
            u_err_const = np.isclose(np.nanmin(u_err_vals), np.nanmax(u_err_vals))
            v_err_const = np.isclose(np.nanmin(v_err_vals), np.nanmax(v_err_vals))
            w_err_const = np.isclose(np.nanmin(w_err_vals), np.nanmax(w_err_vals))
            if u_err_const and v_err_const and w_err_const:
                err_3d      = np.sqrt(u_err_vals**2 + v_err_vals**2 + w_err_vals**2)
                err_3d_name = '3D Wind Speed Error (Static Computed)'
            else:
                err_3d = np.where(
                    wspd_3d > 0,
                    np.sqrt((u_vals * u_err_vals)**2 + (v_vals * v_err_vals)**2 +
                            (w_vals * w_err_vals)**2) / wspd_3d,
                    0.0
                )
                err_3d_name = '3D Wind Speed Error (Dynamic Computed)'
            df_grp['wspd_3d_comp_err'] = err_3d
            raw_data_pack['var_attrs'][grp]['wspd_3d_comp_err'] = {
                'units': u_units, 'long_name': err_3d_name
            }

        # 3-D wind vector placeholder
        df_grp['wind_vec_3d'] = wspd_3d
        raw_data_pack['var_attrs'][grp]['wind_vec_3d'] = {
            'units': u_units, 'long_name': '3D Wind Vectors'
        }


def _compute_global_domain(data_pack):
    """Scan all groups for lat/lon and store a tight square bounding box
    in data_pack['global_domain']. Called at file load; also safe to call
    lazily if missing."""
    all_lats, all_lons = [], []
    for grp, df in data_pack['data'].items():
        if df is None or df.empty:
            continue
        cl = {c.lower(): c for c in df.columns}
        x_c = next((cl[c] for c in ['lon', 'longitude', 'clon'] if c in cl), None)
        y_c = next((cl[c] for c in ['lat', 'latitude',  'clat'] if c in cl), None)
        if x_c and y_c:
            lons = df[x_c].dropna().values
            lats = df[y_c].dropna().values
            if len(lons): all_lons.extend(lons.tolist())
            if len(lats): all_lats.extend(lats.tolist())

    if not all_lats or not all_lons:
        data_pack['global_domain'] = None
        return

    span_lat = max(float(np.max(all_lats)) - float(np.min(all_lats)), 0.05)
    span_lon = max(float(np.max(all_lons)) - float(np.min(all_lons)), 0.05)
    buf_lat  = span_lat * 0.05
    buf_lon  = span_lon * 0.05
    lat_min  = float(np.min(all_lats)) - buf_lat
    lat_max  = float(np.max(all_lats)) + buf_lat
    lon_min  = float(np.min(all_lons)) - buf_lon
    lon_max  = float(np.max(all_lons)) + buf_lon
    lat_span = lat_max - lat_min
    lon_span = lon_max - lon_min
    if lat_span > lon_span:
        extra = (lat_span - lon_span) / 2
        lon_min -= extra; lon_max += extra
    else:
        extra = (lon_span - lat_span) / 2
        lat_min -= extra; lat_max += extra

    data_pack['global_domain'] = {
        'lat_min': round(lat_min, 2), 'lat_max': round(lat_max, 2),
        'lon_min': round(lon_min, 2), 'lon_max': round(lon_max, 2),
    }


def _compute_vert_bounds(data_pack):
    """Pre-compute vertical (height/pressure) slider bounds for every group+column.
    Stored in data_pack['vert_bounds'] as {group: {col: (zmin_global, zmax_global, is_pres, unit)}}.
    Called once at file load alongside _compute_global_domain."""
    bounds = {}
    for grp, df in data_pack['data'].items():
        if df is None or df.empty:
            continue
        cl = {c.lower(): c for c in df.columns}
        grp_bounds = {}
        vert_keys = ['height', 'ght', 'altitude', 'elev', 'pres', 'pressure', 'p']
        for key in vert_keys:
            if key not in cl:
                continue
            col = cl[key]
            is_pres = key in ['pres', 'pressure', 'p']
            raw = df[col].dropna().values
            if len(raw) == 0:
                continue
            # Check units for Pa→hPa conversion
            unit = decode_metadata(
                data_pack['var_attrs'].get(grp, {}).get(col, {}).get('units', '')
            )
            convert = 'Pa' in unit and 'hPa' not in unit
            vals = raw / 100.0 if convert else raw.copy()
            display_unit = 'hPa' if convert else unit

            if is_pres or convert:
                zmin = float(max(0.0, math.floor(np.nanmin(vals) / 50.0) * 50.0))
                raw_max = float(np.nanmax(vals))
                zmax = float(math.ceil(raw_max / 5.0) * 5.0 + 5.0)
                zmax = max(zmax, zmin + 50.0)
                step = 5.0
            else:
                zmin = 0.0
                zmax = float(math.ceil(np.nanmax(vals) / 1000.0) * 1000.0)
                if zmax == 0.0:
                    zmax = 1000.0
                step = 10.0

            if zmin >= zmax:
                zmax = zmin + step

            grp_bounds[col] = (zmin, zmax, is_pres or convert, display_unit, step)
        if grp_bounds:
            bounds[grp] = grp_bounds
    data_pack['vert_bounds'] = bounds


# ---------------------------------------------------------------------------
# Section renderers — each handles one sidebar container
# ---------------------------------------------------------------------------

_VIEWER_STATE_KEYS = [
    'v_sel_group', 'v_variable', 'v_use_filter', 'v_vert_coord',
    'v_lvl_range', 'v_is_3d', 'v_3d_z', 'v_plot_track', 'v_sel_plat',
    'v_3d_ratio', 'v_apply_thinning', 'v_thin_pct', 'v_marker_size',
    'v_lat_range', 'v_lon_range', 'v_time_range', 'v_show_cen', 'v_cen_mode',
    'v_clat', 'v_clon', 'v_track_proj', 'v_vert_range', 'v_color_scale',
    'v_plot_err', 'v_vec_scale', 'v_show_basemap',
    'v_plot_type', 'v_sr_up',
]


def render_file_upload_section(data_pack_key, filename_key, state_keys, state_dict_key):
    """Renders the file upload container and returns the (possibly new) data_pack."""
    data_pack = st.session_state.get(data_pack_key)
    
    # Check cross-tab inheritance
    other_data_key = 'data_pack_analysis' if data_pack_key == 'data_pack' else 'data_pack'
    other_file_key = 'last_uploaded_filename_analysis' if filename_key == 'last_uploaded_filename' else 'last_uploaded_filename'
    
    # If this tab is empty, the other tab has a file, AND we haven't explicitly cleared this tab
    if data_pack is None and st.session_state.get(other_data_key) is not None and not st.session_state.get(f"cleared_{data_pack_key}"):
        st.session_state[data_pack_key] = st.session_state[other_data_key]
        st.session_state[filename_key] = st.session_state[other_file_key]
        data_pack = st.session_state[data_pack_key]

    with st.sidebar.container(border=True):
        st.markdown("### 📁 File Upload")

        if data_pack is None:
            uploaded_file = st.file_uploader(
                "Upload an AI-Ready HDF5 file",
                type=['h5', 'hdf5'],
                label_visibility="collapsed",
                key=f"uploader_{data_pack_key}"
            )
            if uploaded_file is not None:
                if st.session_state.get(filename_key) != uploaded_file.name:
                    with st.spinner("Processing HDF5..."):
                        try:
                            raw_data_pack = load_data_from_h5(uploaded_file.getvalue())
                            _inject_derived_fields(raw_data_pack)
                            _compute_global_domain(raw_data_pack)
                            _compute_vert_bounds(raw_data_pack)
                            st.session_state[data_pack_key] = raw_data_pack
                            st.session_state[filename_key] = uploaded_file.name
                            
                            # Clear the "cleared" flags so the other tab can inherit this new file
                            st.session_state.pop('cleared_data_pack', None)
                            st.session_state.pop('cleared_data_pack_analysis', None)
                            
                            for k in state_keys:
                                if k in st.session_state:
                                    del st.session_state[k]
                            st.session_state[state_dict_key] = {}
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to load file: {e}")
                            st.stop()
        else:
            st.success(f"📂 **File Loaded to Memory:**\n{st.session_state.get(filename_key, 'Unknown')}")
            if st.button("🗑️ Clear Memory & Upload New File", key=f"clear_{data_pack_key}"):
                del st.session_state[data_pack_key]
                if filename_key in st.session_state:
                    del st.session_state[filename_key]
                st.session_state[state_dict_key] = {}
                st.session_state[f"cleared_{data_pack_key}"] = True # Prevent auto-inheriting immediately
                st.rerun()

        # Inventory expanders (only when a file is loaded)
        current_pack = st.session_state.get(data_pack_key)
        if current_pack is not None:
            with st.expander("🗂️ View Current File Inventory", expanded=False):
                inventory_html = f"<div style='font-size: {FS_BODY}px; line-height: 1.6; padding: 5px;'>"
                for g in EXPECTED_GROUPS:
                    if g in current_pack['data']:
                        inventory_html += f"<span style='color: {CLR_SUCCESS};'>✅ <b>{g}</b></span><br>"
                    else:
                        inventory_html += f"<span style='color: {CLR_MUTED};'>❌ <i>{g}</i></span><br>"
                for g in [g for g in current_pack['data'].keys() if g not in EXPECTED_GROUPS]:
                    inventory_html += f"<span style='color: {CLR_EXTRA};'>⚠️ <b>{g} (Extra)</b></span><br>"
                inventory_html += "</div>"
                st.markdown(inventory_html, unsafe_allow_html=True)

            with st.expander("📊 View Global Metadata Inventory", expanded=False):
                meta_html = (
                    f"<table style='font-size: {FS_TABLE}px; width: 100%; text-align: left; "
                    "border-collapse: collapse;'>"
                    "<tr style='border-bottom: 2px solid #ddd;'>"
                    "<th style='padding: 8px;'>Field</th>"
                    "<th style='padding: 8px;'>Value</th></tr>"
                )
                for m in EXPECTED_META:
                    if m in current_pack['meta']['info']:
                        val = decode_metadata(current_pack['meta']['info'][m])
                        meta_html += (
                            f"<tr><td style='padding: 6px;'><b>{m}</b></td>"
                            f"<td style='padding: 6px; color: green;'>{val}</td></tr>"
                        )
                    else:
                        meta_html += (
                            f"<tr><td style='padding: 6px; color: gray;'>{m}</td>"
                            f"<td style='padding: 6px; color: red;'>❌ Missing</td></tr>"
                        )
                for m in [k for k in current_pack['meta']['info'].keys()
                          if k not in EXPECTED_META]:
                    val = decode_metadata(current_pack['meta']['info'][m])
                    meta_html += (
                        f"<tr><td style='padding: 6px; color: blue;'>"
                        f"<i>{m} (Extra)</i></td>"
                        f"<td style='padding: 6px; color: blue;'>{val}</td></tr>"
                    )
                meta_html += "</table>"
                st.markdown(meta_html, unsafe_allow_html=True)

    return st.session_state.get(data_pack_key)


def _render_variable_section(data_pack, plotter, plot_type="Horizontal Cartesian"):
    """Renders group + variable selector. Returns (sel_group, variable, plot_var, color_scale, h_col, p_col)."""

    available_groups = sorted(list(data_pack['data'].keys()))

    if ('v_sel_group' not in st.session_state or
            st.session_state.v_sel_group not in available_groups):
        st.session_state.v_sel_group = available_groups[0] if available_groups else None

    def reset_group_dependencies():
        st.session_state.v_apply_thinning = False
        st.session_state.v_thin_pct = 50
        if 'show_auto_thin_msg' in st.session_state:
            st.session_state.show_auto_thin_msg = False
        for k in ['v_lvl_range', 'v_time_range', 'v_last_coord',
                  'v_vert_range', 'v_plot_err', 'v_vec_scale', '_last_dom_z_col']:
            if k in st.session_state:
                del st.session_state[k]

    def reset_var_dependencies():
        if 'v_plot_err' in st.session_state:
            del st.session_state['v_plot_err']

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
            h_col = next((cols_lower[c] for c in ['height', 'ght', 'altitude', 'elev']
                          if c in cols_lower), None)
            p_col = next((cols_lower[c] for c in ['pres', 'pressure', 'p']
                          if c in cols_lower), None)
        elif sel_group in data_pack['data']:
            # Track groups have clat/clon instead of lat/lon — load them so
            # domain auto-fit, time section, and variable coloring all work
            df_sel     = data_pack['data'][sel_group]
            cols_lower = {c.lower(): c for c in df_sel.columns}

        exclude_col = (st.session_state.get('v_vert_coord')
                       if st.session_state.get('v_use_filter') else None)

        # Determine rh_z_col from session state (widget rendered after plot type section)
        rh_z_col = None
        if plot_type == "Radial-Height Profile":
            rh_z_options = [c for c in [h_col, p_col] if c]
            if rh_z_options:
                if ('v_rh_z_col' not in st.session_state or
                        st.session_state.v_rh_z_col not in rh_z_options):
                    st.session_state.v_rh_z_col = rh_z_options[0]
                rh_z_col = st.session_state.v_rh_z_col

        vars_list   = plotter.get_plottable_variables(
            sel_group,
            active_z_col=exclude_col or rh_z_col,
            exclude_vectors=True
        )

        variable = plot_var = color_scale = None

        if vars_list:
            if ('v_variable' not in st.session_state or
                    st.session_state.v_variable not in vars_list):
                st.session_state.v_variable = vars_list[0]

            v_c1, v_c2 = st.columns([1.6, 1])
            with v_c1:
                variable = st.selectbox(
                    "Variable", vars_list,
                    key='v_variable',
                    on_change=reset_var_dependencies,
                    format_func=lambda x: plotter._get_var_display_name(sel_group, x)
                )
            with v_c2:
                if 'v_color_scale' not in st.session_state:
                    st.session_state.v_color_scale = "Linear scale"
                color_scale = st.selectbox(
                    "Plot on:", ["Linear scale", "Log scale"],
                    key='v_color_scale'
                )
            
            plot_var  = variable
            var_lower = variable.lower()

            err_candidates = [f"{var_lower}err", f"{var_lower}_err",
                              f"{var_lower}_error", f"{var_lower}error"]
            actual_err_col = next(
                (cols_lower[c] for c in err_candidates if c in cols_lower), None
            )
            err_lbl = "Plot Error (Computed)" if "_comp" in var_lower else "Plot Error"

            if actual_err_col:
                err_vals = df_sel[actual_err_col].dropna().values
                if len(err_vals) == 0:
                    st.checkbox(err_lbl, disabled=True, value=False,
                                key=f"err_na_{variable}")
                else:
                    e_min, e_max = float(np.min(err_vals)), float(np.max(err_vals))
                    if np.isclose(e_min, e_max, rtol=1e-5, atol=1e-8):
                        e_unit = decode_metadata(
                            data_pack['var_attrs']
                            .get(sel_group, {})
                            .get(actual_err_col, {})
                            .get('units', '')
                        )
                        unit_str = f" {e_unit}" if e_unit else ""
                        st.checkbox(
                            f"{err_lbl} (Constant at {e_min:g}{unit_str})",
                            disabled=True, value=False,
                            key=f"err_const_{variable}"
                        )
                    else:
                        if 'v_plot_err' not in st.session_state:
                            st.session_state.v_plot_err = False
                        if st.checkbox(err_lbl, key='v_plot_err'):
                            plot_var = actual_err_col
            else:
                st.checkbox(err_lbl, disabled=True, value=False,
                            key=f"err_miss_{variable}")
        else:
            st.stop()

    return sel_group, variable, plot_var, color_scale, h_col, p_col, df_sel, cols_lower, rh_z_col


def _render_plot_type_section(data_pack, sel_group, is_3d, h_col=None, p_col=None, plotter=None):
    """Renders the Plot Type container.
    Returns (plot_type, sr_up_convention, sr_track_grp)."""

    # Determine track availability for SR / RH
    _sr_grp = None
    if 'track_spline_track' in data_pack['data'] and \
            len(data_pack['data']['track_spline_track']) >= 2:
        _sr_grp = 'track_spline_track'
    elif 'track_best_track' in data_pack['data'] and \
            len(data_pack['data']['track_best_track']) >= 2:
        _sr_grp = 'track_best_track'

    _sr_available = (_sr_grp is not None and
                     'TRACK' not in sel_group.upper() and
                     not is_3d)

    _PLOT_TYPES = ["Horizontal Cartesian", "Horizontal Storm-Relative", "Radial-Height Profile"]

    # Auto-reset to Cartesian when SR/RH becomes unavailable
    if 'v_plot_type' not in st.session_state:
        st.session_state.v_plot_type = "Horizontal Cartesian"
    if not _sr_available and st.session_state.v_plot_type in (
            "Horizontal Storm-Relative", "Radial-Height Profile"):
        st.session_state.v_plot_type = "Horizontal Cartesian"

    # SR mode requires storm center — force it before the Storm Center widget renders
    if st.session_state.v_plot_type == "Horizontal Storm-Relative":
        st.session_state.v_show_cen = True
    # RH mode: storm center not relevant — uncheck and leave it off
    if st.session_state.v_plot_type == "Radial-Height Profile":
        st.session_state.v_show_cen = False

    with st.sidebar.container(border=True):
        st.markdown("### 🧭 Plot Type")

        plot_type = st.selectbox(
            "Plot Type",
            _PLOT_TYPES,
            key='v_plot_type',
            disabled=False,
            label_visibility="collapsed",
            help="Storm-Relative and Radial-Height Profile require track_spline_track or "
                 "track_best_track (≥2 points). Unavailable in 3D mode."
        )

        is_sr  = (plot_type == "Horizontal Storm-Relative")
        is_rh  = (plot_type == "Radial-Height Profile")

        if not _sr_available and st.session_state.v_plot_type == "Horizontal Cartesian":
            if is_3d:
                st.caption("ℹ️ Storm-Relative / Radial-Height unavailable in 3D mode.")
            elif 'TRACK' in sel_group.upper():
                st.caption("ℹ️ Storm-Relative / Radial-Height unavailable for track groups.")
            elif _sr_grp is None:
                st.caption("ℹ️ Storm-Relative / Radial-Height requires a spline or best track group.")

        if 'v_sr_up' not in st.session_state:
            st.session_state.v_sr_up = "Relative to North"

        sub_c1, sub_c2 = st.columns([1.1, 1.3])
        if is_sr:
            with sub_c1:
                sidebar_label("Upward Direction Represents:", enabled=True, size='label')
            with sub_c2:
                sr_up_convention = st.selectbox(
                    "Up direction",
                    ["Relative to North", "Relative to Storm Motion"],
                    key='v_sr_up',
                    disabled=False,
                    label_visibility="collapsed"
                )
            rh_z_col = None
        elif is_rh:
            rh_z_options = [c for c in [h_col, p_col] if c]
            if ('v_rh_z_col' not in st.session_state or
                    st.session_state.get('v_rh_z_col') not in rh_z_options):
                st.session_state.v_rh_z_col = rh_z_options[0] if rh_z_options else None
            with sub_c1:
                sidebar_label("Plot on Z axis:", enabled=bool(rh_z_options), size='label')
            with sub_c2:
                if rh_z_options and plotter:
                    rh_z_col = st.selectbox(
                        "RH Z axis", rh_z_options, key='v_rh_z_col',
                        disabled=False, label_visibility="collapsed",
                        format_func=lambda x: plotter._get_var_display_name(sel_group, x)
                    )
                else:
                    rh_z_col = st.session_state.get('v_rh_z_col')
            sr_up_convention = st.session_state.get('v_sr_up', "Relative to North")
        else:
            # Horizontal Cartesian — hide both sub-controls
            sr_up_convention = st.session_state.get('v_sr_up', "Relative to North")
            rh_z_col = None

    return plot_type, sr_up_convention, _sr_grp, rh_z_col


def _render_plotting_options(data_pack, sel_group, h_col, p_col,
                              df_sel, cols_lower, plot_var, plot_type="Horizontal Cartesian"):
    """Renders thinning, level filter, flight track, 3D, marker size controls.
    Returns (show_cen, cen_mode, apply_thinning, thin_pct, z_con, target_col,
             target_col_3d, track_mapping, plot_track, selected_platform, track_proj,
             is_3d, plot_z_col, z_ratio, marker_sz, vec_scale, can_do_3d)."""

    with st.sidebar.container(border=True):
        st.markdown("### ⚙️ Plotting Options")

        is_rh  = (plot_type == "Radial-Height Profile")
        is_sr  = (plot_type == "Horizontal Storm-Relative")

        if 'v_show_cen' not in st.session_state:
            st.session_state.v_show_cen = True
        if 'v_cen_mode' not in st.session_state:
            st.session_state.v_cen_mode = "Display Location Only"

        # RH mode: force storm center off
        if is_rh:
            st.session_state.v_show_cen = False

        c_cen1, c_cen2 = st.columns([1, 1.5])
        with c_cen1:
            spacer('sm')
            show_cen = st.checkbox("Storm Center", key='v_show_cen', disabled=is_rh)
        with c_cen2:
            cen_mode = st.selectbox(
                "Center Mode", 
                ["Display Location Only", "Display As Motion Vector"], 
                key='v_cen_mode', 
                disabled=not show_cen or is_rh, 
                label_visibility="collapsed"
            )

        # --- MAP UNDERLAY LOGIC ---
        is_3d_state = st.session_state.get('v_is_3d', False)
        disable_map = is_3d_state or is_sr or is_rh

        if disable_map and st.session_state.get('v_show_basemap', False):
            st.session_state.v_show_basemap = False

        if 'v_show_basemap' not in st.session_state:
            st.session_state.v_show_basemap = False
            
        show_basemap = st.checkbox("Show Map Underlay", key='v_show_basemap', disabled=disable_map)
        
        # Display the appropriate info caption
        if is_3d_state:
            st.caption("ℹ️ Map underlay is disabled in 3D mode.")
        elif is_sr:
            st.caption("ℹ️ Map underlay is disabled in Storm-Relative mode.")
        elif is_rh:
            st.caption("ℹ️ Map underlay is disabled in Radial-Height mode.")
            
        section_divider()

        # Auto-thinning override from previous rerun
        if st.session_state.pop('_force_thinning', False):
            st.session_state.v_apply_thinning = True
            st.session_state.v_thin_pct = st.session_state.pop('_force_thin_pct', 50)

        if 'v_apply_thinning' not in st.session_state:
            st.session_state.v_apply_thinning = False
        apply_thinning = st.checkbox("Apply thinning?", key='v_apply_thinning')

        thin_color = "inherit" if apply_thinning else CLR_MUTED
        t_c1, t_c2, t_c3 = st.columns([0.8, 2.8, 1.2])
        with t_c1:
            st.markdown(
                f"<div style='margin-top: 6px; font-size: {FS_BODY}px; font-weight: 500; "
                f"color:{thin_color}; text-align:right;'>Show</div>",
                unsafe_allow_html=True
            )
        with t_c2:
            if 'v_thin_pct' not in st.session_state:
                st.session_state.v_thin_pct = 50
            thin_pct = st.slider(
                "Thinning", min_value=5, max_value=100, step=5,
                key='v_thin_pct', disabled=not apply_thinning,
                label_visibility="collapsed"
            )
        with t_c3:
            st.markdown(
                f"<div style='margin-top: 6px; font-size: {FS_BODY}px; font-weight: 500; "
                f"color:{thin_color};'>% of obs.</div>",
                unsafe_allow_html=True
            )

        section_divider()

        # Level filter — disabled entirely in RH mode (height is the Y axis)
        z_con       = None
        target_col  = None
        options     = [c for c in [h_col, p_col] if c]

        if is_rh and st.session_state.get('v_use_filter', False):
            st.session_state.v_use_filter = False
        if not options and st.session_state.get('v_use_filter', False):
            st.session_state.v_use_filter = False
        if 'v_use_filter' not in st.session_state:
            st.session_state.v_use_filter = False
        use_filter = st.checkbox("Filter by Level?", key='v_use_filter',
                                  disabled=not options or is_rh)
        f_color = "inherit" if use_filter else CLR_MUTED

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
                target_col = st.selectbox(
                    "VCoord", options, key='v_vert_coord',
                    disabled=not use_filter, label_visibility="collapsed",
                    format_func=_fmt_vert
                )
            v_unit  = decode_metadata(
                data_pack['var_attrs'].get(sel_group, {})
                .get(target_col, {}).get('units', '')
            )
            convert = 'Pa' in v_unit and 'hPa' not in v_unit
            if convert:
                v_unit = 'hPa'

            raw_vals = df_sel[target_col].dropna().values
            if len(raw_vals) > 0:
                if convert:
                    raw_vals = raw_vals / 100.0
                dmin, dmax = float(np.nanmin(raw_vals)), float(np.nanmax(raw_vals))
                if dmin == dmax:
                    dmax = dmin + 1.0
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
                        if c_min > c_max:
                            c_min = c_max
                        st.session_state.v_lvl_range = (c_min, c_max)

                    lvl_range = st.slider(
                        "Range", min_value=dmin, max_value=dmax,
                        key='v_lvl_range', disabled=not use_filter,
                        label_visibility="collapsed"
                    )
                if use_filter:
                    z_con = {
                        'col': target_col,
                        'val': (lvl_range[1] + lvl_range[0]) / 2.0,
                        'tol': abs(lvl_range[1] - lvl_range[0]) / 2.0,
                        'convert_pa_to_hpa': convert
                    }

        section_divider()

        # Flight track overlay
        available_groups  = sorted(list(data_pack['data'].keys()))
        flight_track_grps = [g for g in available_groups
                              if g.lower().startswith('flight_level_hdobs')]
        track_mapping     = {g.split('_')[-1].upper(): g for g in flight_track_grps}

        track_col1, track_col2 = st.columns([1.1, 1])
        with track_col1:
            spacer('sm')
            if 'v_plot_track' not in st.session_state:
                st.session_state.v_plot_track = False
            plot_track = st.checkbox(
                "Plot flight track from:", key='v_plot_track',
                disabled=(len(track_mapping) == 0)
            )
        with track_col2:
            if ('v_sel_plat' not in st.session_state or
                    st.session_state.v_sel_plat not in track_mapping):
                st.session_state.v_sel_plat = (
                    list(track_mapping.keys())[0] if track_mapping else None
                )
            selected_platform = (
                st.selectbox(
                    "Platform", list(track_mapping.keys()),
                    key='v_sel_plat', disabled=not plot_track,
                    label_visibility="collapsed"
                ) if track_mapping else None
            )

        p_c1, p_c2 = st.columns([1.4, 1])
        with p_c1:
            is_3d_state   = st.session_state.get('v_is_3d', False)
            if is_rh:
                # RH: projection is always "Show" when track is checked — no choice needed
                proj_disabled = True
            else:
                proj_disabled = not (plot_track and is_3d_state)
            p_color       = "inherit" if not proj_disabled else CLR_MUTED
            st.markdown(
                f"<div style='margin-top: 8px; font-size: {FS_BODY}px; font-weight: 500; "
                f"color: {p_color};'>Display track projection:</div>",
                unsafe_allow_html=True
            )
        with p_c2:
            if 'v_track_proj' not in st.session_state:
                st.session_state.v_track_proj = "Bottom Only"
            if is_rh:
                # Force to "Show" whenever track is checked; "None" when unchecked
                st.session_state.v_track_proj = "Show" if plot_track else "None"
                proj_options = ["Show"] if plot_track else ["None"]
            else:
                proj_options = ["None", "Bottom Only", "Sides Only", "Bottom + Sides"]
                if st.session_state.v_track_proj not in proj_options:
                    st.session_state.v_track_proj = proj_options[0]
            track_proj = st.selectbox(
                "Projection",
                proj_options,
                key='v_track_proj', disabled=proj_disabled,
                label_visibility="collapsed"
            )

        section_divider()

        # 3D toggle — disabled in RH mode
        can_do_3d = (h_col is not None or p_col is not None) and not is_rh
        if (not can_do_3d or is_rh) and st.session_state.get('v_is_3d', False):
            st.session_state.v_is_3d = False

        c3d_1, c3d_2 = st.columns([1.1, 1])
        with c3d_1:
            spacer('sm')
            if 'v_is_3d' not in st.session_state:
                st.session_state.v_is_3d = False
            is_3d = st.checkbox("3D view with z axis:", key='v_is_3d',
                                 disabled=not can_do_3d)
        with c3d_2:
            options_3d = options if options else ["None"]
            if st.session_state.get('v_3d_z') not in options_3d:
                st.session_state.v_3d_z = options_3d[0]
            target_col_3d = st.selectbox(
                "Select 3D Z-Axis", options_3d, key='v_3d_z',
                label_visibility="collapsed", disabled=not is_3d
            )

        plot_z_col = target_col if use_filter else (target_col_3d if options else None)

        r1, r2 = st.columns([1.1, 2.2])
        with r1:
            sidebar_label("Vert. Aspect Ratio:", enabled=is_3d)
        with r2:
            if 'v_3d_ratio' not in st.session_state:
                st.session_state.v_3d_ratio = 0.3
            z_ratio = st.slider(
                "VAR", min_value=0.05, max_value=1.5, step=0.05,
                key='v_3d_ratio', disabled=not is_3d,
                label_visibility="collapsed"
            )

        section_divider()

        # Marker size / vector scale
        m1, m2    = st.columns([1.1, 2.2])
        is_vector = plot_var and "wind_vec" in plot_var.lower()
        with m1:
            lbl = "Vector Scale:" if is_vector else "Marker Size:"
            sidebar_label(lbl, size='label')
        with m2:
            if is_vector:
                if 'v_vec_scale' not in st.session_state:
                    st.session_state.v_vec_scale = 1.0
                vec_scale = st.slider(
                    "Vector Scale", min_value=0.1, max_value=5.0, step=0.1,
                    key='v_vec_scale', label_visibility="collapsed"
                )
                marker_sz = 100
            else:
                if ('v_marker_size' not in st.session_state or
                        not (10 <= st.session_state.v_marker_size <= 200)):
                    st.session_state.v_marker_size = 100
                marker_sz = st.slider(
                    "Marker Size", min_value=10, max_value=200, step=10,
                    format="%d%%", key='v_marker_size',
                    label_visibility="collapsed"
                )
                vec_scale = 1.0

    return (show_cen, cen_mode, apply_thinning, thin_pct, z_con, target_col,
            target_col_3d, track_mapping, plot_track, selected_platform,
            track_proj, is_3d, plot_z_col, z_ratio, marker_sz, vec_scale,
            can_do_3d)


def _render_domain_section(data_pack, sel_group, df_sel, options,
                            target_col, target_col_3d, is_3d,
                            default_lat_min, default_lat_max,
                            default_lon_min, default_lon_max,
                            plot_type="Horizontal Cartesian",
                            sr_track_grp=None, plotter=None, rh_z_col=None):
    """Renders domain limit sliders + auto-fit / reset buttons.
    Returns (domain_bounds, convert_dom, vert_range, domain_z_col)."""

    is_sr = (plot_type == "Horizontal Storm-Relative")
    is_rh = (plot_type == "Radial-Height Profile")
    # Both SR and RH modes use a max-range slider rather than lat/lon sliders
    use_range_slider = is_sr or is_rh

    with st.sidebar.container(border=True):
        st.markdown("### 🗺️ Plot Domain Limits")

        # Compute global domain lazily if missing
        if 'global_domain' not in data_pack:
            _compute_global_domain(data_pack)
        _gd = data_pack.get('global_domain')
        _gd_lat = (_gd['lat_min'], _gd['lat_max']) if _gd else (default_lat_min, default_lat_max)
        _gd_lon = (_gd['lon_min'], _gd['lon_max']) if _gd else (default_lon_min, default_lon_max)

        if st.session_state.pop('_force_domain_fit', False):
            if '_force_lat_range' in st.session_state and '_force_lon_range' in st.session_state:
                forced_lat = st.session_state.pop('_force_lat_range')
                forced_lon = st.session_state.pop('_force_lon_range')
                # Clamp to slider bounds so Streamlit accepts the value
                s_lat_min = st.session_state.get('_slider_lat_bounds', (_gd_lat[0], _gd_lat[1]))[0]
                s_lat_max = st.session_state.get('_slider_lat_bounds', (_gd_lat[0], _gd_lat[1]))[1]
                s_lon_min = st.session_state.get('_slider_lon_bounds', (_gd_lon[0], _gd_lon[1]))[0]
                s_lon_max = st.session_state.get('_slider_lon_bounds', (_gd_lon[0], _gd_lon[1]))[1]
                st.session_state.v_lat_range = (
                    max(s_lat_min, min(forced_lat[0], s_lat_max)),
                    max(s_lat_min, min(forced_lat[1], s_lat_max))
                )
                st.session_state.v_lon_range = (
                    max(s_lon_min, min(forced_lon[0], s_lon_max)),
                    max(s_lon_min, min(forced_lon[1], s_lon_max))
                )
            if '_force_z_range' in st.session_state:
                st.session_state.v_vert_range = st.session_state.pop('_force_z_range')
        if st.session_state.pop('_reset_z_range', False):
            if 'v_vert_range' in st.session_state:
                del st.session_state['v_vert_range']

        if use_range_slider:
            # SR / RH mode: Max Range (km) slider instead of lat/lon sliders
            sr_default_max = 500.0
            if plotter is not None and sr_track_grp:
                try:
                    sr_default_max = plotter.get_sr_max_range(sel_group, sr_track_grp)
                except Exception as e:
                    st.warning(f"SR range error: {type(e).__name__}: {e}")

            # Snap the slider's absolute limit to the true max range of the data
            sr_slider_max = max(sr_default_max, 25.0)

            # Apply any pending forced value BEFORE the widget is instantiated
            if '_force_sr_max_range' in st.session_state:
                st.session_state.v_sr_max_range = st.session_state.pop('_force_sr_max_range')

            # Reset to data-driven default when the group changes, or if forced-cleared
            if st.session_state.get('_sr_last_group') != sel_group:
                st.session_state.v_sr_max_range = sr_default_max
                st.session_state['_sr_last_group'] = sel_group
            elif 'v_sr_max_range' not in st.session_state:
                st.session_state.v_sr_max_range = sr_default_max
            else:
                # Clamp to valid slider bounds
                st.session_state.v_sr_max_range = float(np.clip(
                    st.session_state.v_sr_max_range, 25.0, sr_slider_max
                ))

            c1, c2 = st.columns([0.7, 2.0])
            with c1:
                sidebar_label('Max Range:', size='label')
            with c2:
                sr_max_range = st.slider(
                    "Max Range (km)",
                    min_value=25.0, max_value=float(sr_slider_max),
                    step=25.0, key='v_sr_max_range',
                    label_visibility="collapsed"
                )

            # Build a dummy domain_bounds with no lat/lon filtering for SR
            domain_bounds = {
                'lat_min': -90.0, 'lat_max': 90.0,
                'lon_min': -180.0, 'lon_max': 180.0,
                '_sr_max_range_km': sr_max_range,
            }
            lat_range = (_gd_lat[0], _gd_lat[1])
            lon_range = (_gd_lon[0], _gd_lon[1])

        else:
            c1, c2, c3, c4 = st.columns([0.7, 2.0, 0.7, 2.0])
            with c1:
                sidebar_label('Lat:', size='label')
            with c2:
                _s_lat_min, _s_lat_max = st.session_state.get(
                    '_slider_lat_bounds', (_gd_lat[0], _gd_lat[1]))
                if 'v_lat_range' not in st.session_state:
                    st.session_state.v_lat_range = _gd_lat
                lat_range = st.slider(
                    "Latitude Limits",
                    min_value=_s_lat_min, max_value=_s_lat_max,
                    key='v_lat_range', step=0.1,
                    label_visibility="collapsed"
                )
            with c3:
                sidebar_label('Lon:', size='label')
            with c4:
                _s_lon_min, _s_lon_max = st.session_state.get(
                    '_slider_lon_bounds', (_gd_lon[0], _gd_lon[1]))
                if 'v_lon_range' not in st.session_state:
                    st.session_state.v_lon_range = _gd_lon
                lon_range = st.slider(
                    "Longitude Limits",
                    min_value=_s_lon_min, max_value=_s_lon_max,
                    key='v_lon_range', step=0.1,
                    label_visibility="collapsed"
                )

            domain_bounds = {
                'lat_min': lat_range[0], 'lat_max': lat_range[1],
                'lon_min': lon_range[0], 'lon_max': lon_range[1],
            }

        vert_range  = None
        convert_dom = False
        # Always track whichever vertical coord the user has selected —
        # v_vert_coord drives both the level filter and the domain vertical slider.
        if is_rh and rh_z_col:
            domain_z_col = rh_z_col
        else:
            domain_z_col = st.session_state.get('v_vert_coord') or (target_col if target_col else target_col_3d)

        if options and df_sel is not None:
            # Ensure vert_bounds are available (lazy fallback for older sessions)
            if 'vert_bounds' not in data_pack:
                _compute_vert_bounds(data_pack)

            grp_vb   = data_pack.get('vert_bounds', {}).get(sel_group, {})
            col_vb   = grp_vb.get(domain_z_col)  # (zmin, zmax, is_pres, unit, step)

            if col_vb:
                zmin_global, zmax_global, is_pres, v_unit_dom, slider_step = col_vb
                convert_dom = is_pres and any(
                    p in domain_z_col.lower() for p in ['pres', 'pressure', 'p']
                ) and data_pack['var_attrs'].get(sel_group, {}).get(
                    domain_z_col, {}).get('units', '').strip() not in ('hPa', '')
            else:
                # Fallback: compute inline
                v_unit_dom = decode_metadata(
                    data_pack['var_attrs'].get(sel_group, {})
                    .get(domain_z_col, {}).get('units', ''))
                convert_dom = 'Pa' in v_unit_dom and 'hPa' not in v_unit_dom
                if convert_dom:
                    v_unit_dom = 'hPa'
                vert_vals = df_sel[domain_z_col].dropna().values
                if convert_dom:
                    vert_vals = vert_vals / 100.0
                is_pres = convert_dom or any(
                    p in domain_z_col.lower() for p in ['pres', 'pressure', 'p'])
                if is_pres:
                    zmin_global = float(max(0.0, math.floor(np.nanmin(vert_vals) / 50.0) * 50.0))
                    raw_max = float(np.nanmax(vert_vals))
                    zmax_global = float(math.ceil(raw_max / 5.0) * 5.0 + 5.0)
                    zmax_global = max(zmax_global, zmin_global + 50.0)
                    slider_step = 5.0
                else:
                    zmin_global = 0.0
                    zmax_global = float(math.ceil(np.nanmax(vert_vals) / 1000.0) * 1000.0)
                    if zmax_global == 0.0:
                        zmax_global = 1000.0
                    slider_step = 10.0
                if zmin_global >= zmax_global:
                    zmax_global = zmin_global + slider_step

            # Reset slider state when the z column changes
            if st.session_state.get('_last_dom_z_col') != domain_z_col:
                st.session_state.v_vert_range       = (zmin_global, zmax_global)
                st.session_state['_last_dom_z_col'] = domain_z_col
                st.rerun()
            elif 'v_vert_range' not in st.session_state:
                st.session_state.v_vert_range = (zmin_global, zmax_global)
            else:
                c_min, c_max = st.session_state.v_vert_range
                c_min = max(zmin_global, min(c_min, zmax_global))
                c_max = max(zmin_global, min(c_max, zmax_global))
                if c_min > c_max:
                    c_min = c_max
                st.session_state.v_vert_range = (c_min, c_max)

            v1, v2 = st.columns([1.0, 2.2])
            with v1:
                sidebar_label(f'Vert ({v_unit_dom}):', enabled=True, size='label')
            with v2:
                vert_range_ui = st.slider(
                    "Vertical Limits",
                    min_value=zmin_global, max_value=zmax_global,
                    key='v_vert_range', step=slider_step,
                    label_visibility="collapsed"
                )

                vert_range = vert_range_ui
                domain_bounds['z_min']     = vert_range[0]
                domain_bounds['z_max']     = vert_range[1]
                domain_bounds['z_col']     = domain_z_col
                domain_bounds['z_convert'] = convert_dom

        b1, b2 = st.columns(2)

        b1.markdown('<div class="light-btn-marker" style="display:none;"></div>', unsafe_allow_html=True)

        with b1:
            if st.button("🔍 Auto-fit domain", width="stretch"):
                if use_range_slider:
                    if plotter is not None and sr_track_grp:
                        try:
                            temp_df = df_sel.copy()
                            time_col_sr = next(
                                (c for c in temp_df.columns
                                 if c.lower() in ['time', 'date', 'datetime', 'epoch']), None
                            )
                            if time_col_sr and 'v_time_range' in st.session_state:
                                try:
                                    t_min_dt, t_max_dt = st.session_state.v_time_range
                                    t_min_f = float(t_min_dt.strftime("%Y%m%d%H%M%S"))
                                    t_max_f = float(t_max_dt.strftime("%Y%m%d%H%M%S"))
                                    temp_df = temp_df[
                                        (temp_df[time_col_sr] >= t_min_f) &
                                        (temp_df[time_col_sr] <= t_max_f)
                                    ]
                                except Exception:
                                    pass

                            if temp_df.empty:
                                st.toast("⚠️ No data in current time window to fit.", icon="⚠️")
                            else:
                                fitted_max = plotter.get_sr_max_range(
                                    sel_group, sr_track_grp, df_override=temp_df
                                )
                                st.session_state._force_sr_max_range = fitted_max
                                st.rerun()
                        except Exception as e:
                            st.toast(f"⚠️ SR range error: {type(e).__name__}: {e}", icon="⚠️")
                else:
                    if df_sel is None:
                        _fit_df = data_pack['data'].get(sel_group)
                    else:
                        _fit_df = df_sel

                    if _fit_df is None:
                        st.toast("⚠️ No data available to fit.", icon="⚠️")
                    else:
                        temp_df = _fit_df.copy()
                        if (st.session_state.get('v_use_filter') and
                                'v_vert_coord' in st.session_state and
                                'v_lvl_range' in st.session_state):
                            t_col = st.session_state.v_vert_coord
                            if t_col in temp_df.columns:
                                vmin, vmax = st.session_state.v_lvl_range
                                v_unit = decode_metadata(
                                    data_pack['var_attrs'].get(sel_group, {})
                                    .get(t_col, {}).get('units', '')
                                )
                                conv = 'Pa' in v_unit and 'hPa' not in v_unit
                                t_vals = temp_df[t_col] / 100.0 if conv else temp_df[t_col]
                                temp_df = temp_df[(t_vals >= vmin) & (t_vals <= vmax)]

                        time_col = next(
                            (c for c in temp_df.columns
                             if c.lower() in ['time', 'date', 'datetime', 'epoch']), None
                        )
                        is_track_fit = 'TRACK' in sel_group.upper()
                        if not is_track_fit and time_col and 'v_time_range' in st.session_state:
                            try:
                                t_min_dt, t_max_dt = st.session_state.v_time_range
                                t_min_f = float(t_min_dt.strftime("%Y%m%d%H%M%S"))
                                t_max_f = float(t_max_dt.strftime("%Y%m%d%H%M%S"))
                                temp_df = temp_df[
                                    (temp_df[time_col] >= t_min_f) &
                                    (temp_df[time_col] <= t_max_f)
                                ]
                            except Exception:
                                pass

                        cl = {c.lower(): c for c in temp_df.columns}
                        x_c = next((cl[c] for c in ['lon', 'longitude', 'clon'] if c in cl), None)
                        y_c = next((cl[c] for c in ['lat', 'latitude',  'clat'] if c in cl), None)

                        if not x_c or not y_c:
                            st.toast("⚠️ No lat/lon columns found in this group.", icon="⚠️")
                        elif temp_df.empty:
                            st.toast("⚠️ No data remaining after time/level filter.", icon="⚠️")
                        else:
                            a_lat_min = float(temp_df[y_c].min(skipna=True))
                            a_lat_max = float(temp_df[y_c].max(skipna=True))
                            a_lon_min = float(temp_df[x_c].min(skipna=True))
                            a_lon_max = float(temp_df[x_c].max(skipna=True))
                            lat_span  = max(a_lat_max - a_lat_min, 0.05)
                            lon_span  = max(a_lon_max - a_lon_min, 0.05)
                            buf_lat   = lat_span * 0.05
                            buf_lon   = lon_span * 0.05
                            fit_lat_min = a_lat_min - buf_lat
                            fit_lat_max = a_lat_max + buf_lat
                            fit_lon_min = a_lon_min - buf_lon
                            fit_lon_max = a_lon_max + buf_lon
                            fit_lat_span = fit_lat_max - fit_lat_min
                            fit_lon_span = fit_lon_max - fit_lon_min
                            if fit_lat_span > fit_lon_span:
                                extra = (fit_lat_span - fit_lon_span) / 2
                                fit_lon_min -= extra
                                fit_lon_max += extra
                            else:
                                extra = (fit_lon_span - fit_lat_span) / 2
                                fit_lat_min -= extra
                                fit_lat_max += extra

                            if is_track_fit:
                                st.session_state._force_lat_range = (fit_lat_min, fit_lat_max)
                                st.session_state._force_lon_range = (fit_lon_min, fit_lon_max)
                                st.session_state._slider_lat_bounds = (fit_lat_min, fit_lat_max)
                                st.session_state._slider_lon_bounds = (fit_lon_min, fit_lon_max)
                            else:
                                s_lat_min = _gd_lat[0]
                                s_lat_max = _gd_lat[1]
                                s_lon_min = _gd_lon[0]
                                s_lon_max = _gd_lon[1]
                                st.session_state._force_lat_range = (
                                    max(s_lat_min, fit_lat_min),
                                    min(s_lat_max, fit_lat_max)
                                )
                                st.session_state._force_lon_range = (
                                    max(s_lon_min, fit_lon_min),
                                    min(s_lon_max, fit_lon_max)
                                )
                                st.session_state._slider_lat_bounds = (fit_lat_min, fit_lat_max)
                                st.session_state._slider_lon_bounds = (fit_lon_min, fit_lon_max)

                            if (st.session_state.get('v_is_3d') and
                                    domain_z_col and domain_z_col in temp_df.columns):
                                z_vals_fit = temp_df[domain_z_col].dropna()
                                if not z_vals_fit.empty:
                                    v_unit_fit = decode_metadata(
                                        data_pack['var_attrs'].get(sel_group, {})
                                        .get(domain_z_col, {}).get('units', '')
                                    )
                                    conv_fit = 'Pa' in v_unit_fit and 'hPa' not in v_unit_fit
                                    if conv_fit:
                                        z_vals_fit = z_vals_fit / 100.0
                                    a_z_min  = float(z_vals_fit.min())
                                    a_z_max  = float(z_vals_fit.max())
                                    is_pres_fit = conv_fit or any(
                                        p in domain_z_col.lower() for p in ['pres', 'pressure', 'p']
                                    )
                                    if is_pres_fit:
                                        # Small fixed pad at surface (high P), proportional at top
                                        z_span  = max(a_z_max - a_z_min, 1.0)
                                        buf_top = z_span * 0.05   # top of atmosphere side
                                        buf_sfc = 5.0              # surface side — just 5 hPa
                                        st.session_state._force_z_range = (
                                            max(0.0, a_z_min - buf_top),
                                            a_z_max + buf_sfc
                                        )
                                    else:
                                        z_span = max(a_z_max - a_z_min, 1.0)
                                        buf_z  = z_span * 0.05
                                        st.session_state._force_z_range = (
                                            a_z_min - buf_z, a_z_max + buf_z
                                        )
                            st.session_state._force_domain_fit = True
                            st.rerun()

        with b2:
            if st.button("🔄 Reset domain", width="stretch"):
                # Unconditionally wipe all domain bounds so it works reliably in either mode
                st.session_state._force_lat_range = (_gd_lat[0], _gd_lat[1])
                st.session_state._force_lon_range = (_gd_lon[0], _gd_lon[1])
                st.session_state.pop('_slider_lat_bounds', None)
                st.session_state.pop('_slider_lon_bounds', None)
                st.session_state._force_domain_fit = True
                st.session_state._reset_z_range    = True
                
                # Explicitly wipe the SR widget state from both session and persistence dictionaries
                st.session_state.pop('_force_sr_max_range', None)
                if 'v_sr_max_range' in st.session_state:
                    del st.session_state['v_sr_max_range']
                if 'viewer_state' in st.session_state and 'v_sr_max_range' in st.session_state.viewer_state:
                    del st.session_state.viewer_state['v_sr_max_range']
                    
                st.rerun()

    return domain_bounds, convert_dom, vert_range, domain_z_col


def _render_time_section(data_pack, sel_group, df_sel, domain_bounds,
                         plot_type="Horizontal Cartesian",
                         sr_track_grp=None, plotter=None):
    """Renders time slider + auto-fit / reset buttons. Returns time_bounds or None."""

    from datetime import timedelta

    with st.sidebar.container(border=True):
        st.markdown("### ⏱️ Plot Time Limits")

        time_col   = next(
            (c for c in df_sel.columns
             if c.lower() in ['time', 'date', 'datetime', 'epoch']), None
        )
        time_bounds = None

        if not time_col:
            st.info("No time data available for this variable.")
            return None

        valid_mask = df_sel[time_col] > 19000000000000.0
        dt_series  = pd.to_datetime(
            df_sel.loc[valid_mask, time_col]
            .apply(lambda x: f"{x:.0f}" if pd.notna(x) else None),
            format="%Y%m%d%H%M%S", errors='coerce'
        ).dropna()

        if dt_series.empty:
            st.warning("Time column exists, but all values are invalid or corrupted.")
            return None

        data_min_dt    = dt_series.min().to_pydatetime()
        data_max_dt    = dt_series.max().to_pydatetime()

        mission_start = data_min_dt
        mission_end   = data_max_dt

        s_min_dt = data_min_dt
        s_max_dt = data_max_dt

        is_track_grp = 'TRACK' in sel_group.upper()
        default_range = (s_min_dt, s_max_dt)

        # 1. MOVE THESE THREE LINES UP HERE
        _t_bounds = st.session_state.get('_slider_time_bounds')
        _t_slider_min = _t_bounds[0] if _t_bounds else s_min_dt
        _t_slider_max = _t_bounds[1] if _t_bounds else s_max_dt

        # Reset time range when group type changes between track and non-track
        last_grp_was_track = st.session_state.get('_time_last_was_track', None)
        if last_grp_was_track is not None and last_grp_was_track != is_track_grp:
            st.session_state.pop('v_time_range', None)
        st.session_state['_time_last_was_track'] = is_track_grp

        if st.session_state.pop('_force_time_fit', False):
            forced_min, forced_max = st.session_state.pop('_force_time_range')
            forced_min = max(s_min_dt, min(forced_min, s_max_dt))
            forced_max = max(s_min_dt, min(forced_max, s_max_dt))
            if forced_min > forced_max:
                forced_min = forced_max
            st.session_state.pop('v_time_range', None)
            st.session_state._pending_time_range = (forced_min, forced_max)
        elif 'v_time_range' not in st.session_state:
            st.session_state.v_time_range = default_range
        else:
            t_c_min, t_c_max = st.session_state.v_time_range
            
            # 2. FIX CLAMPING: Use _t_slider_min / _t_slider_max instead of s_min_dt / s_max_dt
            t_c_min = max(_t_slider_min, min(t_c_min, _t_slider_max))
            t_c_max = max(_t_slider_min, min(t_c_max, _t_slider_max))
            
            if t_c_min > t_c_max:
                t_c_min = t_c_max
            st.session_state.v_time_range = (t_c_min, t_c_max)

        sidebar_label('Time Range (UTC):', size='label')
        _pending_time = st.session_state.pop('_pending_time_range', None)
        
        if 'v_time_range' not in st.session_state:
            st.session_state.v_time_range = _pending_time if _pending_time else default_range
            
        time_range = st.slider(
            "Time Limits", min_value=_t_slider_min, max_value=_t_slider_max,
            key='v_time_range', format="HH:mm:ss",
            label_visibility="collapsed"
        )

        tb1, tb2 = st.columns(2)

        tb1.markdown('<div class="light-btn-marker" style="display:none;"></div>', unsafe_allow_html=True)

        with tb1:
            if st.button("⏱️ Auto-fit time", width="stretch",
                         key='btn_time_fit'):
                temp_df = df_sel.copy()
                if (st.session_state.get('v_use_filter') and
                        'v_vert_coord' in st.session_state and
                        'v_lvl_range' in st.session_state):
                    t_col = st.session_state.v_vert_coord
                    if t_col in temp_df.columns:
                        vmin, vmax = st.session_state.v_lvl_range
                        v_unit = decode_metadata(
                            data_pack['var_attrs'].get(sel_group, {})
                            .get(t_col, {}).get('units', '')
                        )
                        conv = 'Pa' in v_unit and 'hPa' not in v_unit
                        t_vals  = temp_df[t_col] / 100.0 if conv else temp_df[t_col]
                        temp_df = temp_df[(t_vals >= vmin) & (t_vals <= vmax)]

                is_sr_time = (plot_type in ("Horizontal Storm-Relative", "Radial-Height Profile"))
                cl  = {c.lower(): c for c in temp_df.columns}
                x_c = next((cl[c] for c in ['lon', 'longitude', 'clon'] if c in cl), None)
                y_c = next((cl[c] for c in ['lat', 'latitude',  'clat'] if c in cl), None)

                if is_sr_time and plotter is not None and sr_track_grp and x_c and y_c:
                    sr_max = domain_bounds.get('_sr_max_range_km', 9999.0)
                    t_c = cl.get('time')
                    if t_c:
                        try:
                            result = plotter._to_storm_relative(
                                temp_df[x_c].values, temp_df[y_c].values,
                                temp_df[t_c].values, sr_track_grp, "Relative to North"
                            )
                            if result is not None:
                                _, _, range_km_fit, _, _ = result
                                temp_df = temp_df[range_km_fit <= sr_max]
                        except Exception:
                            pass
                elif x_c and y_c:
                    mask = (
                        (temp_df[y_c] >= domain_bounds['lat_min']) &
                        (temp_df[y_c] <= domain_bounds['lat_max']) &
                        (temp_df[x_c] >= domain_bounds['lon_min']) &
                        (temp_df[x_c] <= domain_bounds['lon_max'])
                    )
                    temp_df = temp_df[mask]

                if not temp_df.empty:
                    visible_dt = pd.to_datetime(
                        temp_df[time_col].apply(lambda x: f"{x:.0f}"),
                        format="%Y%m%d%H%M%S", errors='coerce'
                    ).dropna()
                    if not visible_dt.empty:
                        fit_min = max(visible_dt.min().to_pydatetime(), s_min_dt)
                        fit_max = min(visible_dt.max().to_pydatetime(), s_max_dt)
                        if fit_min > fit_max:
                            fit_min = fit_max
                        st.session_state._force_time_range  = (fit_min, fit_max)
                        st.session_state._force_time_fit    = True
                        st.session_state._slider_time_bounds = (fit_min, fit_max)
                        st.rerun()

                st.toast("⚠️ No data remaining in current Domain/Level to fit.",
                         icon="⚠️")

        with tb2:
            if st.button("🔄 Reset time", width="stretch",
                         key='btn_time_reset'):
                st.session_state._force_time_range = (data_min_dt, data_max_dt)
                st.session_state._force_time_fit   = True
                st.session_state.pop('_slider_time_bounds', None)
                st.rerun()

        time_bounds = {
            'col': time_col,
            'min': float(time_range[0].strftime("%Y%m%d%H%M%S")),
            'max': float(time_range[1].strftime("%Y%m%d%H%M%S")),
        }

    return time_bounds


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_viewer_controls(plotter) -> ViewerIntent:
    """
    Render all sidebar sections and return a ViewerIntent with every value
    the caller needs to invoke the plotter.  No Streamlit state is read
    by the caller after this function returns.
    """
    intent = ViewerIntent()

    # --- File upload (may trigger st.rerun internally) ---
    if 'viewer_state' not in st.session_state:
        st.session_state.viewer_state = {}

    data_pack = render_file_upload_section(
        data_pack_key='data_pack', 
        filename_key='last_uploaded_filename', 
        state_keys=_VIEWER_STATE_KEYS, 
        state_dict_key='viewer_state'
    )

    if data_pack is None:
        return intent   # caller should show the "please upload" message

    intent.data_pack = data_pack

    # Build plotter from the freshly confirmed data_pack so all downstream
    # sections (variable list, SR range computation, etc.) have a valid instance.
    from plotter import StormPlotter
    plotter = StormPlotter(
        data_pack['data'], data_pack['track'],
        data_pack['meta'], data_pack['var_attrs']
    )

    # --- Manual storm centre override ---
    if data_pack['meta']['storm_center'] is None:
        with st.sidebar.container(border=True):
            st.warning("⚠️ Storm Center Missing from Metadata")
            if 'v_clat' not in st.session_state:
                st.session_state.v_clat = 20.0
            if 'v_clon' not in st.session_state:
                st.session_state.v_clon = -50.0
            c1, c2 = st.columns(2)
            clat = c1.number_input("Manual Lat", key='v_clat')
            clon = c2.number_input("Manual Lon", key='v_clon')
            data_pack['meta']['storm_center'] = (clat, clon)

    # --- Default geo bounds (used by domain section and auto-fit) ---
    intent.default_lat_min = _extract_strict_bound(data_pack, 'geospatial_lat_min') or 0.0
    intent.default_lat_max = _extract_strict_bound(data_pack, 'geospatial_lat_max') or 0.0
    intent.default_lon_min = _extract_strict_bound(data_pack, 'geospatial_lon_min') or 0.0
    intent.default_lon_max = _extract_strict_bound(data_pack, 'geospatial_lon_max') or 0.0

    # --- Variable selector ---
    # plot_type is rendered below, but we need it here to exclude h_col in RH mode.
    # Read from session state (set by the selectbox key 'v_plot_type') so it's available.
    plot_type = st.session_state.get('v_plot_type', 'Horizontal Cartesian')
    (sel_group, variable, plot_var, color_scale,
     h_col, p_col, df_sel, cols_lower, rh_z_col) = _render_variable_section(data_pack, plotter, plot_type)
    intent.sel_group   = sel_group
    intent.variable    = variable
    intent.plot_var    = plot_var
    intent.color_scale = color_scale

    options = [c for c in [h_col, p_col] if c]

    # --- Plot Type (Cartesian / Storm-Relative / Radial-Height) ---
    # is_3d not yet known here; read from session state for the availability check
    _cur_is_3d = st.session_state.get('v_is_3d', False)
    plot_type, sr_up_convention, sr_track_grp, rh_z_col = _render_plot_type_section(
        data_pack, sel_group, _cur_is_3d,
        h_col=h_col, p_col=p_col, plotter=plotter
    )

    # --- Plotting options (thinning, level, track, 3D, size) ---
    (show_cen, cen_mode, apply_thinning, thin_pct, z_con, target_col,
     target_col_3d, track_mapping, plot_track, selected_platform,
     track_proj, is_3d, plot_z_col, z_ratio, marker_sz, vec_scale,
     can_do_3d) = _render_plotting_options(
         data_pack, sel_group, h_col, p_col, df_sel, cols_lower, plot_var, plot_type
     )

    # Pass the actively managed basemap state to the intent
    show_basemap = st.session_state.get('v_show_basemap', False)

    intent.show_cen          = show_cen
    intent.cen_mode          = cen_mode
    intent.show_basemap      = show_basemap
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

    # --- Domain limits ---
    (domain_bounds, convert_dom,
     vert_range, domain_z_col) = _render_domain_section(
         data_pack, sel_group, df_sel, options,
         target_col, target_col_3d, is_3d,
         intent.default_lat_min, intent.default_lat_max,
         intent.default_lon_min, intent.default_lon_max,
         plot_type=plot_type, sr_track_grp=sr_track_grp, plotter=plotter,
         rh_z_col=rh_z_col
     )
    intent.domain_bounds = domain_bounds

    # --- Time limits ---
    if df_sel is not None:
        intent.time_bounds = _render_time_section(
            data_pack, sel_group, df_sel, domain_bounds,
            plot_type=plot_type, sr_track_grp=sr_track_grp, plotter=plotter
        )

    # Persist v_ keys to viewer_state for cross-rerun continuity
    for k in list(st.session_state.keys()):
        if k.startswith('v_'):
            st.session_state.viewer_state[k] = st.session_state[k]

    return intent
