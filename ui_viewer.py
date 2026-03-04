# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from config import EXPECTED_GROUPS, EXPECTED_META
from data_utils import load_data_from_h5, decode_metadata
from ui_layout import apply_viewer_compaction_css
from plotter import StormPlotter, add_flight_tracks

def render_viewer_tab():
    apply_viewer_compaction_css()

    if 'viewer_state' not in st.session_state:
        st.session_state.viewer_state = {}
        
    for k, v in st.session_state.viewer_state.items():
        if k not in st.session_state:
            st.session_state[k] = v

    with st.sidebar.container(border=True):
        st.markdown("### 📁 File Upload")
        data_pack = st.session_state.get('data_pack', None)

        if data_pack is None:
            uploaded_file = st.file_uploader("Upload an AI-Ready HDF5 file", type=['h5', 'hdf5'], label_visibility="collapsed")
            if uploaded_file is not None:
                if st.session_state.get('last_uploaded_filename') != uploaded_file.name:
                    with st.spinner("Processing HDF5..."):
                        try:
                            st.session_state.data_pack = load_data_from_h5(uploaded_file.getvalue())
                            st.session_state.last_uploaded_filename = uploaded_file.name
                            keys_to_clear = ['v_sel_group', 'v_variable', 'v_use_filter', 'v_vert_coord', 'v_lvl_range', 'v_is_3d', 'v_3d_z', 'v_plot_track', 'v_sel_plat', 'v_3d_ratio', 'v_apply_thinning', 'v_thin_pct', 'v_marker_size', 'v_lat_range', 'v_lon_range', 'v_time_range', 'v_show_cen', 'v_clat', 'v_clon']
                            for k in keys_to_clear:
                                if k in st.session_state: del st.session_state[k]
                            st.session_state.viewer_state = {}
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to load file: {e}")
                            st.stop()
        else:
            st.success(f"📂 **File Loaded to Memory:**\n{st.session_state.last_uploaded_filename}")
            if st.button("🗑️ Clear Memory & Upload New File"):
                del st.session_state['data_pack']
                del st.session_state['last_uploaded_filename']
                st.session_state.viewer_state = {} 
                st.rerun()
                
        if data_pack is not None:
            with st.expander("🗂️ View Current File Inventory", expanded=False):
                inventory_html = "<div style='font-size: 13px; line-height: 1.6; padding: 5px;'>"
                for g in EXPECTED_GROUPS:
                    if g in data_pack['data']: inventory_html += f"<span style='color: #0c7b20;'>✅ <b>{g}</b></span><br>"
                    else: inventory_html += f"<span style='color: #a0a0a0;'>❌ <i>{g}</i></span><br>"
                for g in [g for g in data_pack['data'].keys() if g not in EXPECTED_GROUPS]: 
                    inventory_html += f"<span style='color: #005bb5;'>⚠️ <b>{g} (Extra)</b></span><br>"
                inventory_html += "</div>"
                st.markdown(inventory_html, unsafe_allow_html=True)
                
            with st.expander("📊 View Global Metadata Inventory", expanded=False):
                meta_html = "<table style='font-size: 14px; width: 100%; text-align: left; border-collapse: collapse;'><tr style='border-bottom: 2px solid #ddd;'><th style='padding: 8px;'>Field</th><th style='padding: 8px;'>Value</th></tr>"
                for m in EXPECTED_META:
                    if m in data_pack['meta']['info']:
                        meta_html += f"<tr><td style='padding: 6px;'><b>{m}</b></td><td style='padding: 6px; color: green;'>{decode_metadata(data_pack['meta']['info'][m])}</td></tr>"
                    else: 
                        meta_html += f"<tr><td style='padding: 6px; color: gray;'>{m}</td><td style='padding: 6px; color: red;'>❌ Missing</td></tr>"
                for m in [k for k in data_pack['meta']['info'].keys() if k not in EXPECTED_META]:
                    meta_html += f"<tr><td style='padding: 6px; color: blue;'><i>{m} (Extra)</i></td><td style='padding: 6px; color: blue;'>{decode_metadata(data_pack['meta']['info'][m])}</td></tr>"
                meta_html += "</table>"
                st.markdown(meta_html, unsafe_allow_html=True)

    if data_pack is None:
        st.info("👈 Please upload an AI-Ready HDF5 file from the sidebar to visualize its contents.")
        return

    if data_pack['meta']['storm_center'] is None:
        with st.sidebar.container(border=True):
            st.warning("⚠️ Storm Center Missing from Metadata")
            if 'v_clat' not in st.session_state: st.session_state.v_clat = 20.0
            if 'v_clon' not in st.session_state: st.session_state.v_clon = -50.0
            c1, c2 = st.columns(2)
            clat = c1.number_input("Manual Lat", key='v_clat')
            clon = c2.number_input("Manual Lon", key='v_clon')
            data_pack['meta']['storm_center'] = (clat, clon)

    plotter = StormPlotter(data_pack['data'], data_pack['track'], data_pack['meta'], data_pack['var_attrs'])

    with st.sidebar.container(border=True):
        st.markdown("### 📈 Plot Variable")
        available_groups = sorted(list(data_pack['data'].keys()))
        if 'v_sel_group' not in st.session_state or st.session_state.v_sel_group not in available_groups:
            st.session_state.v_sel_group = available_groups[0] if available_groups else None
            
        def reset_thinning_on_change():
            st.session_state.v_apply_thinning = False
            st.session_state.v_thin_pct = 50
            if 'show_auto_thin_msg' in st.session_state: st.session_state.show_auto_thin_msg = False

        sel_group = st.selectbox("Select Active Group to Plot", available_groups, key='v_sel_group', on_change=reset_thinning_on_change)
        h_col, p_col = None, None
        
        if 'TRACK' not in sel_group.upper():
            df_sel = data_pack['data'][sel_group]
            cols_lower = {c.lower(): c for c in df_sel.columns}
            h_col = next((cols_lower[c] for c in ['height', 'ght', 'altitude', 'elev'] if c in cols_lower), None)
            p_col = next((cols_lower[c] for c in ['pres', 'pressure', 'p'] if c in cols_lower), None)

        exclude_col = st.session_state.get('v_vert_coord', None) if st.session_state.get('v_use_filter', False) else None
        vars_list = plotter.get_plottable_variables(sel_group, active_z_col=exclude_col)

        if 'TRACK' in sel_group.upper(): variable = 'Path'
        elif vars_list: 
            if 'v_variable' not in st.session_state or st.session_state.v_variable not in vars_list:
                st.session_state.v_variable = vars_list[0]
            variable = st.selectbox("Variable", vars_list, key='v_variable')
        else: 
            st.stop()

    def extract_strict_bound(key):
        for k, v in data_pack['meta'].get('info', {}).items():
            if str(k).strip("[]b'\" ").lower() == key.lower():
                try: return float(decode_metadata(v))
                except: return None
        return None

    default_lat_min = extract_strict_bound('geospatial_lat_min') or 0.0
    default_lat_max = extract_strict_bound('geospatial_lat_max') or 0.0
    default_lon_min = extract_strict_bound('geospatial_lon_min') or 0.0
    default_lon_max = extract_strict_bound('geospatial_lon_max') or 0.0

    with st.sidebar.container(border=True):
        st.markdown("### ⚙️ Plotting Options")
        if 'v_show_cen' not in st.session_state: st.session_state.v_show_cen = True
        show_cen = st.checkbox("Show Storm Center", key='v_show_cen')
        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)
        
        if st.session_state.pop('_force_thinning', False):
            st.session_state.v_apply_thinning = True
            st.session_state.v_thin_pct = st.session_state.pop('_force_thin_pct', 50)

        if 'v_apply_thinning' not in st.session_state: st.session_state.v_apply_thinning = False
        apply_thinning = st.checkbox("Apply thinning?", key='v_apply_thinning')
            
        thin_color = "inherit" if apply_thinning else "#999"
        t_c1, t_c2, t_c3 = st.columns([0.8, 2.8, 1.2])
        with t_c1: st.markdown(f"<div style='margin-top: 6px; font-size:13px; font-weight:500; color:{thin_color}; text-align:right;'>Show</div>", unsafe_allow_html=True)
        with t_c2:
            if 'v_thin_pct' not in st.session_state: st.session_state.v_thin_pct = 50
            thin_pct = st.slider("Thinning", min_value=5, max_value=100, step=5, key='v_thin_pct', disabled=not apply_thinning, label_visibility="collapsed")
        with t_c3: st.markdown(f"<div style='margin-top: 6px; font-size:13px; font-weight:500; color:{thin_color};'>% of obs.</div>", unsafe_allow_html=True)
            
        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)
        
        if 'v_use_filter' not in st.session_state: st.session_state.v_use_filter = False
        use_filter = st.checkbox("Filter by Level?", key='v_use_filter')
        f_color = "inherit" if use_filter else "#999"
        
        z_con, target_col = None, None 
        options = [c for c in [h_col, p_col] if c]

        if options:
            c_c, c_s = st.columns([1.2, 2.0])
            if st.session_state.get('v_vert_coord') not in options: st.session_state.v_vert_coord = options[0]
            
            with c_c:
                st.markdown(f"<div style='font-size:13px; font-weight:500; color:{f_color};'>Vertical Coord.</div>", unsafe_allow_html=True)
                target_col = st.selectbox("VCoord", options, key='v_vert_coord', disabled=not use_filter, label_visibility="collapsed")
            
            v_unit = decode_metadata(data_pack['var_attrs'].get(sel_group, {}).get(target_col, {}).get('units', ''))
            convert = 'Pa' in v_unit and 'hPa' not in v_unit
            if convert: v_unit = 'hPa'
            
            raw_vals = df_sel[target_col].dropna().values
            if len(raw_vals) > 0:
                if convert: raw_vals = raw_vals / 100.0
                dmin, dmax = float(np.nanmin(raw_vals)), float(np.nanmax(raw_vals))
                if dmin == dmax: dmax = dmin + 1.0
                
                with c_s:
                    st.markdown(f"<div style='font-size:13px; font-weight:500; color:{f_color};'>Range ({v_unit})</div>", unsafe_allow_html=True)
                    if st.session_state.get('v_last_coord') != target_col:
                        st.session_state.v_lvl_range = (dmin, dmax)
                        st.session_state.v_last_coord = target_col
                    elif 'v_lvl_range' not in st.session_state:
                        st.session_state.v_lvl_range = (dmin, dmax)

                    lvl_range = st.slider("Range", min_value=dmin, max_value=dmax, key='v_lvl_range', disabled=not use_filter, label_visibility="collapsed")
            
                if use_filter: z_con = {'col': target_col, 'val': (lvl_range[1] + lvl_range[0]) / 2.0, 'tol': abs(lvl_range[1] - lvl_range[0]) / 2.0, 'convert_pa_to_hpa': convert}

        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)

        flight_track_groups = [g for g in available_groups if g.lower().startswith('flight_level_hdobs')]
        track_mapping = {g.split('_')[-1].upper(): g for g in flight_track_groups}
        
        track_col1, track_col2 = st.columns([1.1, 1])
        with track_col1:
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
            if 'v_plot_track' not in st.session_state: st.session_state.v_plot_track = False
            plot_track = st.checkbox("Plot flight track from:", key='v_plot_track', disabled=(len(track_mapping) == 0))
            
        with track_col2:
            if 'v_sel_plat' not in st.session_state or st.session_state.v_sel_plat not in track_mapping:
                st.session_state.v_sel_plat = list(track_mapping.keys())[0] if track_mapping else None
            selected_platform = st.selectbox("Platform", list(track_mapping.keys()), key='v_sel_plat', disabled=not plot_track, label_visibility="collapsed") if track_mapping else None
        
        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)

        can_do_3d = (h_col is not None or p_col is not None)
        c3d_1, c3d_2 = st.columns([1.1, 1])
        with c3d_1:
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
            if 'v_is_3d' not in st.session_state: st.session_state.v_is_3d = False
            is_3d = st.checkbox("3D view with z axis:", key='v_is_3d', disabled=not can_do_3d)
            
        with c3d_2:
            options_3d = options if options else ["None"]
            if st.session_state.get('v_3d_z') not in options_3d: st.session_state.v_3d_z = options_3d[0]
            target_col_3d = st.selectbox("Select 3D Z-Axis", options_3d, key='v_3d_z', label_visibility="collapsed", disabled=not is_3d)
            
        plot_z_col = target_col if use_filter else (target_col_3d if options else None)

        r1, r2 = st.columns([1.1, 2.2])
        with r1: st.markdown(f"<div style='margin-top: 12px; font-size: 13px; font-weight: 500; color: {'inherit' if is_3d else '#999'};'>Vert. Aspect Ratio:</div>", unsafe_allow_html=True)
        with r2:
            if 'v_3d_ratio' not in st.session_state: st.session_state.v_3d_ratio = 0.3
            z_ratio = st.slider("VAR", min_value=0.05, max_value=1.5, step=0.05, key='v_3d_ratio', disabled=not is_3d, label_visibility="collapsed")

        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)

        m1, m2 = st.columns([1.1, 2.2])
        with m1: st.markdown("<div style='margin-top: 12px; font-size: 16px;'>Marker Size:</div>", unsafe_allow_html=True)
        with m2:
            if 'v_marker_size' not in st.session_state: st.session_state.v_marker_size = 100
            marker_sz = st.slider("Marker Size", min_value=10, max_value=200, step=10, format="%d%%", key='v_marker_size', label_visibility="collapsed")

    with st.sidebar.container(border=True):
        st.markdown("### 🗺️ Plot Domain Limits")
        if st.session_state.pop('_force_domain_fit', False):
            st.session_state.v_lat_range = st.session_state.pop('_force_lat_range')
            st.session_state.v_lon_range = st.session_state.pop('_force_lon_range')
        
        c1, c2, c3, c4 = st.columns([0.7, 2.0, 0.7, 2.0])
        with c1: st.markdown("<div style='margin-top: 8px; font-size: 16px;'>Lat:</div>", unsafe_allow_html=True)
        with c2:
            if 'v_lat_range' not in st.session_state: st.session_state.v_lat_range = (default_lat_min, default_lat_max)
            lat_range = st.slider("Latitude Limits", min_value=default_lat_min-2.0, max_value=default_lat_max+2.0, key='v_lat_range', step=0.1, label_visibility="collapsed")
        with c3: st.markdown("<div style='margin-top: 8px; font-size: 16px;'>Lon:</div>", unsafe_allow_html=True)
        with c4:
            if 'v_lon_range' not in st.session_state: st.session_state.v_lon_range = (default_lon_min, default_lon_max)
            lon_range = st.slider("Longitude Limits", min_value=default_lon_min-2.0, max_value=default_lon_max+2.0, key='v_lon_range', step=0.1, label_visibility="collapsed")
            
        st.markdown("""<style>[data-testid="stSidebar"] div[data-testid="stButton"] button p { font-size: 11px !important; } [data-testid="stSidebar"] div[data-testid="stButton"] button { padding: 0px 2px !important; min-height: 24px !important; }</style>""", unsafe_allow_html=True)
        st.markdown("<div style='margin-top: -10px;'></div>", unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔍 Auto-fit domain", use_container_width=True):
                cols_lower = {c.lower(): c for c in df_sel.columns}
                x_c = next((cols_lower[c] for c in ['lon', 'longitude'] if c in cols_lower), None)
                y_c = next((cols_lower[c] for c in ['lat', 'latitude'] if c in cols_lower), None)
                
                if x_c and y_c:
                    a_lat_min, a_lat_max = float(df_sel[y_c].min(skipna=True)), float(df_sel[y_c].max(skipna=True))
                    a_lon_min, a_lon_max = float(df_sel[x_c].min(skipna=True)), float(df_sel[x_c].max(skipna=True))
                    s_lat_min, s_lat_max = default_lat_min-2.0, default_lat_max+2.0
                    s_lon_min, s_lon_max = default_lon_min-2.0, default_lon_max+2.0
                    st.session_state._force_lat_range = (max(s_lat_min, a_lat_min - 0.1), min(s_lat_max, a_lat_max + 0.1))
                    st.session_state._force_lon_range = (max(s_lon_min, a_lon_min - 0.1), min(s_lon_max, a_lon_max + 0.1))
                    st.session_state._force_domain_fit = True
                    st.rerun()
                    
        with b2:
            if st.button("🔄 Reset domain", use_container_width=True):
                st.session_state._force_lat_range = (default_lat_min-2.0, default_lat_max+2.0)
                st.session_state._force_lon_range = (default_lon_min-2.0, default_lon_max+2.0)
                st.session_state._force_domain_fit = True
                st.rerun()

        domain_bounds = {'lat_min': lat_range[0], 'lat_max': lat_range[1], 'lon_min': lon_range[0], 'lon_max': lon_range[1]}
        
        vert_range = None
        if options:
            domain_z_col = target_col_3d
            v_unit_dom = decode_metadata(data_pack['var_attrs'].get(sel_group, {}).get(domain_z_col, {}).get('units', ''))
            convert_dom = 'Pa' in v_unit_dom and 'hPa' not in v_unit_dom
            if convert_dom: v_unit_dom = 'hPa'
            
            vert_vals = df_sel[domain_z_col].dropna().values
            if len(vert_vals) > 0:
                if convert_dom: vert_vals = vert_vals / 100.0
                zmin, zmax = float(np.nanmin(vert_vals)), float(np.nanmax(vert_vals))
                
                if is_3d and plot_track:
                    is_pres = convert_dom or any(p in domain_z_col.lower() for p in ['pres', 'pressure', 'p'])
                    if is_pres: zmax = max(zmax, 1015.0)  
                    else: zmin = min(zmin, 0.0)     
                        
                if zmin == zmax: zmax = zmin + 1.0
                
                v1, v2 = st.columns([1.0, 2.2])
                with v1: st.markdown(f"<div style='margin-top: 8px; font-size: 16px; color: {'inherit' if is_3d else '#999'};'>Vert ({v_unit_dom}):</div>", unsafe_allow_html=True)
                with v2: vert_range_ui = st.slider("Vertical Limits", min_value=zmin, max_value=zmax, value=(zmin, zmax), step=0.01, disabled=not is_3d, label_visibility="collapsed")
                
                if is_3d:
                    vert_range = vert_range_ui
                    domain_bounds['z_min'] = vert_range[0]
                    domain_bounds['z_max'] = vert_range[1]
                    domain_bounds['z_col'] = domain_z_col
                    domain_bounds['z_convert'] = convert_dom

    with st.sidebar.container(border=True):
        st.markdown("### ⏱️ Plot Time Limits")
        time_col = next((c for c in df_sel.columns if c.lower() in ['time', 'date', 'datetime', 'epoch']), None)
        time_bounds = None
        
        if time_col:
            valid_mask = df_sel[time_col] > 19000000000000.0
            dt_series = pd.to_datetime(df_sel.loc[valid_mask, time_col].apply(lambda x: f"{x:.0f}" if pd.notna(x) else None), format="%Y%m%d%H%M%S", errors='coerce').dropna()
            
            if not dt_series.empty:
                data_min_dt = dt_series.min().to_pydatetime()
                data_max_dt = dt_series.max().to_pydatetime()
                center_dt = data_min_dt + (data_max_dt - data_min_dt) / 2
                mission_start = center_dt - timedelta(hours=3)
                mission_end = center_dt + timedelta(hours=3)
                s_min_dt = min(data_min_dt - timedelta(minutes=1), mission_start)
                s_max_dt = max(data_max_dt + timedelta(minutes=1), mission_end)
                
                if st.session_state.pop('_force_time_fit', False): st.session_state.v_time_range = st.session_state.pop('_force_time_range')
                if 'v_time_range' not in st.session_state: st.session_state.v_time_range = (mission_start, mission_end)
                
                st.markdown("<div style='margin-top: 8px; font-size: 14px;'>Time Range (UTC):</div>", unsafe_allow_html=True)
                time_range = st.slider("Time Limits", min_value=s_min_dt, max_value=s_max_dt, key='v_time_range', format="HH:mm:ss", label_visibility="collapsed")
                
                st.markdown("<div style='margin-bottom: -15px;'></div>", unsafe_allow_html=True)
                tb1, tb2 = st.columns(2)
                
                with tb1:
                    if st.button("⏱️ Auto-fit time", use_container_width=True, key='btn_time_fit'):
                        cols_lower = {c.lower(): c for c in df_sel.columns}
                        x_c = next((cols_lower[c] for c in ['lon', 'longitude'] if c in cols_lower), None)
                        y_c = next((cols_lower[c] for c in ['lat', 'latitude'] if c in cols_lower), None)
                        
                        if x_c and y_c:
                            mask = (df_sel[y_c] >= domain_bounds['lat_min']) & (df_sel[y_c] <= domain_bounds['lat_max']) & (df_sel[x_c] >= domain_bounds['lon_min']) & (df_sel[x_c] <= domain_bounds['lon_max'])
                            visible_dt = dt_series.loc[mask]
                            st.session_state._force_time_range = (visible_dt.min().to_pydatetime(), visible_dt.max().to_pydatetime()) if not visible_dt.empty else (data_min_dt, data_max_dt)
                            st.session_state._force_time_fit = True
                            st.rerun()
                                
                with tb2:
                    if st.button("🔄 Reset time", use_container_width=True, key='btn_time_reset'):
                        st.session_state._force_time_range = (mission_start, mission_end)
                        st.session_state._force_time_fit = True
                        st.rerun()

                time_bounds = {'col': time_col, 'min': float(time_range[0].strftime("%Y%m%d%H%M%S")), 'max': float(time_range[1].strftime("%Y%m%d%H%M%S"))}
            else:
                st.warning("Time column exists, but all values are invalid or corrupted.")
        else:
            st.info("No time data available for this variable.")

    if variable:
        MAX_POINTS = 50000
        active_thinning = st.session_state.get('v_thin_pct', 50) if st.session_state.get('v_apply_thinning', False) else None
        valid_count = 0
        
        if 'TRACK' not in sel_group.upper() and variable in df_sel.columns:
            cols_lower = {c.lower(): c for c in df_sel.columns}
            x_c = next((cols_lower[c] for c in ['lon', 'longitude'] if c in cols_lower), None)
            y_c = next((cols_lower[c] for c in ['lat', 'latitude'] if c in cols_lower), None)
            
            req_cols = [x_c, y_c, variable]
            if plot_z_col and plot_z_col in df_sel.columns: req_cols.append(plot_z_col)
                
            if all(req_cols): 
                temp_df = df_sel.dropna(subset=req_cols)
                mask = (temp_df[y_c] >= lat_range[0]) & (temp_df[y_c] <= lat_range[1]) & (temp_df[x_c] >= lon_range[0]) & (temp_df[x_c] <= lon_range[1])
                if vert_range:
                    v_min, v_max = vert_range
                    v_vals = temp_df[domain_z_col] / 100.0 if convert_dom else temp_df[domain_z_col]
                    mask &= (v_vals >= v_min) & (v_vals <= v_max)
                valid_count = len(temp_df[mask])
                
            apply_thinning_val = st.session_state.get('v_apply_thinning', False)
            expected_points = int(valid_count * (st.session_state.get('v_thin_pct', 50) / 100.0)) if apply_thinning_val else valid_count
            
            if expected_points > MAX_POINTS and valid_count > 0:
                raw_safe_pct = (MAX_POINTS / valid_count) * 100
                st.session_state._force_thinning = True
                st.session_state._force_thin_pct = max(5, int(raw_safe_pct / 5) * 5) 
                st.session_state.show_auto_thin_msg = True
                st.rerun()

        if st.session_state.pop('show_auto_thin_msg', False):
            st.toast(f"⚡ **Auto-Thinning Applied!**\n\nDataset inside domain was too large. Automatically snapped thinning to **{st.session_state.v_thin_pct}%**.", icon="⚡")

        fig, plot_df = plotter.plot(
            sel_group, variable, z_con, domain_bounds, show_cen, 
            is_3d=is_3d, z_col=plot_z_col if can_do_3d else None, 
            thinning_pct=active_thinning, marker_size_pct=marker_sz,
            time_bounds=time_bounds 
        )
        
        if fig:
            is_target_pres = plot_z_col and any(p in plot_z_col.lower() for p in ['pres', 'pressure', 'p'])
            
            # --- Dynamically Inject Tracks via Plotter Helper ---
            fig = add_flight_tracks(fig, data_pack, track_mapping, plot_track, selected_platform, is_3d, is_target_pres)
            
            col_left, col_center, col_right = st.columns([1, 8, 1])
            with col_center:
                st.plotly_chart(fig, use_container_width=False)
                
    for k in list(st.session_state.keys()):
        if k.startswith('v_'): st.session_state.viewer_state[k] = st.session_state[k]
        