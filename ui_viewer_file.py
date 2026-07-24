# -*- coding: utf-8 -*-
"""
Purpose:
    Provides the file loading and metadata inspection interface for the File Data Viewer and Statistical Analysis tabs.

Functions/Classes:
    - render_file_upload_section: Renders the file loading container, supporting manual upload and retrieval of a Dataset Explorer result from the online archive, and handles cross-tab data inheritance.
"""

import streamlit as st
import pandas as pd

from config import EXPECTED_GROUPS, EXPECTED_META, SUPPRESSED_META, SHIPS_PREDICTOR_META
from data_utils import (
    load_data_from_h5, 
    decode_metadata, 
    inject_derived_fields, 
    compute_global_domain, 
    compute_vert_bounds,
    fetch_hrdobs_file_from_ftp,
)
from ui_layout import CLR_MUTED, CLR_SUCCESS, CLR_EXTRA, FS_TABLE, FS_BODY


def render_file_upload_section(data_pack_key, filename_key, state_keys, state_dict_key):
    """
    Renders the file loading container, supporting manual upload and retrieval of a Dataset Explorer result from the online archive, and handles cross-tab data inheritance.
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
            st.markdown("**Option 1:** Manual upload")
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
                            inject_derived_fields(raw_data_pack)
                            compute_global_domain(raw_data_pack)
                            compute_vert_bounds(raw_data_pack)
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

            explorer_files = st.session_state.get('explorer_available_files', [])
            explorer_row_lookup = st.session_state.get('explorer_row_lookup', {})
            explorer_select_key = f"explorer_quick_load_{data_pack_key}"

            st.markdown("**Option 2:** Load online from Dataset Explorer filtered results:")

            if explorer_files:
                # Drop a stored selection that is no longer among the current
                # results, which would otherwise be an invalid selectbox option.
                if st.session_state.get(explorer_select_key) not in explorer_files:
                    st.session_state.pop(explorer_select_key, None)

                col_sel, col_btn = st.columns([2, 1])
                with col_sel:
                    selected_explorer_file = st.selectbox(
                        "Select from filtered results:",
                        explorer_files,
                        format_func=lambda fname: f"#{explorer_row_lookup.get(fname, '?')} — {fname}",
                        label_visibility="collapsed",
                        key=explorer_select_key,
                    )
                with col_btn:
                    do_fetch = st.button("Load", key=f"explorer_fetch_btn_{data_pack_key}",
                                         type="primary", width="stretch")

                if do_fetch:
                    with st.spinner(f"Fetching {selected_explorer_file} from HRD Archive..."):
                        try:
                            file_bytes = fetch_hrdobs_file_from_ftp(selected_explorer_file)
                            raw_data_pack = load_data_from_h5(file_bytes)
                            inject_derived_fields(raw_data_pack)
                            compute_global_domain(raw_data_pack)
                            compute_vert_bounds(raw_data_pack)

                            st.session_state[data_pack_key] = raw_data_pack
                            st.session_state[filename_key] = selected_explorer_file

                            st.session_state.pop('cleared_data_pack', None)
                            st.session_state.pop('cleared_data_pack_analysis', None)

                            for k in state_keys:
                                st.session_state.pop(k, None)
                            st.session_state[state_dict_key] = {}
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to fetch file: {e}")
            else:
                st.caption(
                    "No Dataset Explorer results yet — apply filters on the "
                    "**Dataset Explorer** tab to populate this list."
                )
                if st.button("Go to Dataset Explorer", key=f"goto_explorer_{data_pack_key}", width="stretch"):
                    st.session_state.selected_tab_index = 0
                    st.rerun()
        else:
            st.success(f"📂 **File Loaded to Memory:**\n{st.session_state.get(filename_key, 'Unknown')}")
            if st.button("🗑️ Clear Memory & Load New File", key=f"clear_{data_pack_key}", width="stretch"):
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
                          if k not in EXPECTED_META and k not in SUPPRESSED_META]:
                    val = decode_metadata(current_pack['meta']['info'][m])
                    meta_html += (
                        f"<tr><td style='padding: 6px; color: blue;'>"
                        f"<i>{m} (Extra)</i></td>"
                        f"<td style='padding: 6px; color: blue;'>{val}</td></tr>"
                    )
                meta_html += "</table>"
                st.markdown(meta_html, unsafe_allow_html=True)

            with st.expander("🛳️ View SHIPS Parameters", expanded=False):
                ships_html = f"<div style='font-size: {FS_BODY}px; line-height: 1.6; padding: 5px;'>"
                
                if 'ships_params' in current_pack['data'] and not current_pack['data']['ships_params'].empty:
                    ships_df = current_pack['data']['ships_params']
                    ships_html += (
                        f"<table style='font-size: {FS_TABLE}px; width: 100%; text-align: left; "
                        "border-collapse: collapse;'>"
                        "<tr style='border-bottom: 2px solid #ddd;'>"
                        "<th style='padding: 8px;'>Parameter</th>"
                        "<th style='padding: 8px;'>Value</th>"
                        "<th style='padding: 8px;'>Units</th></tr>"
                    )
                    
                    for col in ships_df.columns:
                        val = ships_df[col].iloc[0]
                        if pd.isna(val):
                            val_str = "<span style='color: red;'>NaN</span>"
                        elif isinstance(val, (int, float)):
                            val_str = f"{val:.2f}" if val % 1 != 0 else f"{int(val)}"
                        else:
                            val_str = str(val)
                            
                        if col in SHIPS_PREDICTOR_META:
                            units = SHIPS_PREDICTOR_META[col][0]
                            long_name = SHIPS_PREDICTOR_META[col][1]
                        else:
                            units = current_pack['var_attrs'].get('ships_params', {}).get(col, {}).get('units', '')
                            long_name = current_pack['var_attrs'].get('ships_params', {}).get(col, {}).get('long_name', '')
                        
                        if long_name:
                            col_display = f"<span title='{long_name}' style='cursor:help; border-bottom: 1px dotted #ccc;'>{col}</span>"
                        else:
                            col_display = str(col)
                        
                        ships_html += (
                            f"<tr><td style='padding: 6px;'><b>{col_display}</b></td>"
                            f"<td style='padding: 6px;'>{val_str}</td>"
                            f"<td style='padding: 6px; color: gray;'>{units}</td></tr>"
                        )
                else:
                    ships_html += f"<span style='color: {CLR_MUTED};'><i>No SHIPS data for this cycle</i></span>"
                    
                ships_html += "</div>"
                st.markdown(ships_html, unsafe_allow_html=True)

    return st.session_state.get(data_pack_key)