# -*- coding: utf-8 -*-
"""
ui_viewer_domain.py
-------------------
Domain and time limit sidebar sections for the File Data Viewer tab.

Public API
----------
_render_domain_section(...)
    Renders lat/lon/vertical domain sliders with auto-fit and reset buttons.
    Returns (domain_bounds, convert_dom, vert_range, domain_z_col).

_render_time_section(...)
    Renders the time range slider with auto-fit and reset buttons.
    Returns time_bounds dict or None.
"""

import math
import pandas as pd
import numpy as np
import streamlit as st

from data_utils import decode_metadata
from ui_components import section_divider, sidebar_label
from ui_viewer_file import _compute_global_domain


def _render_domain_section(data_pack, sel_group, df_sel, options,
                            target_col_3d, is_3d,
                            default_lat_min, default_lat_max,
                            default_lon_min, default_lon_max,
                            plot_type="Horizontal Cartesian",
                            sr_track_grp=None, plotter=None):
    """Renders domain limit sliders + auto-fit / reset buttons.
    Returns (domain_bounds, convert_dom, vert_range, domain_z_col)."""

    is_sr = (plot_type == "Horizontal Storm-Relative")

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

        if is_sr:
            # SR mode: left column = Max Range (km) slider, right column hidden
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
        domain_z_col = target_col_3d

        if options and df_sel is not None:
            v_unit_dom = decode_metadata(
                data_pack['var_attrs'].get(sel_group, {})
                .get(domain_z_col, {}).get('units', '')
            )
            convert_dom = 'Pa' in v_unit_dom and 'hPa' not in v_unit_dom
            if convert_dom:
                v_unit_dom = 'hPa'

            vert_vals = df_sel[domain_z_col].dropna().values
            if len(vert_vals) > 0:
                if convert_dom:
                    vert_vals = vert_vals / 100.0

                is_pres = convert_dom or any(
                    p in domain_z_col.lower() for p in ['pres', 'pressure', 'p']
                )
                if is_pres:
                    zmin_global = float(max(0.0, math.floor(np.nanmin(vert_vals) / 50.0) * 50.0))
                    zmax_global = float(max(1015.0, math.ceil(np.nanmax(vert_vals) / 50.0) * 50.0))
                else:
                    zmin_global = 0.0
                    zmax_global = float(math.ceil(np.nanmax(vert_vals) / 1000.0) * 1000.0)
                    if zmax_global == 0.0:
                        zmax_global = 1000.0

                if zmin_global >= zmax_global:
                    zmax_global = zmin_global + 1.0

                if 'v_vert_range' not in st.session_state:
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
                        key='v_vert_range', step=0.01,
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
                if is_sr:
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
                                    z_span   = max(a_z_max - a_z_min, 1.0)
                                    buf_z    = z_span * 0.05
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
            # Delete widget key so slider reinitializes with new bounds
            st.session_state.pop('v_time_range', None)
            st.session_state._pending_time_range = (forced_min, forced_max)
        elif 'v_time_range' not in st.session_state:
            st.session_state.v_time_range = default_range
        else:
            t_c_min, t_c_max = st.session_state.v_time_range
            t_c_min = max(s_min_dt, min(t_c_min, s_max_dt))
            t_c_max = max(s_min_dt, min(t_c_max, s_max_dt))
            if t_c_min > t_c_max:
                t_c_min = t_c_max
            st.session_state.v_time_range = (t_c_min, t_c_max)

        sidebar_label('Time Range (UTC):', size='label')
        _pending_time = st.session_state.pop('_pending_time_range', None)
        _t_bounds = st.session_state.get('_slider_time_bounds')
        _t_slider_min = _t_bounds[0] if _t_bounds else s_min_dt
        _t_slider_max = _t_bounds[1] if _t_bounds else s_max_dt
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

                is_sr_time = (plot_type == "Horizontal Storm-Relative")
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
