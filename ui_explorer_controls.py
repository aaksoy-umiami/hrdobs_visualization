# -*- coding: utf-8 -*-
"""
ui_explorer_controls.py
-----------------------
All sidebar filter logic for the Global Dataset Explorer tab.

render_explorer_controls() renders every sidebar section and returns an
ExplorerIntent dataclass that the caller (ui_explorer.py) uses to filter
the inventory and render the results table.
"""

import streamlit as st
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

from config import EXPECTED_GROUPS
from ui_layout import CLR_MUTED, FS_BODY
from ui_components import spacer, sidebar_label, multiselect_with_controls, section_divider

# Conversion constant kept here so both files share the same value
MS_TO_KTS = 1.94384


# ---------------------------------------------------------------------------
# Return type
# ---------------------------------------------------------------------------

@dataclass
class ExplorerIntent:
    """Plain data object produced by the sidebar controls."""
    unit:       str             = "m/s"
    years:      List            = field(default_factory=list)
    storms:     List            = field(default_factory=list)
    cats:       List            = field(default_factory=list)
    basins:     List            = field(default_factory=list)
    groups:     List            = field(default_factory=list)
    vars_:      List            = field(default_factory=list)
    int_range:  Tuple           = (0.0, 100.0)
    slp_range:  Tuple           = (900.0, 1020.0)
    sort_col:   str             = "Year"
    sort_order: str             = "Ascending"
    # Raw global bounds — needed by the main tab for change detection
    g_min_i_unit: float         = 0.0
    g_max_i_unit: float         = 100.0
    init_min_p:   float         = 900.0
    init_max_p:   float         = 1020.0


# ---------------------------------------------------------------------------
# Cascade mask — shared by sidebar (for dynamic dropdown options) and by
# the main tab (for final filtering).  Defined here so it lives beside the
# state it depends on.
# ---------------------------------------------------------------------------

