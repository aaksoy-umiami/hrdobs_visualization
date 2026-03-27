# -*- coding: utf-8 -*-
"""
ui_explorer_controls.py
-----------------------
All sidebar filter logic for the Global Dataset Explorer tab.
"""

import streamlit as st
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from config import (
    EXPECTED_GROUPS, MS_TO_KTS, 
    DEFAULT_INTENSITY_MIN, DEFAULT_INTENSITY_MAX, 
    DEFAULT_MSLP_MIN, DEFAULT_MSLP_MAX
)
from ui_layout import CLR_MUTED, FS_BODY
from ui_components import spacer, sidebar_label, multiselect_with_controls, section_divider, init_state, sync_namespace


@dataclass
class ExplorerIntent:
    unit:       str             = "m/s"
    years:      List            = field(default_factory=list)
    storms:     List            = field(default_factory=list)
    cats:       List            = field(default_factory=list)
    basins:     List            = field(default_factory=list)
    groups:     List            = field(default_factory=list)
    vars_:      List            = field(default_factory=list)
    int_range:  Tuple           = (DEFAULT_INTENSITY_MIN, DEFAULT_INTENSITY_MAX)
    slp_range:  Tuple           = (DEFAULT_MSLP_MIN, DEFAULT_MSLP_MAX)
    sort_col:   str             = "Year"
    sort_order: str             = "Ascending"
    g_min_i_unit: float         = DEFAULT_INTENSITY_MIN
    g_max_i_unit: float         = DEFAULT_INTENSITY_MAX
    init_min_p:   float         = DEFAULT_MSLP_MIN
    init_max_p:   float         = DEFAULT_MSLP_MAX

def get_dropdown_mask(df, skip_filters, has_vars):
    if isinstance(skip_filters, str): skip_filters = [skip_filters]
    elif skip_filters is None: skip_filters = []

    m    = pd.Series(True, index=df.index)
    mult = 1 / MS_TO_KTS if st.session_state.get('ui_unit') == "knots" else 1.0

    if 'Year' not in skip_filters and st.session_state.get('ui_years'): m &= df['Year'].isin(st.session_state.ui_years)
    if 'Storm' not in skip_filters and st.session_state.get('ui_storms'): m &= df['Storm'].isin(st.session_state.ui_storms)
    if 'TC_Category' not in skip_filters and st.session_state.get('ui_cats'): m &= df['TC_Category'].isin(st.session_state.ui_cats)
    if 'Basin' not in skip_filters and st.session_state.get('ui_basins'): m &= df['Basin'].isin(st.session_state.ui_basins)
    if 'Groups' not in skip_filters and st.session_state.get('ui_groups'):
        v_cols = [g for g in st.session_state.ui_groups if g in df.columns]
        if v_cols: m &= df[v_cols].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1) > 0
    if 'Vars' not in skip_filters and st.session_state.get('ui_vars') and has_vars:
        m &= df['Observation_Variables'].apply(lambda x: any(v in [s.strip() for s in str(x).split(',')] for v in st.session_state.ui_vars))
    if 'Intensity' not in skip_filters and 'ui_int' in st.session_state:
        m &= ((df['Intensity_ms'] >= st.session_state.ui_int[0] * mult) & (df['Intensity_ms'] <= st.session_state.ui_int[1] * mult))
    if 'MSLP' not in skip_filters and 'ui_slp' in st.session_state:
        m &= ((df['MSLP_hPa'] >= st.session_state.ui_slp[0]) & (df['MSLP_hPa'] <= st.session_state.ui_slp[1]))
    return m

