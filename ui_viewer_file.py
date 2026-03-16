# -*- coding: utf-8 -*-
"""
ui_viewer_file.py
-----------------
File upload section, post-load data enrichment, and global domain computation
for the File Data Viewer tab.

Public API
----------
render_file_upload_section(data_pack_key, filename_key, state_keys, state_dict_key)
    Renders the sidebar file upload container and returns the resolved data_pack.

_inject_derived_fields(raw_data_pack)
    Post-load enrichment: adds SFMR altitude, derived wind speeds,
    propagated error estimates, and vector dummy variables in-place.

_compute_global_domain(data_pack)
    Scans all groups for lat/lon and stores a tight square bounding box
    in data_pack['global_domain'].
"""

import numpy as np
import streamlit as st

from config import EXPECTED_GROUPS, EXPECTED_META
from data_utils import load_data_from_h5, decode_metadata
from ui_layout import CLR_MUTED, CLR_SUCCESS, CLR_EXTRA, FS_TABLE, FS_BODY


def _inject_derived_fields(raw_data_pack):
    """
    Post-load enrichment: adds SFMR altitude, derived wind speeds,
    propagated error estimates, and vector dummy variables in-place.
    """
    for grp in raw_data_pack['data'].keys():
        df_grp = raw_data_pack['data'][grp]
        if grp not in raw_data_pack['var_attrs']:
            raw_data_pack['var_attrs'][grp] = {}

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

        wspd_hz = np.sqrt(u_vals**2 + v_vals**2)
        df_grp['wspd_hz_comp'] = wspd_hz
        raw_data_pack['var_attrs'][grp]['wspd_hz_comp'] = {
            'units': u_units, 'long_name': 'Horizontal Wind Speed (Computed)'
        }

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

        df_grp['wind_vec_hz'] = wspd_hz
        raw_data_pack['var_attrs'][grp]['wind_vec_hz'] = {
            'units': u_units, 'long_name': 'Horizontal Wind Vectors'
        }

        if not has_w:
            continue

        w_c    = cols_lower['w']
        w_vals = df_grp[w_c]

        wspd_3d = np.sqrt(u_vals**2 + v_vals**2 + w_vals**2)
        df_grp['wspd_3d_comp'] = wspd_3d
        raw_data_pack['var_attrs'][grp]['wspd_3d_comp'] = {
            'units': u_units, 'long_name': '3D Wind Speed (Computed)'
        }

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

        df_grp['wind_vec_3d'] = wspd_3d
        raw_data_pack['var_attrs'][grp]['wind_vec_3d'] = {
            'units': u_units, 'long_name': '3D Wind Vectors'
        }


def _compute_global_domain(data_pack):
    """
    Scans all groups for lat/lon and stores a tight square bounding box
    in data_pack['global_domain']. Called at file load; also safe to call
    lazily if missing.
    """
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


def render_file_upload_section(data_pack_key, filename_key, state_keys, state_dict_key):
    """
    Renders the file upload container and returns the resolved data_pack.
    """
    data_pack = st.session_state.get(data_pack_key)
    
    other_data_key = 'data_pack_analysis' if data_pack_key == 'data_pack' else 'data_pack'
    other_file_key = 'last_uploaded_filename_analysis' if filename_key == 'last_uploaded_filename' else 'last_uploaded_filename'
    
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
                            st.session_state[data_pack_key] = raw_data_pack
                            st.session_state[filename_key] = uploaded_file.name
                            
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
                st.session_state[f"cleared_{data_pack_key}"] = True 
                st.rerun()

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
    
