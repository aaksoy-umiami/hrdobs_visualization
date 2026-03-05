# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
import math
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
                            # 1. Load the raw data
                            raw_data_pack = load_data_from_h5(uploaded_file.getvalue())
                            
                            # 2. Inject artificial 10m altitude for SFMR & Compute Vectors
                            for grp in raw_data_pack['data'].keys():
                                df_grp = raw_data_pack['data'][grp]
                                if grp not in raw_data_pack['var_attrs']: raw_data_pack['var_attrs'][grp] = {}
                                
                                # -- SFMR Altitude --
                                if 'sfmr' in grp.lower():
                                    df_grp['altitude'] = 10.0
                                    raw_data_pack['var_attrs'][grp]['altitude'] = {'units': 'm', 'long_name': 'Assumed Observation Height'}
                                    
                                # -- Derived Wind Speeds & Errors --
                                cols_lower = {c.lower(): c for c in df_grp.columns}
                                has_u, has_v, has_w = 'u' in cols_lower, 'v' in cols_lower, 'w' in cols_lower
                                
                                def get_err_col(var_name):
                                    cands = [f"{var_name}err", f"{var_name}_err", f"{var_name}_error", f"{var_name}error"]
                                    return next((cols_lower[c] for c in cands if c in cols_lower), None)

                                if has_u and has_v:
                                    u_c, v_c = cols_lower['u'], cols_lower['v']
                                    u_vals, v_vals = df_grp[u_c], df_grp[v_c]
                                    
                                    wspd_hz = np.sqrt(u_vals**2 + v_vals**2)
                                    df_grp['wspd_hz_comp'] = wspd_hz
                                    u_units = raw_data_pack['var_attrs'][grp].get(u_c, {}).get('units', 'm/s')
                                    raw_data_pack['var_attrs'][grp]['wspd_hz_comp'] = {'units': u_units, 'long_name': 'Horizontal Wind Speed (Computed)'}
                                    
                                    # Propagate 2D Error
                                    u_err_c, v_err_c = get_err_col('u'), get_err_col('v')
                                    if u_err_c and v_err_c:
                                        u_err_vals, v_err_vals = df_grp[u_err_c], df_grp[v_err_c]
                                        
                                        # Check if base errors are constant
                                        u_err_const = np.isclose(np.nanmin(u_err_vals), np.nanmax(u_err_vals))
                                        v_err_const = np.isclose(np.nanmin(v_err_vals), np.nanmax(v_err_vals))
                                        
                                        if u_err_const and v_err_const:
                                            # Simpler RSS formula for constant errors
                                            hz_err = np.sqrt(u_err_vals**2 + v_err_vals**2)
                                            hz_err_name = 'Horizontal Wind Speed Error (Static Computed)'
                                        else:
                                            # Dynamic formula for varying errors
                                            hz_err = np.where(wspd_hz > 0, np.sqrt((u_vals * u_err_vals)**2 + (v_vals * v_err_vals)**2) / wspd_hz, 0.0)
                                            hz_err_name = 'Horizontal Wind Speed Error (Dynamic Computed)'
                                            
                                        df_grp['wspd_hz_comp_err'] = hz_err
                                        raw_data_pack['var_attrs'][grp]['wspd_hz_comp_err'] = {'units': u_units, 'long_name': hz_err_name}
                                    
                                    # ---> NEW: Inject 2D Vector Dummy Variable <---
                                    df_grp['wind_vec_hz'] = wspd_hz
                                    raw_data_pack['var_attrs'][grp]['wind_vec_hz'] = {'units': u_units, 'long_name': 'Horizontal Wind Vectors'}
                                    
                                    if has_w:
                                        w_c = cols_lower['w']
                                        w_vals = df_grp[w_c]
                                        
                                        wspd_3d = np.sqrt(u_vals**2 + v_vals**2 + w_vals**2)
                                        df_grp['wspd_3d_comp'] = wspd_3d
                                        raw_data_pack['var_attrs'][grp]['wspd_3d_comp'] = {'units': u_units, 'long_name': '3D Wind Speed (Computed)'}

                                        # Propagate 3D Error
                                        w_err_c = get_err_col('w')
                                        if u_err_c and v_err_c and w_err_c:
                                            w_err_vals = df_grp[w_err_c]
                                            
                                            w_err_const = np.isclose(np.nanmin(w_err_vals), np.nanmax(w_err_vals))
                                            
                                            if u_err_const and v_err_const and w_err_const:
                                                # Simpler RSS formula for constant errors
                                                err_3d = np.sqrt(u_err_vals**2 + v_err_vals**2 + w_err_vals**2)
                                                err_3d_name = '3D Wind Speed Error (Static Computed)'
                                            else:
                                                # Dynamic formula for varying errors
                                                err_3d = np.where(wspd_3d > 0, np.sqrt((u_vals * u_err_vals)**2 + (v_vals * v_err_vals)**2 + (w_vals * w_err_vals)**2) / wspd_3d, 0.0)
                                                err_3d_name = '3D Wind Speed Error (Dynamic Computed)'
                                                
                                            df_grp['wspd_3d_comp_err'] = err_3d
                                            raw_data_pack['var_attrs'][grp]['wspd_3d_comp_err'] = {'units': u_units, 'long_name': err_3d_name}
                                        
                                        # ---> NEW: Inject 3D Vector Dummy Variable <---
                                        df_grp['wind_vec_3d'] = wspd_3d
                                        raw_data_pack['var_attrs'][grp]['wind_vec_3d'] = {'units': u_units, 'long_name': '3D Wind Vectors'}
                                        
                            # 3. Save the modified pack to session state
                            st.session_state.data_pack = raw_data_pack
                            st.session_state.last_uploaded_filename = uploaded_file.name
                            
                            keys_to_clear = ['v_sel_group', 'v_variable', 'v_use_filter', 'v_vert_coord', 'v_lvl_range', 'v_is_3d', 'v_3d_z', 'v_plot_track', 'v_sel_plat', 'v_3d_ratio', 'v_apply_thinning', 'v_thin_pct', 'v_marker_size', 'v_lat_range', 'v_lon_range', 'v_time_range', 'v_show_cen', 'v_clat', 'v_clon', 'v_track_proj', 'v_vert_range', 'v_plot_err', 'v_vec_scale']
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
            
        def reset_group_dependencies():
            """Callback: Wipes memory of bounds that vary dramatically between datasets"""
            st.session_state.v_apply_thinning = False
            st.session_state.v_thin_pct = 50
            if 'show_auto_thin_msg' in st.session_state: st.session_state.show_auto_thin_msg = False
            
            for k in ['v_lvl_range', 'v_time_range', 'v_last_coord', 'v_vert_range', 'v_plot_err', 'v_vec_scale']:
                if k in st.session_state: del st.session_state[k]

        def reset_var_dependencies():
            """Callback: Uncheck the error box if we switch to a new variable"""
            if 'v_plot_err' in st.session_state: del st.session_state['v_plot_err']

        sel_group = st.selectbox("Select Active Group to Plot", available_groups, key='v_sel_group', on_change=reset_group_dependencies)
        h_col, p_col = None, None
        
        if 'TRACK' not in sel_group.upper():
            df_sel = data_pack['data'][sel_group]
            cols_lower = {c.lower(): c for c in df_sel.columns}
            h_col = next((cols_lower[c] for c in ['height', 'ght', 'altitude', 'elev'] if c in cols_lower), None)
            p_col = next((cols_lower[c] for c in ['pres', 'pressure', 'p'] if c in cols_lower), None)

        exclude_col = st.session_state.get('v_vert_coord', None) if st.session_state.get('v_use_filter', False) else None
        vars_list = plotter.get_plottable_variables(sel_group, active_z_col=exclude_col)

        plot_var = None
        if 'TRACK' in sel_group.upper(): 
            variable = 'Path'
            plot_var = variable
        elif vars_list: 
            if 'v_variable' not in st.session_state or st.session_state.v_variable not in vars_list:
                st.session_state.v_variable = vars_list[0]
            variable = st.selectbox(
                "Variable", 
                vars_list, 
                key='v_variable', 
                on_change=reset_var_dependencies,
                format_func=lambda x: plotter._get_var_display_name(sel_group, x) # <--- Formats the dropdown nicely!
            )
            
            # ---> NEW: SMART ERROR FIELD DETECTION <---
            plot_var = variable
            var_lower = variable.lower()
            err_candidates = [f"{var_lower}err", f"{var_lower}_err", f"{var_lower}_error", f"{var_lower}error"]
            actual_err_col = next((cols_lower[c] for c in err_candidates if c in cols_lower), None)
            
            # Change checkbox label if this is a derived variable
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
                        if 'v_plot_err' not in st.session_state: st.session_state.v_plot_err = False
                        if st.checkbox(err_lbl, key='v_plot_err'):
                            plot_var = actual_err_col
            else:
                st.checkbox(err_lbl, disabled=True, value=False, key=f"err_miss_{variable}")
                
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
        
        z_con, target_col = None, None 
        options = [c for c in [h_col, p_col] if c]
        
        # ---> NEW: Force filter off if no vertical coordinates exist <---
        if not options and st.session_state.get('v_use_filter', False):
            st.session_state.v_use_filter = False
            
        if 'v_use_filter' not in st.session_state: st.session_state.v_use_filter = False
        use_filter = st.checkbox("Filter by Level?", key='v_use_filter', disabled=not options)
        f_color = "inherit" if use_filter else "#999"

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
                    else:
                        c_min, c_max = st.session_state.v_lvl_range
                        c_min = max(dmin, min(c_min, dmax))
                        c_max = max(dmin, min(c_max, dmax))
                        if c_min > c_max: c_min = c_max
                        st.session_state.v_lvl_range = (c_min, c_max)

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
            
        p_c1, p_c2 = st.columns([1.4, 1])
        with p_c1:
            is_3d_state = st.session_state.get('v_is_3d', False)
            proj_disabled = not (plot_track and is_3d_state)
            p_color = "inherit" if not proj_disabled else "#999"
            st.markdown(f"<div style='margin-top: 8px; font-size: 13px; font-weight: 500; color: {p_color};'>Display track projection:</div>", unsafe_allow_html=True)
        with p_c2:
            if 'v_track_proj' not in st.session_state: st.session_state.v_track_proj = "Bottom Only"
            track_proj = st.selectbox("Projection", ["None", "Bottom Only", "Sides Only", "Bottom + Sides"], key='v_track_proj', disabled=proj_disabled, label_visibility="collapsed")
        
        st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)

        can_do_3d = (h_col is not None or p_col is not None)
        
        # ---> NEW: Force 3D mode off if the dataset is strictly 2D <---
        if not can_do_3d and st.session_state.get('v_is_3d', False):
            st.session_state.v_is_3d = False
            
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

        # ---> NEW: Contextual Size Slider (Vector vs Scalar) <---
        m1, m2 = st.columns([1.1, 2.2])
        is_vector = plot_var and "wind_vec" in plot_var.lower()
        
        with m1: 
            lbl = "Vector Scale:" if is_vector else "Marker Size:"
            st.markdown(f"<div style='margin-top: 12px; font-size: 16px;'>{lbl}</div>", unsafe_allow_html=True)
            
        with m2:
            if is_vector:
                if 'v_vec_scale' not in st.session_state: st.session_state.v_vec_scale = 1.0
                vec_scale = st.slider("Vector Scale", min_value=0.1, max_value=5.0, step=0.1, key='v_vec_scale', label_visibility="collapsed")
                marker_sz = 100 # Feed default marker size to backend safely
            else:
                if 'v_marker_size' not in st.session_state: st.session_state.v_marker_size = 100
                marker_sz = st.slider("Marker Size", min_value=10, max_value=200, step=10, format="%d%%", key='v_marker_size', label_visibility="collapsed")
                vec_scale = 1.0 # Feed default vec scale to backend safely

    with st.sidebar.container(border=True):
        st.markdown("### 🗺️ Plot Domain Limits")
        
        if st.session_state.pop('_force_domain_fit', False):
            st.session_state.v_lat_range = st.session_state.pop('_force_lat_range')
            st.session_state.v_lon_range = st.session_state.pop('_force_lon_range')
            if '_force_z_range' in st.session_state:
                st.session_state.v_vert_range = st.session_state.pop('_force_z_range')
        
        if st.session_state.pop('_reset_z_range', False):
            if 'v_vert_range' in st.session_state: del st.session_state['v_vert_range']
        
        c1, c2, c3, c4 = st.columns([0.7, 2.0, 0.7, 2.0])
        with c1: st.markdown("<div style='margin-top: 8px; font-size: 16px;'>Lat:</div>", unsafe_allow_html=True)
        with c2:
            if 'v_lat_range' not in st.session_state: st.session_state.v_lat_range = (default_lat_min, default_lat_max)
            lat_range = st.slider("Latitude Limits", min_value=default_lat_min-2.0, max_value=default_lat_max+2.0, key='v_lat_range', step=0.1, label_visibility="collapsed")
        with c3: st.markdown("<div style='margin-top: 8px; font-size: 16px;'>Lon:</div>", unsafe_allow_html=True)
        with c4:
            if 'v_lon_range' not in st.session_state: st.session_state.v_lon_range = (default_lon_min, default_lon_max)
            lon_range = st.slider("Longitude Limits", min_value=default_lon_min-2.0, max_value=default_lon_max+2.0, key='v_lon_range', step=0.1, label_visibility="collapsed")
            
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
                
                is_pres = convert_dom or any(p in domain_z_col.lower() for p in ['pres', 'pressure', 'p'])
                if is_pres:
                    zmin_global = float(max(0.0, math.floor(np.nanmin(vert_vals) / 50.0) * 50.0))
                    zmax_global = float(max(1015.0, math.ceil(np.nanmax(vert_vals) / 50.0) * 50.0))
                else:
                    zmin_global = 0.0
                    zmax_global = float(math.ceil(np.nanmax(vert_vals) / 1000.0) * 1000.0)
                    if zmax_global == 0.0: zmax_global = 1000.0
                    
                if zmin_global >= zmax_global: zmax_global = zmin_global + 1.0
                
                if 'v_vert_range' not in st.session_state:
                    st.session_state.v_vert_range = (zmin_global, zmax_global)
                else:
                    c_min, c_max = st.session_state.v_vert_range
                    c_min = max(zmin_global, min(c_min, zmax_global))
                    c_max = max(zmin_global, min(c_max, zmax_global))
                    if c_min > c_max: c_min = c_max
                    st.session_state.v_vert_range = (c_min, c_max)

                v1, v2 = st.columns([1.0, 2.2])
                with v1: st.markdown(f"<div style='margin-top: 8px; font-size: 16px; color: {'inherit' if is_3d else '#999'};'>Vert ({v_unit_dom}):</div>", unsafe_allow_html=True)
                with v2: vert_range_ui = st.slider("Vertical Limits", min_value=zmin_global, max_value=zmax_global, key='v_vert_range', step=0.01, disabled=not is_3d, label_visibility="collapsed")
                
                if is_3d:
                    vert_range = vert_range_ui
                    domain_bounds['z_min'] = vert_range[0]
                    domain_bounds['z_max'] = vert_range[1]
                    domain_bounds['z_col'] = domain_z_col
                    domain_bounds['z_convert'] = convert_dom
                    
        st.markdown("""<style>[data-testid="stSidebar"] div[data-testid="stButton"] button p { font-size: 11px !important; } [data-testid="stSidebar"] div[data-testid="stButton"] button { padding: 0px 2px !important; min-height: 24px !important; }</style>""", unsafe_allow_html=True)
        
        b1, b2 = st.columns(2)
        with b1:
            if st.button("🔍 Auto-fit domain", use_container_width=True):
                temp_df = df_sel.copy()
                if st.session_state.get('v_use_filter', False) and 'v_vert_coord' in st.session_state and 'v_lvl_range' in st.session_state:
                    t_col = st.session_state.v_vert_coord
                    if t_col in temp_df.columns:
                        vmin, vmax = st.session_state.v_lvl_range
                        v_unit = decode_metadata(data_pack['var_attrs'].get(sel_group, {}).get(t_col, {}).get('units', ''))
                        convert = 'Pa' in v_unit and 'hPa' not in v_unit
                        t_vals = temp_df[t_col] / 100.0 if convert else temp_df[t_col]
                        temp_df = temp_df[(t_vals >= vmin) & (t_vals <= vmax)]
                        
                time_col = next((c for c in temp_df.columns if c.lower() in ['time', 'date', 'datetime', 'epoch']), None)
                if time_col and 'v_time_range' in st.session_state:
                    try:
                        t_min_dt, t_max_dt = st.session_state.v_time_range
                        t_min_float = float(t_min_dt.strftime("%Y%m%d%H%M%S"))
                        t_max_float = float(t_max_dt.strftime("%Y%m%d%H%M%S"))
                        temp_df = temp_df[(temp_df[time_col] >= t_min_float) & (temp_df[time_col] <= t_max_float)]
                    except:
                        pass
                
                cols_lower = {c.lower(): c for c in temp_df.columns}
                x_c = next((cols_lower[c] for c in ['lon', 'longitude'] if c in cols_lower), None)
                y_c = next((cols_lower[c] for c in ['lat', 'latitude'] if c in cols_lower), None)
                
                if x_c and y_c and not temp_df.empty:
                    a_lat_min, a_lat_max = float(temp_df[y_c].min(skipna=True)), float(temp_df[y_c].max(skipna=True))
                    a_lon_min, a_lon_max = float(temp_df[x_c].min(skipna=True)), float(temp_df[x_c].max(skipna=True))
                    
                    lat_span = max(a_lat_max - a_lat_min, 0.05)
                    lon_span = max(a_lon_max - a_lon_min, 0.05)
                    buf_lat = lat_span * 0.05
                    buf_lon = lon_span * 0.05
                    
                    s_lat_min, s_lat_max = default_lat_min-2.0, default_lat_max+2.0
                    s_lon_min, s_lon_max = default_lon_min-2.0, default_lon_max+2.0
                    
                    st.session_state._force_lat_range = (max(s_lat_min, a_lat_min - buf_lat), min(s_lat_max, a_lat_max + buf_lat))
                    st.session_state._force_lon_range = (max(s_lon_min, a_lon_min - buf_lon), min(s_lon_max, a_lon_max + buf_lon))
                    
                    if st.session_state.get('v_is_3d') and target_col_3d and target_col_3d in temp_df.columns:
                        z_vals = temp_df[target_col_3d].dropna()
                        if not z_vals.empty:
                            v_unit_fit = decode_metadata(data_pack['var_attrs'].get(sel_group, {}).get(target_col_3d, {}).get('units', ''))
                            conv_fit = 'Pa' in v_unit_fit and 'hPa' not in v_unit_fit
                            z_vals_fit = z_vals / 100.0 if conv_fit else z_vals
                            
                            a_z_min, a_z_max = float(z_vals_fit.min()), float(z_vals_fit.max())
                            z_span_fit = max(a_z_max - a_z_min, 1.0)
                            buf_z = z_span_fit * 0.05
                            st.session_state._force_z_range = (a_z_min - buf_z, a_z_max + buf_z)

                    st.session_state._force_domain_fit = True
                    st.rerun()
                else:
                    st.toast("⚠️ No data available in current time/level window to fit.", icon="⚠️")
                    
        with b2:
            if st.button("🔄 Reset domain", use_container_width=True):
                st.session_state._force_lat_range = (default_lat_min-2.0, default_lat_max+2.0)
                st.session_state._force_lon_range = (default_lon_min-2.0, default_lon_max+2.0)
                st.session_state._force_domain_fit = True
                st.session_state._reset_z_range = True
                st.rerun()

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
                
                exact_center_dt = data_min_dt + (data_max_dt - data_min_dt) / 2
                center_dt = (exact_center_dt + timedelta(minutes=30)).replace(minute=0, second=0, microsecond=0)
                
                mission_start = center_dt - timedelta(hours=3)
                mission_end = center_dt + timedelta(hours=3)
                s_min_dt = min(data_min_dt - timedelta(minutes=1), mission_start)
                s_max_dt = max(data_max_dt + timedelta(minutes=1), mission_end)
                
                if st.session_state.pop('_force_time_fit', False): 
                    st.session_state.v_time_range = st.session_state.pop('_force_time_range')
                elif 'v_time_range' not in st.session_state: 
                    st.session_state.v_time_range = (mission_start, mission_end)
                else:
                    t_c_min, t_c_max = st.session_state.v_time_range
                    t_c_min = max(s_min_dt, min(t_c_min, s_max_dt))
                    t_c_max = max(s_min_dt, min(t_c_max, s_max_dt))
                    if t_c_min > t_c_max: t_c_min = t_c_max
                    st.session_state.v_time_range = (t_c_min, t_c_max)
                
                # ---> FIX: Changed font size to 16px here! <---
                st.markdown("<div style='margin-top: 8px; font-size: 16px;'>Time Range (UTC):</div>", unsafe_allow_html=True)
                time_range = st.slider("Time Limits", min_value=s_min_dt, max_value=s_max_dt, key='v_time_range', format="HH:mm:ss", label_visibility="collapsed")
                
                tb1, tb2 = st.columns(2)
                
                with tb1:
                    if st.button("⏱️ Auto-fit time", use_container_width=True, key='btn_time_fit'):
                        temp_df = df_sel.copy()
                        
                        if st.session_state.get('v_use_filter', False) and 'v_vert_coord' in st.session_state and 'v_lvl_range' in st.session_state:
                            t_col = st.session_state.v_vert_coord
                            if t_col in temp_df.columns:
                                vmin, vmax = st.session_state.v_lvl_range
                                v_unit = decode_metadata(data_pack['var_attrs'].get(sel_group, {}).get(t_col, {}).get('units', ''))
                                convert = 'Pa' in v_unit and 'hPa' not in v_unit
                                t_vals = temp_df[t_col] / 100.0 if convert else temp_df[t_col]
                                temp_df = temp_df[(t_vals >= vmin) & (t_vals <= vmax)]
                                
                        cols_lower = {c.lower(): c for c in temp_df.columns}
                        x_c = next((cols_lower[c] for c in ['lon', 'longitude'] if c in cols_lower), None)
                        y_c = next((cols_lower[c] for c in ['lat', 'latitude'] if c in cols_lower), None)
                        
                        if x_c and y_c:
                            mask = (temp_df[y_c] >= domain_bounds['lat_min']) & (temp_df[y_c] <= domain_bounds['lat_max']) & (temp_df[x_c] >= domain_bounds['lon_min']) & (temp_df[x_c] <= domain_bounds['lon_max'])
                            temp_df = temp_df[mask]
                            
                            if not temp_df.empty:
                                visible_dt = pd.to_datetime(temp_df[time_col].apply(lambda x: f"{x:.0f}"), format="%Y%m%d%H%M%S", errors='coerce').dropna()
                                if not visible_dt.empty:
                                    st.session_state._force_time_range = (visible_dt.min().to_pydatetime(), visible_dt.max().to_pydatetime())
                                    st.session_state._force_time_fit = True
                                    st.rerun()
                                    
                        st.toast("⚠️ No data remaining in current Domain/Level to fit.", icon="⚠️")
                                
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

    if plot_var:
        MAX_POINTS = 50000
        active_thinning = st.session_state.get('v_thin_pct', 50) if st.session_state.get('v_apply_thinning', False) else None
        valid_count = 0
        
        if 'TRACK' not in sel_group.upper() and plot_var in df_sel.columns:
            cols_lower = {c.lower(): c for c in df_sel.columns}
            x_c = next((cols_lower[c] for c in ['lon', 'longitude'] if c in cols_lower), None)
            y_c = next((cols_lower[c] for c in ['lat', 'latitude'] if c in cols_lower), None)
            
            req_cols = [x_c, y_c, plot_var]
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
            sel_group, plot_var, z_con, domain_bounds, show_cen, 
            is_3d=is_3d, z_col=plot_z_col if can_do_3d else None, 
            thinning_pct=active_thinning, marker_size_pct=marker_sz,
            time_bounds=time_bounds,
            z_ratio=st.session_state.get('v_3d_ratio', 0.3),
            vec_scale=vec_scale
        )
        
        if fig:
            is_target_pres = plot_z_col and any(p in plot_z_col.lower() for p in ['pres', 'pressure', 'p'])
            
            track_proj = st.session_state.get('v_track_proj', 'Bottom Only')
            fig = add_flight_tracks(fig, data_pack, track_mapping, plot_track, selected_platform, is_3d, is_target_pres, track_proj, domain_bounds)
            
            col_left, col_center, col_right = st.columns([1, 8, 1])
            with col_center:
                st.plotly_chart(fig, use_container_width=False)
                
    for k in list(st.session_state.keys()):
        if k.startswith('v_'): st.session_state.viewer_state[k] = st.session_state[k]
        