def render_explorer_controls(db_df, has_vars, raw_min_i, raw_max_i, raw_min_p, raw_max_p) -> ExplorerIntent:
    init_min_i = float(np.floor(raw_min_i))
    init_max_i = float(np.ceil(raw_max_i))
    init_min_p = float(np.floor(raw_min_p))
    init_max_p = float(np.ceil(raw_max_p))

    default_state = {
        'ui_years': [], 'ui_storms': [], 'ui_cats': [], 'ui_basins': [],
        'ui_groups': [], 'ui_vars': [],
        'ui_unit': "m/s", 'prev_unit': "m/s",
        'ui_int': (init_min_i, init_max_i),
        'ui_slp': (init_min_p, init_max_p),
        'ui_sort_col': 'Year', 'ui_sort_order': 'Ascending',
    }

    init_state('explorer_state', {})
    for k, v in default_state.items():
        init_state(k, st.session_state.explorer_state.get(k, v))

    def reset_all_filters():
        st.session_state.ui_years  = []
        st.session_state.ui_storms = []
        st.session_state.ui_cats   = []
        st.session_state.ui_basins = []
        st.session_state.ui_groups = []
        st.session_state.ui_vars   = []
        cur_mult = MS_TO_KTS if st.session_state.get('ui_unit') == "knots" else 1.0
        st.session_state.ui_int = (float(np.floor(raw_min_i * cur_mult)), float(np.ceil(raw_max_i * cur_mult)))
        st.session_state.ui_slp  = (init_min_p, init_max_p)
        st.session_state.ui_sort_col   = 'Year'
        st.session_state.ui_sort_order = 'Ascending'
        st.session_state._last_t_min_i = float(np.floor(raw_min_i * cur_mult))
        st.session_state._last_t_max_i = float(np.ceil(raw_max_i * cur_mult))
        st.session_state._last_t_min_p = init_min_p
        st.session_state._last_t_max_p = init_max_p

    def reset_table_sort():
        st.session_state.ui_sort_col   = 'Year'
        st.session_state.ui_sort_order = 'Ascending'

    # UPDATED TITLE LINE HERE
    st.sidebar.markdown(f"### 🌍 Explorer Filters (for {len(db_df)} Total Files)")
    
    with st.sidebar.container(border=True):
        st.markdown("#### Filter by Storm Information")

        filter_mappings = [
            ("Year",        "ui_years",  "Year",        "Year"),
            ("Name",        "ui_storms", "Storm",       "Storm"),
            ("Category",    "ui_cats",   "TC_Category", "TC_Category"),
            ("Storm Basin", "ui_basins", "Basin",       "Basin"),
        ]
        for label, key, col, skip_arg in filter_mappings:
            avail = sorted(db_df[get_dropdown_mask(db_df, skip_arg, has_vars)][col].dropna().unique())
            multiselect_with_controls(label, avail, key)
            section_divider()

        col_label, col_radio = st.columns([0.6, 1])
        with col_label: sidebar_label('Intensity', size='label')
        with col_radio: unit = st.radio("Unit", ["m/s", "knots"], key="ui_unit", label_visibility="collapsed", horizontal=True)

        mult             = MS_TO_KTS if unit == "knots" else 1.0
        g_min_i_unit     = float(np.floor(raw_min_i * mult))
        g_max_i_unit     = float(np.ceil(raw_max_i  * mult))

        if st.session_state.ui_unit != st.session_state.prev_unit:
            c_low, c_high = st.session_state.ui_int
            old_mult      = MS_TO_KTS if st.session_state.prev_unit == "knots" else 1.0
            old_g_min     = float(np.floor(raw_min_i * old_mult))
            old_g_max     = float(np.ceil(raw_max_i  * old_mult))
            new_low       = c_low  * MS_TO_KTS if unit == "knots" else c_low  / MS_TO_KTS
            new_high      = c_high * MS_TO_KTS if unit == "knots" else c_high / MS_TO_KTS
            if abs(c_low  - old_g_min) < 0.1: new_low  = g_min_i_unit
            if abs(c_high - old_g_max) < 0.1: new_high = g_max_i_unit
            st.session_state.ui_int  = (new_low, new_high)
            st.session_state.prev_unit = unit
            
            last_min_old = st.session_state.get('_last_t_min_i', old_g_min)
            last_max_old = st.session_state.get('_last_t_max_i', old_g_max)
            st.session_state._last_t_min_i = last_min_old * MS_TO_KTS if unit == "knots" else last_min_old / MS_TO_KTS
            st.session_state._last_t_max_i = last_max_old * MS_TO_KTS if unit == "knots" else last_max_old / MS_TO_KTS

        slider_mask = get_dropdown_mask(db_df, ['Intensity', 'MSLP'], has_vars)
        slider_df   = db_df[slider_mask]

        t_min_i  = float(np.floor(slider_df['Intensity_ms'].min() * mult)) if not slider_df.empty else g_min_i_unit
        t_max_i  = float(np.ceil( slider_df['Intensity_ms'].max() * mult)) if not slider_df.empty else g_max_i_unit
        
        last_t_min_i = st.session_state.get('_last_t_min_i', g_min_i_unit)
        last_t_max_i = st.session_state.get('_last_t_max_i', g_max_i_unit)
        curr_val_i   = st.session_state.ui_int
        
        if curr_val_i[0] <= last_t_min_i + 0.1 and curr_val_i[1] >= last_t_max_i - 0.1:
            new_val_i = (t_min_i, t_max_i)
        else:
            new_val_i = (max(t_min_i, min(curr_val_i[0], t_max_i)), max(t_min_i, min(curr_val_i[1], t_max_i)))
            if new_val_i[0] > new_val_i[1]: new_val_i = (t_min_i, t_max_i)

        st.session_state.ui_int = new_val_i
        st.session_state._last_t_min_i = t_min_i
        st.session_state._last_t_max_i = t_max_i

        st.slider("Intensity", min_value=g_min_i_unit, max_value=g_max_i_unit, step=5.0 if unit == "knots" else 1.0, key="ui_int", label_visibility="collapsed")

        sidebar_label('MSLP (hPa)', size='label')
        t_min_p = float(np.floor(slider_df['MSLP_hPa'].min())) if not slider_df.empty else init_min_p
        t_max_p = float(np.ceil( slider_df['MSLP_hPa'].max())) if not slider_df.empty else init_max_p
        
        last_t_min_p = st.session_state.get('_last_t_min_p', init_min_p)
        last_t_max_p = st.session_state.get('_last_t_max_p', init_max_p)
        curr_val_p   = st.session_state.ui_slp
        
        if curr_val_p[0] <= last_t_min_p + 0.1 and curr_val_p[1] >= last_t_max_p - 0.1:
            new_val_p = (t_min_p, t_max_p)
        else:
            new_val_p = (max(t_min_p, min(curr_val_p[0], t_max_p)), max(t_min_p, min(curr_val_p[1], t_max_p)))
            if new_val_p[0] > new_val_p[1]: new_val_p = (t_min_p, t_max_p)

        st.session_state.ui_slp = new_val_p
        st.session_state._last_t_min_p = t_min_p
        st.session_state._last_t_max_p = t_max_p

        st.slider("MSLP", min_value=init_min_p, max_value=init_max_p, step=1.0, key="ui_slp", label_visibility="collapsed")

    with st.sidebar.container(border=True):
        st.markdown("#### Filter Rows by Group")
        df_groups    = db_df[get_dropdown_mask(db_df, 'Groups', has_vars)]
        avail_groups = sorted([g for g in EXPECTED_GROUPS if g in df_groups.columns and pd.to_numeric(df_groups[g], errors='coerce').fillna(0).sum() > 0])
        multiselect_with_controls('Contains group:', avail_groups, 'ui_groups')

    with st.sidebar.container(border=True):
        st.markdown("#### Filter Rows by Variable")
        df_vars    = db_df[get_dropdown_mask(db_df, 'Vars', has_vars)]
        avail_vars = (sorted(set(v.strip() for v_str in df_vars['Observation_Variables'] if isinstance(v_str, str) for v in v_str.split(',') if v.strip() and v.strip().lower() != 'nan')) if has_vars else [])
        multiselect_with_controls('Contains variable:', avail_vars, 'ui_vars')

    st.sidebar.button("🔄 Reset All Filters", type="secondary", width="stretch", on_click=reset_all_filters)

    sync_namespace('ui_', 'explorer_state')

    return ExplorerIntent(
        unit       = unit,
        years      = list(st.session_state.ui_years),
        storms     = list(st.session_state.ui_storms),
        cats       = list(st.session_state.ui_cats),
        basins     = list(st.session_state.ui_basins),
        groups     = list(st.session_state.ui_groups),
        vars_      = list(st.session_state.ui_vars),
        int_range  = tuple(st.session_state.ui_int),
        slp_range  = tuple(st.session_state.ui_slp),
        sort_col   = st.session_state.get('ui_sort_col',   'Year'),
        sort_order = st.session_state.get('ui_sort_order', 'Ascending'),
        g_min_i_unit = g_min_i_unit,
        g_max_i_unit = g_max_i_unit,
        init_min_p   = init_min_p,
        init_max_p   = init_max_p,
    )
