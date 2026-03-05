# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from config import EXPECTED_GROUPS
from data_utils import load_inventory_db
from ui_explorer_table import display_explorer_table

def render_explorer_tab():
    
    DB_PATH = "hrdobs_inventory_db.csv"
    if not os.path.exists(DB_PATH):
        st.warning(f"Database file `{DB_PATH}` not found. Please run your batch script to generate it!")
        return

    db_df = load_inventory_db(DB_PATH)
    has_vars = 'Observation_Variables' in db_df.columns
    MS_TO_KTS = 1.94384

    raw_min_i = float(db_df['Intensity_ms'].min(skipna=True))
    raw_max_i = float(db_df['Intensity_ms'].max(skipna=True))
    raw_min_p = float(db_df['MSLP_hPa'].min(skipna=True))
    raw_max_p = float(db_df['MSLP_hPa'].max(skipna=True))
    
    init_min_i, init_max_i = float(np.floor(raw_min_i)), float(np.ceil(raw_max_i))
    init_min_p, init_max_p = float(np.floor(raw_min_p)), float(np.ceil(raw_max_p))

    default_state = {
        'ui_years': [], 'ui_storms': [], 'ui_cats': [], 'ui_basins': [],
        'ui_groups': [], 'ui_vars': [], 
        'ui_unit': "m/s", 'prev_unit': "m/s",
        'ui_int': (init_min_i, init_max_i), 'ui_slp': (init_min_p, init_max_p),
        'ui_sort_col': 'Year', 'ui_sort_order': 'Ascending'
    }

    if 'explorer_state' not in st.session_state:
        st.session_state.explorer_state = {}

    for k, v in default_state.items():
        if k not in st.session_state:
            st.session_state[k] = st.session_state.explorer_state.get(k, v)

    def reset_all_filters():
        st.session_state.ui_years, st.session_state.ui_storms, st.session_state.ui_cats, st.session_state.ui_basins = [], [], [], []
        st.session_state.ui_groups, st.session_state.ui_vars = [], []
        current_mult = MS_TO_KTS if st.session_state.get('ui_unit', 'm/s') == "knots" else 1.0
        st.session_state.ui_int = (float(np.floor(raw_min_i * current_mult)), float(np.ceil(raw_max_i * current_mult)))
        st.session_state.ui_slp = (init_min_p, init_max_p)
        st.session_state.ui_sort_col = 'Year'
        st.session_state.ui_sort_order = 'Ascending'

    def reset_table_sort():
        st.session_state.ui_sort_col = 'Year'
        st.session_state.ui_sort_order = 'Ascending'

    def get_dropdown_mask(df, skip_filter=None):
        m = pd.Series(True, index=df.index)
        if skip_filter != 'Year' and st.session_state.ui_years: m &= df['Year'].isin(st.session_state.ui_years)
        if skip_filter != 'Storm' and st.session_state.ui_storms: m &= df['Storm'].isin(st.session_state.ui_storms)
        if skip_filter != 'TC_Category' and st.session_state.ui_cats: m &= df['TC_Category'].isin(st.session_state.ui_cats)
        if skip_filter != 'Basin' and st.session_state.ui_basins: m &= df['Basin'].isin(st.session_state.ui_basins)
        if skip_filter != 'Groups' and st.session_state.ui_groups:
            v_cols = [g for g in st.session_state.ui_groups if g in df.columns]
            if v_cols: m &= df[v_cols].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1) > 0
        if skip_filter != 'Vars' and st.session_state.ui_vars and has_vars:
            var_mask = df['Observation_Variables'].apply(lambda x: any(v in [s.strip() for s in str(x).split(',')] for v in st.session_state.ui_vars))
            m &= var_mask
        mult = 1/MS_TO_KTS if st.session_state.ui_unit == "knots" else 1.0
        if skip_filter != 'Intensity':
            m &= (df['Intensity_ms'] >= st.session_state.ui_int[0] * mult) & (df['Intensity_ms'] <= st.session_state.ui_int[1] * mult)
        if skip_filter != 'MSLP':
            m &= (df['MSLP_hPa'] >= st.session_state.ui_slp[0]) & (df['MSLP_hPa'] <= st.session_state.ui_slp[1])
        return m

    st.sidebar.markdown("### 🌍 Explorer Filters")
    with st.sidebar.container(border=True):
        st.markdown("#### Filter by Storm Information")
        filter_mappings = [
            ("Year", "ui_years", "Year", "Year"), ("Name", "ui_storms", "Storm", "Storm"), 
            ("Category", "ui_cats", "TC_Category", "TC_Category"), ("Storm Basin", "ui_basins", "Basin", "Basin")
        ]
        
        for label, key, col, skip_arg in filter_mappings:
            avail = sorted(db_df[get_dropdown_mask(db_df, skip_arg)][col].dropna().unique())
            st.session_state[key] = [x for x in st.session_state[key] if x in avail]
            st.multiselect(label, avail, key=key)
            
            cb1, cb2 = st.columns(2)
            cb1.button("Select All", type="secondary", use_container_width=True, on_click=lambda k=key, a=avail: st.session_state.update({k: a}), key=f"sa_{key}")
            cb2.button("Deselect All", type="secondary", use_container_width=True, on_click=lambda k=key: st.session_state.update({k: []}), key=f"da_{key}")
            st.markdown("<div style='height: 5px;'></div>", unsafe_allow_html=True)
        
        col_label, col_radio = st.columns([0.6, 1])
        with col_label: st.markdown("<p style='margin-top:5px; font-size: 16px;'>Intensity</p>", unsafe_allow_html=True)
        with col_radio: unit = st.radio("Unit", ["m/s", "knots"], key="ui_unit", label_visibility="collapsed", horizontal=True)

        mult = MS_TO_KTS if unit == "knots" else 1.0
        g_min_i_unit, g_max_i_unit = float(np.floor(raw_min_i * mult)), float(np.ceil(raw_max_i * mult))

        if st.session_state.ui_unit != st.session_state.prev_unit:
            c_low, c_high = st.session_state.ui_int
            old_mult = MS_TO_KTS if st.session_state.prev_unit == "knots" else 1.0
            old_g_min, old_g_max = float(np.floor(raw_min_i * old_mult)), float(np.ceil(raw_max_i * old_mult))
            new_low = (c_low * MS_TO_KTS) if unit == "knots" else (c_low / MS_TO_KTS)
            new_high = (c_high * MS_TO_KTS) if unit == "knots" else (c_high / MS_TO_KTS)
            
            if abs(c_low - old_g_min) < 0.1: new_low = g_min_i_unit
            if abs(c_high - old_g_max) < 0.1: new_high = g_max_i_unit
            
            st.session_state.ui_int = (new_low, new_high)
            st.session_state.prev_unit = unit
        
        i_df = db_df[get_dropdown_mask(db_df, 'Intensity')]
        t_min_i, t_max_i = (float(np.floor(i_df['Intensity_ms'].min()*mult)), float(np.ceil(i_df['Intensity_ms'].max()*mult))) if not i_df.empty else (g_min_i_unit, g_max_i_unit)
        st.session_state.ui_int = (max(t_min_i, min(st.session_state.ui_int[0], t_max_i)), max(t_min_i, min(st.session_state.ui_int[1], t_max_i)))
        st.slider("Intensity", min_value=g_min_i_unit, max_value=g_max_i_unit, step=(5.0 if unit == "knots" else 1.0), key="ui_int", label_visibility="collapsed")
        
        st.markdown("<p style='margin-bottom: -15px;'>MSLP (hPa)</p>", unsafe_allow_html=True)
        p_df = db_df[get_dropdown_mask(db_df, 'MSLP')]
        t_min_p, t_max_p = (float(np.floor(p_df['MSLP_hPa'].min())), float(np.ceil(p_df['MSLP_hPa'].max()))) if not p_df.empty else (init_min_p, init_max_p)
        st.session_state.ui_slp = (max(t_min_p, min(st.session_state.ui_slp[0], t_max_p)), max(t_min_p, min(st.session_state.ui_slp[1], t_max_p)))
        st.slider("MSLP", min_value=init_min_p, max_value=init_max_p, step=1.0, key="ui_slp", label_visibility="collapsed")

    with st.sidebar.container(border=True):
        st.markdown("#### Filter Rows by Group")
        df_groups = db_df[get_dropdown_mask(db_df, 'Groups')]
        avail_groups = sorted([g for g in EXPECTED_GROUPS if g in df_groups.columns and pd.to_numeric(df_groups[g], errors='coerce').fillna(0).sum() > 0])
        st.session_state.ui_groups = [x for x in st.session_state.ui_groups if x in avail_groups]
        st.multiselect("Contains group:", avail_groups, key="ui_groups")
        cg1, cg2 = st.columns(2)
        cg1.button("Select All", type="secondary", use_container_width=True, on_click=lambda a=avail_groups: st.session_state.update({"ui_groups": a}), key="sa_groups")
        cg2.button("Deselect All", type="secondary", use_container_width=True, on_click=lambda: st.session_state.update({"ui_groups": []}), key="da_groups")

    with st.sidebar.container(border=True):
        st.markdown("#### Filter Rows by Variable")
        df_vars = db_df[get_dropdown_mask(db_df, 'Vars')]
        avail_vars = sorted(list(set(v.strip() for v_str in df_vars['Observation_Variables'] if isinstance(v_str, str) for v in v_str.split(',') if v.strip() and v.strip().lower() != 'nan'))) if has_vars else []
        st.session_state.ui_vars = [x for x in st.session_state.ui_vars if x in avail_vars]
        st.multiselect("Contains variable:", avail_vars, key="ui_vars")
        cv1, cv2 = st.columns(2)
        cv1.button("Select All", type="secondary", use_container_width=True, on_click=lambda a=avail_vars: st.session_state.update({"ui_vars": a}), key="sa_vars")
        cv2.button("Deselect All", type="secondary", use_container_width=True, on_click=lambda: st.session_state.update({"ui_vars": []}), key="da_vars")

    st.sidebar.button("🔄 Reset All Filters", type="secondary", use_container_width=True, on_click=reset_all_filters)

    int_changed = (abs(st.session_state.ui_int[0] - g_min_i_unit) > 0.1) or (abs(st.session_state.ui_int[1] - g_max_i_unit) > 0.1)
    slp_changed = (abs(st.session_state.ui_slp[0] - init_min_p) > 0.1) or (abs(st.session_state.ui_slp[1] - init_max_p) > 0.1)

    if not any([bool(st.session_state.ui_years), bool(st.session_state.ui_storms), bool(st.session_state.ui_cats), bool(st.session_state.ui_basins), bool(st.session_state.ui_groups), bool(st.session_state.ui_vars), int_changed, slp_changed]):
        st.markdown("<div style='margin-top: 60px;'></div>", unsafe_allow_html=True)
        st.info("👈 **Ready to explore?**\nPlease make a selection from the filters to begin.")
        for k in default_state.keys():
            if k in st.session_state: st.session_state.explorer_state[k] = st.session_state[k]
        return  
    
    final_df = db_df[get_dropdown_mask(db_df, None)].copy()
    if final_df.empty:
        st.warning("No files match the current combination of filters.")
        return
        
    final_df['Lon'] = final_df['Lon'].abs()

    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown("#### 📄 Table Controls")
        sort_options = {"Year": "Year", "Storm Name": "Storm", "Basin": "Basin", "Cycle (Time)": "Cycle_Raw", "Latitude": "Lat", "Longitude": "Lon", "Intensity": "Intensity_ms", "MSLP": "MSLP_hPa", "Category": "TC_Category"}
        for g in EXPECTED_GROUPS:
            if g in final_df.columns: sort_options[g.replace('_', ' ').title()] = g
                
        sc1, sc2, sc3, sc4, sc5 = st.columns([1.6, 1.35, 0.7, 0.9, 1.5])
        with sc1: st.selectbox("Sort By Column:", list(sort_options.keys()), key="ui_sort_col")
        with sc2: st.radio("Sort Direction:", ["Ascending", "Descending"], key="ui_sort_order", horizontal=True)
        with sc3:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            st.button("🔄 Reset Sort", key="btn_reset_sort", type="secondary", use_container_width=True, on_click=reset_table_sort)
        
        active_col_key = st.session_state.get('ui_sort_col', 'Year')
        sort_col_internal = sort_options.get(active_col_key, 'Year')
        is_asc = (st.session_state.get('ui_sort_order', 'Ascending') == "Ascending")
        
        sort_cols = [sort_col_internal]
        asc_list = [is_asc]
        for tb in ['Year', 'Storm', 'Cycle_Raw']:
            if tb != sort_col_internal:
                sort_cols.append(tb); asc_list.append(True) 
                
        final_df = final_df.sort_values(by=sort_cols, ascending=asc_list)
        csv_data = final_df.to_csv(index=False).encode('utf-8')
        
        with sc5:
            st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
            st.download_button(label="⬇️ Download Results as CSV", data=csv_data, file_name=f"hrdobs_filtered_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime='text/csv', type="secondary", use_container_width=True)

        st.markdown("""
            <style>
            div[data-testid="stSelectbox"] label p, div[data-testid="stRadio"] label p { font-size: 16px !important; }
            div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] button[kind="secondary"],
            div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stDownloadButton"] button[kind="secondary"] {
                background-color: #555555 !important; color: white !important; border: 2px solid #555555 !important;
                padding: 0px 10px !important; min-height: 28px !important; height: 28px !important; border-radius: 6px !important;
            }
            div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stButton"] button p,
            div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stDownloadButton"] button p { font-size: 12px !important; color: white !important; }
            [data-testid="stHorizontalBlock"]:has([data-testid="stDownloadButton"]) { border-bottom: none !important; margin-bottom: 0px !important; }
            </style>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    st.markdown(f"#### 🔎 Found **{len(final_df)}** matching files")
    
    display_explorer_table(final_df, unit, sort_col_internal, is_asc)

    for k in default_state.keys():
        if k in st.session_state: st.session_state.explorer_state[k] = st.session_state[k]
        