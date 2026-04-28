# -*- coding: utf-8 -*-
"""
ui_viewer_domain.py
-------------------
Domain and time limit sidebar sections for the File Data Viewer tab.
"""

import math
import pandas as pd
import numpy as np
import streamlit as st

from config import (
    DEFAULT_SR_MAX_RANGE, 
    GLOBAL_LAT_MIN, GLOBAL_LAT_MAX, 
    GLOBAL_LON_MIN, GLOBAL_LON_MAX
)
from data_utils import decode_metadata, compute_global_domain, compute_vert_bounds
from ui_components import section_divider, sidebar_label, init_state, consume_flag, safe_slider, dynamic_range_slider

def _render_domain_section(data_pack, sel_group, df_sel, options,
                           target_col_3d, is_3d,
                           default_lat_min, default_lat_max,
                           default_lon_min, default_lon_max,
                           plot_type="Horizontal Cartesian",
                           sr_track_grp=None, plotter=None):

    is_sr = (plot_type == "Horizontal Storm-Relative")
    is_rh = (plot_type == "Radial-Height Profile")

    with st.sidebar.container(border=True):
        st.markdown("### 🗺️ Plot Domain Limits")

        if 'global_domain' not in data_pack:
            compute_global_domain(data_pack)
        _gd = data_pack.get('global_domain')
        _gd_lat = (_gd['lat_min'], _gd['lat_max']) if _gd else (default_lat_min, default_lat_max)
        _gd_lon = (_gd['lon_min'], _gd['lon_max']) if _gd else (default_lon_min, default_lon_max)

        if consume_flag('_force_domain_fit'):
            if '_force_lat_range' in st.session_state and '_force_lon_range' in st.session_state:
                forced_lat = consume_flag('_force_lat_range')
                forced_lon = consume_flag('_force_lon_range')
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
                st.session_state.v_vert_range = consume_flag('_force_z_range')
                
        if consume_flag('_reset_z_range'):
            if 'v_vert_range' in st.session_state:
                del st.session_state['v_vert_range']

        if is_sr or is_rh:
            sr_default_max = DEFAULT_SR_MAX_RANGE
            if plotter is not None and sr_track_grp:
                try:
                    sr_default_max = plotter.get_sr_max_range(sel_group, sr_track_grp)
                except Exception as e:
                    st.warning(f"SR range error: {type(e).__name__}: {e}")

            sr_slider_max = max(sr_default_max, 25.0)

            if '_force_sr_max_range' in st.session_state:
                st.session_state.v_sr_max_range = consume_flag('_force_sr_max_range')

            if st.session_state.get('_sr_last_group') != sel_group:
                st.session_state.v_sr_max_range = sr_default_max
                st.session_state['_sr_last_group'] = sel_group
            else:
                init_state('v_sr_max_range', sr_default_max)
                st.session_state.v_sr_max_range = float(np.clip(st.session_state.v_sr_max_range, 25.0, sr_slider_max))

            c1, c2 = st.columns([0.7, 2.0])
            with c1: sidebar_label('Max Range (km):', size='label')
            with c2:
                # Replaced raw slider with safe_slider to automatically prevent the 25.0 bounds collision
                sr_max_range = safe_slider("Max Range (km)", min_value=25.0, max_value=float(sr_slider_max), step=25.0, key='v_sr_max_range', label_visibility="collapsed")

            domain_bounds = {
                'lat_min': GLOBAL_LAT_MIN, 'lat_max': GLOBAL_LAT_MAX,
                'lon_min': GLOBAL_LON_MIN, 'lon_max': GLOBAL_LON_MAX,
                '_sr_max_range_km': sr_max_range,
            }
            lat_range = (_gd_lat[0], _gd_lat[1])
            lon_range = (_gd_lon[0], _gd_lon[1])

        else:
            c1, c2, c3, c4 = st.columns([0.7, 2.0, 0.7, 2.0])
            with c1: sidebar_label('Lat (deg):', size='label')
            with c2:
                _s_lat_min, _s_lat_max = st.session_state.get('_slider_lat_bounds', (_gd_lat[0], _gd_lat[1]))
                init_state('v_lat_range', _gd_lat)
                
                lat_range = dynamic_range_slider(
                    "Latitude Limits", global_min=_gd_lat[0], global_max=_gd_lat[1], 
                    data_min=_s_lat_min, data_max=_s_lat_max, 
                    key='v_lat_range', step=0.1, label_visibility="collapsed"
                )
            
            with c3: sidebar_label('Lon (deg):', size='label')
            with c4:
                _s_lon_min, _s_lon_max = st.session_state.get('_slider_lon_bounds', (_gd_lon[0], _gd_lon[1]))
                init_state('v_lon_range', _gd_lon)
                
                lon_range = dynamic_range_slider(
                    "Longitude Limits", global_min=_gd_lon[0], global_max=_gd_lon[1], 
                    data_min=_s_lon_min, data_max=_s_lon_max, 
                    key='v_lon_range', step=0.1, label_visibility="collapsed"
                )

            domain_bounds = {'lat_min': lat_range[0], 'lat_max': lat_range[1], 'lon_min': lon_range[0], 'lon_max': lon_range[1]}

        vert_range   = None
        convert_dom  = False
        domain_z_col = None
        rh_z_col     = None
        z_con        = None
        plot_z_col   = None

        if options and df_sel is not None:
            init_state('v_vert_coord', options[0])
            if st.session_state.v_vert_coord not in options:
                st.session_state.v_vert_coord = options[0]
                
            domain_z_col = st.session_state.v_vert_coord

            v_unit_dom = decode_metadata(data_pack['var_attrs'].get(sel_group, {}).get(domain_z_col, {}).get('units', ''))
            convert_dom = 'Pa' in v_unit_dom and 'hPa' not in v_unit_dom
            if convert_dom: v_unit_dom = 'hPa'
            
            unit_str = f"({v_unit_dom})" if v_unit_dom else ""

            v1, v2 = st.columns([1.1, 1.8])
            with v1: 
                sidebar_label(f'Vertical Range {unit_str}:', enabled=True, size='label')
            with v2: 
                def _fmt_vert(x):
                    meta = data_pack.get('var_attrs', {}).get(sel_group, {}).get(x, {})
                    long = decode_metadata(meta.get('long_name', '')) or x.replace('_', ' ').title()
                    return long.title()
                
                st.selectbox("VCoord", options, key='v_vert_coord', label_visibility="collapsed", format_func=_fmt_vert)

            if st.session_state.get('v_last_coord') != domain_z_col:
                st.session_state.pop('v_vert_range', None)
                st.session_state.v_last_coord = domain_z_col

            vert_vals = df_sel[domain_z_col].dropna().values
            if len(vert_vals) > 0:
                if convert_dom: vert_vals = vert_vals / 100.0

                is_pres = convert_dom or any(p in domain_z_col.lower() for p in ['pres', 'pressure', 'p'])
                if is_pres:
                    zmin_global = float(max(0.0, math.floor(np.nanmin(vert_vals) / 50.0) * 50.0))
                    zmax_global = float(max(1015.0, math.ceil(np.nanmax(vert_vals) / 50.0) * 50.0))
                else:
                    zmin_global = 0.0
                    zmax_global = float(math.ceil(np.nanmax(vert_vals) / 1000.0) * 1000.0)
                    if zmax_global == 0.0: zmax_global = 1000.0

                if zmin_global >= zmax_global: zmax_global = zmin_global + 1.0

                init_state('v_vert_range', (zmin_global, zmax_global))
                
                vert_range_ui = dynamic_range_slider(
                    "Vertical Limits", global_min=zmin_global, global_max=zmax_global,
                    data_min=zmin_global, data_max=zmax_global, 
                    key='v_vert_range', step=0.01, label_visibility="collapsed"
                )

                vert_range = vert_range_ui
                domain_bounds['z_min']     = vert_range[0]
                domain_bounds['z_max']     = vert_range[1]
                domain_bounds['z_col']     = domain_z_col
                domain_bounds['z_convert'] = convert_dom
                
                if is_rh:
                    rh_z_col = domain_z_col
                else:
                    z_con = {'col': domain_z_col, 'val': (vert_range[1] + vert_range[0]) / 2.0, 'tol': abs(vert_range[1] - vert_range[0]) / 2.0, 'convert_pa_to_hpa': convert_dom}
                    plot_z_col = domain_z_col if not is_3d else (target_col_3d if target_col_3d else domain_z_col)

        b1, b2 = st.columns(2)
        b1.markdown('<div class="light-btn-marker" style="display:none;"></div>', unsafe_allow_html=True)

        with b1:
            if st.button("🔍 Auto-fit domain", width="stretch") or consume_flag('_trigger_auto_fit'):
                if is_sr or is_rh:
                    if plotter is not None and sr_track_grp:
                        try:
                            temp_df = df_sel.copy()
                            time_col_sr = next((c for c in temp_df.columns if c.lower() in ['time', 'date', 'datetime', 'epoch']), None)
                            if time_col_sr and 'v_time_range' in st.session_state:
                                try:
                                    t_min_dt, t_max_dt = st.session_state.v_time_range
                                    t_min_f = float(t_min_dt.strftime("%Y%m%d%H%M%S"))
                                    t_max_f = float(t_max_dt.strftime("%Y%m%d%H%M%S"))
                                    temp_df = temp_df[(temp_df[time_col_sr] >= t_min_f) & (temp_df[time_col_sr] <= t_max_f)]
                                except Exception: pass

                            if temp_df.empty:
                                st.toast("⚠️ No data in current time window to fit.", icon="⚠️")
                            else:
                                fitted_max = plotter.get_sr_max_range(sel_group, sr_track_grp, df_override=temp_df)
                                st.session_state._force_sr_max_range = fitted_max
                                st.rerun()
                        except Exception as e: st.toast(f"⚠️ SR range error: {type(e).__name__}: {e}", icon="⚠️")
                else:
                    _fit_df = df_sel if df_sel is not None else data_pack['data'].get(sel_group)
                    if _fit_df is None:
                        st.toast("⚠️ No data available to fit.", icon="⚠️")
                    else:
                        temp_df = _fit_df.copy()
                        
                        if domain_z_col and domain_z_col in temp_df.columns and 'v_vert_range' in st.session_state:
                            vmin, vmax = st.session_state.v_vert_range
                            v_unit = decode_metadata(data_pack['var_attrs'].get(sel_group, {}).get(domain_z_col, {}).get('units', ''))
                            conv = 'Pa' in v_unit and 'hPa' not in v_unit
                            t_vals = temp_df[domain_z_col] / 100.0 if conv else temp_df[domain_z_col]
                            temp_df = temp_df[(t_vals >= vmin) & (t_vals <= vmax)]

                        time_col = next((c for c in temp_df.columns if c.lower() in ['time', 'date', 'datetime', 'epoch']), None)
                        is_track_fit = 'TRACK' in sel_group.upper()
                        if not is_track_fit and time_col and 'v_time_range' in st.session_state:
                            try:
                                t_min_dt, t_max_dt = st.session_state.v_time_range
                                t_min_f = float(t_min_dt.strftime("%Y%m%d%H%M%S"))
                                t_max_f = float(t_max_dt.strftime("%Y%m%d%H%M%S"))
                                temp_df = temp_df[(temp_df[time_col] >= t_min_f) & (temp_df[time_col] <= t_max_f)]
                            except Exception: pass

                        cl = {c.lower(): c for c in temp_df.columns}
                        x_c = next((cl[c] for c in ['lon', 'longitude', 'clon'] if c in cl), None)
                        y_c = next((cl[c] for c in ['lat', 'latitude',  'clat'] if c in cl), None)

                        if not x_c or not y_c: st.toast("⚠️ No lat/lon columns found in this group.", icon="⚠️")
                        elif temp_df.empty: st.toast("⚠️ No data remaining after time/level filter.", icon="⚠️")
                        else:
                            a_lat_min, a_lat_max = float(temp_df[y_c].min(skipna=True)), float(temp_df[y_c].max(skipna=True))
                            a_lon_min, a_lon_max = float(temp_df[x_c].min(skipna=True)), float(temp_df[x_c].max(skipna=True))
                            lat_span, lon_span  = max(a_lat_max - a_lat_min, 0.05), max(a_lon_max - a_lon_min, 0.05)
                            buf_lat, buf_lon   = lat_span * 0.05, lon_span * 0.05
                            fit_lat_min, fit_lat_max = a_lat_min - buf_lat, a_lat_max + buf_lat
                            fit_lon_min, fit_lon_max = a_lon_min - buf_lon, a_lon_max + buf_lon
                            
                            if (fit_lat_max - fit_lat_min) > (fit_lon_max - fit_lon_min):
                                extra = ((fit_lat_max - fit_lat_min) - (fit_lon_max - fit_lon_min)) / 2
                                fit_lon_min -= extra; fit_lon_max += extra
                            else:
                                extra = ((fit_lon_max - fit_lon_min) - (fit_lat_max - fit_lat_min)) / 2
                                fit_lat_min -= extra; fit_lat_max += extra

                            if is_track_fit:
                                st.session_state._force_lat_range = (fit_lat_min, fit_lat_max)
                                st.session_state._force_lon_range = (fit_lon_min, fit_lon_max)
                                st.session_state._slider_lat_bounds = (fit_lat_min, fit_lat_max)
                                st.session_state._slider_lon_bounds = (fit_lon_min, fit_lon_max)
                            else:
                                st.session_state._force_lat_range = (max(_gd_lat[0], fit_lat_min), min(_gd_lat[1], fit_lat_max))
                                st.session_state._force_lon_range = (max(_gd_lon[0], fit_lon_min), min(_gd_lon[1], fit_lon_max))
                                st.session_state._slider_lat_bounds = (fit_lat_min, fit_lat_max)
                                st.session_state._slider_lon_bounds = (fit_lon_min, fit_lon_max)

                            if (st.session_state.get('v_is_3d') and domain_z_col and domain_z_col in temp_df.columns):
                                z_vals_fit = temp_df[domain_z_col].dropna()
                                if not z_vals_fit.empty:
                                    v_unit_fit = decode_metadata(data_pack['var_attrs'].get(sel_group, {}).get(domain_z_col, {}).get('units', ''))
                                    conv_fit = 'Pa' in v_unit_fit and 'hPa' not in v_unit_fit
                                    if conv_fit: z_vals_fit = z_vals_fit / 100.0
                                    a_z_min, a_z_max  = float(z_vals_fit.min()), float(z_vals_fit.max())
                                    if conv_fit or any(p in domain_z_col.lower() for p in ['pres', 'pressure', 'p']):
                                        st.session_state._force_z_range = (max(0.0, a_z_min - (max(a_z_max - a_z_min, 1.0) * 0.05)), a_z_max + 5.0)
                                    else:
                                        buf_z = max(a_z_max - a_z_min, 1.0) * 0.05
                                        st.session_state._force_z_range = (a_z_min - buf_z, a_z_max + buf_z)
                            st.session_state._force_domain_fit = True
                            st.rerun()

        with b2:
            if st.button("🔄 Reset domain", width="stretch"):
                st.session_state._force_lat_range = (_gd_lat[0], _gd_lat[1])
                st.session_state._force_lon_range = (_gd_lon[0], _gd_lon[1])
                st.session_state.pop('_slider_lat_bounds', None)
                st.session_state.pop('_slider_lon_bounds', None)
                st.session_state._force_domain_fit = True
                st.session_state._reset_z_range    = True
                
                consume_flag('_force_sr_max_range')
                if 'v_sr_max_range' in st.session_state: del st.session_state['v_sr_max_range']
                if 'viewer_state' in st.session_state and 'v_sr_max_range' in st.session_state.viewer_state:
                    del st.session_state.viewer_state['v_sr_max_range']
                st.rerun()

    return domain_bounds, convert_dom, vert_range, domain_z_col, rh_z_col, z_con, plot_z_col