def get_dropdown_mask(df, skip_filter, has_vars):
    """Return a boolean Series respecting all active filters except skip_filter."""
    m    = pd.Series(True, index=df.index)
    mult = 1 / MS_TO_KTS if st.session_state.get('ui_unit') == "knots" else 1.0

    if skip_filter != 'Year'        and st.session_state.ui_years:
        m &= df['Year'].isin(st.session_state.ui_years)
    if skip_filter != 'Storm'       and st.session_state.ui_storms:
        m &= df['Storm'].isin(st.session_state.ui_storms)
    if skip_filter != 'TC_Category' and st.session_state.ui_cats:
        m &= df['TC_Category'].isin(st.session_state.ui_cats)
    if skip_filter != 'Basin'       and st.session_state.ui_basins:
        m &= df['Basin'].isin(st.session_state.ui_basins)
    if skip_filter != 'Groups'      and st.session_state.ui_groups:
        v_cols = [g for g in st.session_state.ui_groups if g in df.columns]
        if v_cols:
            m &= df[v_cols].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1) > 0
    if skip_filter != 'Vars' and st.session_state.ui_vars and has_vars:
        m &= df['Observation_Variables'].apply(
            lambda x: any(
                v in [s.strip() for s in str(x).split(',')]
                for v in st.session_state.ui_vars
            )
        )
    if skip_filter != 'Intensity':
        m &= (
            (df['Intensity_ms'] >= st.session_state.ui_int[0] * mult) &
            (df['Intensity_ms'] <= st.session_state.ui_int[1] * mult)
        )
    if skip_filter != 'MSLP':
        m &= (
            (df['MSLP_hPa'] >= st.session_state.ui_slp[0]) &
            (df['MSLP_hPa'] <= st.session_state.ui_slp[1])
        )
    return m


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_explorer_controls(db_df, has_vars,
                              raw_min_i, raw_max_i,
                              raw_min_p, raw_max_p) -> ExplorerIntent:
    """
    Render all sidebar filter sections and return an ExplorerIntent.
    No filtering of db_df happens here — only widget state is managed.
    """
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

    if 'explorer_state' not in st.session_state:
        st.session_state.explorer_state = {}
    for k, v in default_state.items():
        if k not in st.session_state:
            st.session_state[k] = st.session_state.explorer_state.get(k, v)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def reset_all_filters():
        st.session_state.ui_years  = []
        st.session_state.ui_storms = []
        st.session_state.ui_cats   = []
        st.session_state.ui_basins = []
        st.session_state.ui_groups = []
        st.session_state.ui_vars   = []
        cur_mult = MS_TO_KTS if st.session_state.get('ui_unit') == "knots" else 1.0
        st.session_state.ui_int = (
            float(np.floor(raw_min_i * cur_mult)),
            float(np.ceil(raw_max_i * cur_mult)),
        )
        st.session_state.ui_slp  = (init_min_p, init_max_p)
        st.session_state.ui_sort_col   = 'Year'
        st.session_state.ui_sort_order = 'Ascending'

    def reset_table_sort():
        st.session_state.ui_sort_col   = 'Year'
        st.session_state.ui_sort_order = 'Ascending'

    # ------------------------------------------------------------------
    # Storm information filters
    # ------------------------------------------------------------------

    st.sidebar.markdown("### 🌍 Explorer Filters")
    with st.sidebar.container(border=True):
        st.markdown("#### Filter by Storm Information")

        filter_mappings = [
            ("Year",        "ui_years",  "Year",        "Year"),
            ("Name",        "ui_storms", "Storm",       "Storm"),
            ("Category",    "ui_cats",   "TC_Category", "TC_Category"),
            ("Storm Basin", "ui_basins", "Basin",       "Basin"),
        ]
        for label, key, col, skip_arg in filter_mappings:
            avail = sorted(
                db_df[get_dropdown_mask(db_df, skip_arg, has_vars)][col]
                .dropna().unique()
            )
            multiselect_with_controls(label, avail, key)
            section_divider()

        # Intensity slider with unit toggle
        col_label, col_radio = st.columns([0.6, 1])
        with col_label:
            sidebar_label('Intensity', size='label')
        with col_radio:
            unit = st.radio("Unit", ["m/s", "knots"], key="ui_unit",
                            label_visibility="collapsed", horizontal=True)

        mult             = MS_TO_KTS if unit == "knots" else 1.0
        g_min_i_unit     = float(np.floor(raw_min_i * mult))
        g_max_i_unit     = float(np.ceil(raw_max_i  * mult))

        # Rescale slider when unit changes
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

        # Clamp slider to the currently visible intensity range
        i_df     = db_df[get_dropdown_mask(db_df, 'Intensity', has_vars)]
        t_min_i  = float(np.floor(i_df['Intensity_ms'].min() * mult)) if not i_df.empty else g_min_i_unit
        t_max_i  = float(np.ceil( i_df['Intensity_ms'].max() * mult)) if not i_df.empty else g_max_i_unit
        st.session_state.ui_int = (
            max(t_min_i, min(st.session_state.ui_int[0], t_max_i)),
            max(t_min_i, min(st.session_state.ui_int[1], t_max_i)),
        )
        st.slider("Intensity", min_value=g_min_i_unit, max_value=g_max_i_unit,
                  step=5.0 if unit == "knots" else 1.0,
                  key="ui_int", label_visibility="collapsed")

        # MSLP slider
        sidebar_label('MSLP (hPa)', size='label')
        p_df    = db_df[get_dropdown_mask(db_df, 'MSLP', has_vars)]
        t_min_p = float(np.floor(p_df['MSLP_hPa'].min())) if not p_df.empty else init_min_p
        t_max_p = float(np.ceil( p_df['MSLP_hPa'].max())) if not p_df.empty else init_max_p
        st.session_state.ui_slp = (
            max(t_min_p, min(st.session_state.ui_slp[0], t_max_p)),
            max(t_min_p, min(st.session_state.ui_slp[1], t_max_p)),
        )
        st.slider("MSLP", min_value=init_min_p, max_value=init_max_p,
                  step=1.0, key="ui_slp", label_visibility="collapsed")

    # ------------------------------------------------------------------
    # Group filter
    # ------------------------------------------------------------------

    with st.sidebar.container(border=True):
        st.markdown("#### Filter Rows by Group")
        df_groups    = db_df[get_dropdown_mask(db_df, 'Groups', has_vars)]
        avail_groups = sorted([
            g for g in EXPECTED_GROUPS
            if g in df_groups.columns and
            pd.to_numeric(df_groups[g], errors='coerce').fillna(0).sum() > 0
        ])
        multiselect_with_controls('Contains group:', avail_groups, 'ui_groups')

    # ------------------------------------------------------------------
    # Variable filter
    # ------------------------------------------------------------------

    with st.sidebar.container(border=True):
        st.markdown("#### Filter Rows by Variable")
        df_vars    = db_df[get_dropdown_mask(db_df, 'Vars', has_vars)]
        avail_vars = (
            sorted(set(
                v.strip()
                for v_str in df_vars['Observation_Variables']
                if isinstance(v_str, str)
                for v in v_str.split(',')
                if v.strip() and v.strip().lower() != 'nan'
            ))
            if has_vars else []
        )
        multiselect_with_controls('Contains variable:', avail_vars, 'ui_vars')

    st.sidebar.button("🔄 Reset All Filters", type="secondary",
                      use_container_width=True, on_click=reset_all_filters)

    # ------------------------------------------------------------------
    # Persist state and return intent
    # ------------------------------------------------------------------

    for k in default_state.keys():
        if k in st.session_state:
            st.session_state.explorer_state[k] = st.session_state[k]

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
