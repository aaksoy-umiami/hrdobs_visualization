# -*- coding: utf-8 -*-
"""
ui_viewer_file.py
-----------------
File upload section for the File Data Viewer tab.
"""

import streamlit as st

from config import EXPECTED_GROUPS, EXPECTED_META
from data_utils import (
    load_data_from_h5, 
    decode_metadata, 
    inject_derived_fields, 
    compute_global_domain, 
    compute_vert_bounds
)
from ui_layout import CLR_MUTED, CLR_SUCCESS, CLR_EXTRA, FS_TABLE, FS_BODY


def render_file_upload_section(data_pack_key, filename_key, state_keys, state_dict_key):
    """
    Renders the file upload container and returns the resolved data_pack.
    """
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
                            inject_derived_fields(raw_data_pack)
                            compute_global_domain(raw_data_pack)
                            compute_vert_bounds(raw_data_pack)
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