def _render_time_section(data_pack, sel_group, df_sel, domain_bounds,
                         plot_type="Horizontal Cartesian",
                         sr_track_grp=None, plotter=None):
    from datetime import timedelta

    with st.sidebar.container(border=True):
        st.markdown("### ⏱️ Plot Time Limits")

        time_col   = next((c for c in df_sel.columns if c.lower() in ['time', 'date', 'datetime', 'epoch']), None)
        time_bounds = None

        if not time_col:
            st.info("No time data available for this variable.")
            return None

        time_vals = df_sel[time_col].dropna()
        is_legacy_time = (time_vals > 1.9e13).any()
        
        offset = data_pack.get('meta', {}).get('time_offset_seconds', 0.0)

        if is_legacy_time:
            valid_mask = df_sel[time_col] > 19000000000000.0
            dt_series  = pd.to_datetime(
                df_sel.loc[valid_mask, time_col].apply(lambda x: f"{x:.0f}" if pd.notna(x) else None),
                format="%Y%m%d%H%M%S", errors='coerce'
            ).dropna()
        else:
            dt_series = pd.to_datetime(df_sel[time_col] - offset, unit='s', errors='coerce').dropna()

        if dt_series.empty:
            st.warning("Time column exists, but all values are invalid or corrupted.")
            return None

        data_min_dt = dt_series.min().to_pydatetime()
        data_max_dt = dt_series.max().to_pydatetime()

        is_track_grp = 'TRACK' in sel_group.upper()
        default_range = (data_min_dt, data_max_dt)

        _t_bounds = st.session_state.get('_slider_time_bounds')
        _t_slider_min = _t_bounds[0] if _t_bounds else data_min_dt
        _t_slider_max = _t_bounds[1] if _t_bounds else data_max_dt

        if st.session_state.get('_time_last_was_track') != is_track_grp:
            st.session_state.pop('v_time_range', None)
        st.session_state['_time_last_was_track'] = is_track_grp

        if consume_flag('_force_time_fit'):
            forced_min, forced_max = consume_flag('_force_time_range')
            forced_min = max(data_min_dt, min(forced_min, data_max_dt))
            forced_max = max(data_min_dt, min(forced_max, data_max_dt))
            if forced_min > forced_max: forced_min = forced_max
            st.session_state.pop('v_time_range', None)
            st.session_state._pending_time_range = (forced_min, forced_max)
        else:
            init_state('v_time_range', default_range)
            t_c_min, t_c_max = st.session_state.v_time_range
            t_c_min = max(_t_slider_min, min(t_c_min, _t_slider_max))
            t_c_max = max(_t_slider_min, min(t_c_max, _t_slider_max))
            if t_c_min > t_c_max: t_c_min = t_c_max
            st.session_state.v_time_range = (t_c_min, t_c_max)

        sidebar_label('Time Range (UTC):', size='label')
        
        _pending_time = consume_flag('_pending_time_range')
        if _pending_time: st.session_state.v_time_range = _pending_time
            
        # Standard Streamlit slider explicitly maintained to support the safe timedelta logic 
        if pd.isnull(_t_slider_min) or pd.isnull(_t_slider_max):
            st.warning("⚠️ Invalid time bounds in current domain.")
            return None
        elif _t_slider_min >= _t_slider_max:
            safe_max = _t_slider_min + timedelta(seconds=1)
            time_range = st.slider(
                "Time Limits", 
                min_value=_t_slider_min, 
                max_value=safe_max, 
                value=(_t_slider_min, safe_max), 
                key='v_time_range', 
                format="HH:mm:ss", 
                label_visibility="collapsed"
            )
        else:
            time_range = st.slider(
                "Time Limits", 
                min_value=_t_slider_min, 
                max_value=_t_slider_max, 
                key='v_time_range', 
                format="HH:mm:ss", 
                label_visibility="collapsed"
            )

        tb1, tb2 = st.columns(2)
        tb1.markdown('<div class="light-btn-marker" style="display:none;"></div>', unsafe_allow_html=True)

        with tb1:
            if st.button("⏱️ Auto-fit time", width="stretch", key='btn_time_fit') or consume_flag('_trigger_time_fit'):
                temp_df = df_sel.copy()
                
                if domain_bounds and domain_bounds.get('z_col') and 'v_vert_range' in st.session_state:
                    t_col = domain_bounds['z_col']
                    if t_col in temp_df.columns:
                        vmin, vmax = st.session_state.v_vert_range
                        v_unit = decode_metadata(data_pack['var_attrs'].get(sel_group, {}).get(t_col, {}).get('units', ''))
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
                            result = plotter._to_storm_relative(temp_df[x_c].values, temp_df[y_c].values, temp_df[t_c].values, sr_track_grp, "Relative to North")
                            if result is not None:
                                _, _, range_km_fit, _, _ = result
                                temp_df = temp_df[range_km_fit <= sr_max]
                        except Exception: pass
                elif x_c and y_c:
                    mask = ((temp_df[y_c] >= domain_bounds['lat_min']) & (temp_df[y_c] <= domain_bounds['lat_max']) & (temp_df[x_c] >= domain_bounds['lon_min']) & (temp_df[x_c] <= domain_bounds['lon_max']))
                    temp_df = temp_df[mask]

                if not temp_df.empty:
                    offset = data_pack.get('meta', {}).get('time_offset_seconds', 0.0)
                    
                    if is_legacy_time:
                        visible_dt = pd.to_datetime(temp_df[time_col].apply(lambda x: f"{x:.0f}"), format="%Y%m%d%H%M%S", errors='coerce').dropna()
                    else:
                        visible_dt = pd.to_datetime(temp_df[time_col] - offset, unit='s', errors='coerce').dropna()
                    
                    if not visible_dt.empty:
                        fit_min = max(visible_dt.min().to_pydatetime(), data_min_dt)
                        fit_max = min(visible_dt.max().to_pydatetime(), data_max_dt)
                        
                        if fit_min >= fit_max: 
                            fit_max = fit_min + timedelta(seconds=1)
                            
                        st.session_state._force_time_range  = (fit_min, fit_max)
                        st.session_state._force_time_fit    = True
                        st.session_state._slider_time_bounds = (fit_min, fit_max)
                        st.rerun()

                st.toast("⚠️ No data remaining in current Domain/Level to fit.", icon="⚠️")

        with tb2:
            if st.button("🔄 Reset time", width="stretch", key='btn_time_reset'):
                st.session_state._force_time_range = (data_min_dt, data_max_dt)
                st.session_state._force_time_fit   = True
                st.session_state.pop('_slider_time_bounds', None)
                st.rerun()

        offset = data_pack.get('meta', {}).get('time_offset_seconds', 0.0)
        
        if is_legacy_time:
            ret_min = float(time_range[0].strftime("%Y%m%d%H%M%S"))
            ret_max = float(time_range[1].strftime("%Y%m%d%H%M%S"))
        else:
            from datetime import timezone
            ret_min = time_range[0].replace(tzinfo=timezone.utc).timestamp() + offset
            ret_max = time_range[1].replace(tzinfo=timezone.utc).timestamp() + offset
            
        time_bounds = {'col': time_col, 'min': ret_min, 'max': ret_max}

    return time_bounds
