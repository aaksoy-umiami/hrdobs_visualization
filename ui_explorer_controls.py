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
    DEFAULT_MSLP_MIN, DEFAULT_MSLP_MAX,
    GLOBAL_VAR_CONFIG, SHIPS_PREDICTOR_META
)
from ui_layout import CLR_MUTED, FS_BODY
from ui_components import spacer, sidebar_label, multiselect_with_controls, section_divider, init_state, sync_namespace

# --- SHIPS Parameter Definitions ---
SHIPS_CONFIG = {
    'incv_kt':  {'label': 'Intensity Change (kt)', 'step': 1.0},
    'dtl_km':   {'label': 'Distance to Land (km)', 'step': 10.0},
    'shrd_kt':  {'label': 'Shear Magnitude (kt)',  'step': 1.0},
    'shtd_deg': {'label': 'Shear Direction (deg)', 'step': 10.0},
    'rhmd_pct': {'label': 'Mid RH (%)',            'step': 1.0},
    'vmpi_kt':  {'label': 'MPI (kt)',              'step': 1.0},
}

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
    is_ships_active: bool       = False

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
    
    # Apply SHIPS filters
    if 'SHIPS' not in skip_filters:
        inc_nan = st.session_state.get('ui_ships_inc_nan', True)
        for col in SHIPS_CONFIG.keys():
            state_key = f"ui_ships_{col}"
            if state_key in st.session_state and col in df.columns:
                vmin, vmax = st.session_state[state_key]
                cond = (df[col] >= vmin) & (df[col] <= vmax)
                if inc_nan:
                    cond = cond | df[col].isna()
                m &= cond
                
    return m

def render_explorer_controls(db_df, has_vars, raw_min_i, raw_max_i, raw_min_p, raw_max_p) -> ExplorerIntent:
    init_min_i = float(np.floor(raw_min_i))
    init_max_i = float(np.ceil(raw_max_i))
    init_min_p = float(np.floor(raw_min_p))
    init_max_p = float(np.ceil(raw_max_p))

    # Calculate global bounds for SHIPS variables
    ships_global_bounds = {}
    for col, config in SHIPS_CONFIG.items():
        if col in db_df.columns:
            cmin = float(np.floor(db_df[col].min())) if not db_df[col].isna().all() else 0.0
            cmax = float(np.ceil(db_df[col].max())) if not db_df[col].isna().all() else 100.0
            if cmin >= cmax: cmax = cmin + config['step']
            ships_global_bounds[col] = (cmin, cmax)

    default_state = {
        'ui_years': [], 'ui_storms': [], 'ui_cats': [], 'ui_basins': [],
        'ui_groups': [], 'ui_vars': [],
        'ui_unit': "knots", 'prev_unit': "knots",
        'ui_int': (float(np.floor(raw_min_i * MS_TO_KTS)), float(np.ceil(raw_max_i * MS_TO_KTS))), # <-- Apply knot conversion
        'ui_slp': (init_min_p, init_max_p),
        'ui_ships_inc_nan': True,
        'ui_sort_col': 'Year', 'ui_sort_order': 'Ascending',
    }
    
    # Initialize state for SHIPS sliders
    for col, bounds in ships_global_bounds.items():
        default_state[f"ui_ships_{col}"] = bounds
        default_state[f"_last_t_min_ships_{col}"] = bounds[0]
        default_state[f"_last_t_max_ships_{col}"] = bounds[1]

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
        
        st.session_state.ui_ships_inc_nan = True
        for c, b in ships_global_bounds.items():
            st.session_state[f"ui_ships_{c}"] = b
            st.session_state[f"_last_t_min_ships_{c}"] = b[0]
            st.session_state[f"_last_t_max_ships_{c}"] = b[1]

    st.sidebar.markdown(f"### 🌍 Apply Filters Below to List Matching Files")
    
    with st.sidebar.container(border=True):
        st.markdown("#### Filter by Storm Information")

        filter_mappings = [
            ("Year",        "ui_years",  "Year",        "Year"),
            ("Name",        "ui_storms", "Storm",       "Storm"),
            ("Storm Basin", "ui_basins", "Basin",       "Basin"),
        ]
        
        for label, key, col, skip_arg in filter_mappings:
            avail = sorted(db_df[get_dropdown_mask(db_df, skip_arg, has_vars)][col].dropna().unique())
            multiselect_with_controls(label, avail, key)
            section_divider()

        # --- INTENSITY & MSLP GROUPING (No separators) ---
        avail_cats = sorted(db_df[get_dropdown_mask(db_df, "TC_Category", has_vars)]["TC_Category"].dropna().unique())
        multiselect_with_controls("Intensity Category", avail_cats, "ui_cats")
        
        spacer('sm')

        col_label, col_radio = st.columns([0.35, 1.25])
        with col_label: sidebar_label('Intensity', size='label')
        with col_radio: unit = st.radio("Unit", ["knots", "m/s"], key="ui_unit", label_visibility="collapsed", horizontal=True)

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
        st.markdown("#### Filter Rows by Aircraft/Platform/Track/Variable")
        
        df_groups    = db_df[get_dropdown_mask(db_df, 'Groups', has_vars)]
        # Removed sorted() to preserve the exact order defined in config.py's EXPECTED_GROUPS
        avail_groups = [g for g in EXPECTED_GROUPS if g in df_groups.columns and pd.to_numeric(df_groups[g], errors='coerce').fillna(0).sum() > 0]
        multiselect_with_controls('Contains aircraft/platform/track group:', avail_groups, 'ui_groups')

        section_divider()

        df_vars    = db_df[get_dropdown_mask(db_df, 'Vars', has_vars)]
        avail_vars = (sorted(set(v.strip() for v_str in df_vars['Observation_Variables'] if isinstance(v_str, str) for v in v_str.split(',') if v.strip() and v.strip().lower() != 'nan')) if has_vars else [])

        # --- SMART VARIABLE FILTERING (Cumulative Mask) ---
        active_groups = st.session_state.get('ui_groups', [])
        if active_groups:
            allowed_vars = set()
            ships_vars = list(SHIPS_CONFIG.keys()) # <-- Now uses your existing global import!
            track_vars = ['lat', 'latitude', 'clat', 'lon', 'longitude', 'clon', 'time', 'vmax', 'pmin', 'rmw']
            
            # Map specific keywords in your group names to their respective variables
            instrument_mappings = {
                'sfmr': ['SFC_WSPD', 'RAIN_RATE', 'lat', 'lon', 'time'],
                'tdr': ['DBZ', 'VR', 'w', 'u', 'v', 'lat', 'lon', 'time', 'altitude', 'height', 'dz', 'vt'],
                'flight_level': ['T', 'Td', 'wspd', 'wdir', 'u', 'v', 'p', 'height', 'lat', 'lon', 'time', 'w', 'hwspd', 'theta', 'theta_e'],
                'dropsonde': ['T', 'RH', 'wspd', 'wdir', 'u', 'v', 'p', 'height', 'altitude', 'ght', 'lat', 'lon', 'time', 'vt', 'mr', 'theta', 'theta_e', 'sfcp', 'elev'],
                'axbt': ['SST', 'T', 'depth', 'lat', 'lon', 'time']
            }
            
            for g in active_groups:
                g_lower = g.lower()
                if g_lower == 'ships_params':
                    allowed_vars.update(ships_vars)
                elif g_lower.startswith('track_'):
                    allowed_vars.update(track_vars)
                else:
                    # Check if the group name contains an instrument keyword (e.g., 'dropsonde_ghawk' contains 'dropsonde')
                    matched = False
                    for inst, ivars in instrument_mappings.items():
                        if inst in g_lower:
                            # Add both the exact cases and lowercase versions to be safe
                            allowed_vars.update(ivars)
                            allowed_vars.update([iv.lower() for iv in ivars])
                            matched = True
                    
                    # Fallback: if we have an unmapped group, add all remaining non-derived vars just in case
                    if not matched:
                        obs_vars = [k for k, v in GLOBAL_VAR_CONFIG.items() if not v.get('is_derived', False) and k not in track_vars]
                        allowed_vars.update(obs_vars)
                        allowed_vars.update(['lat', 'latitude', 'lon', 'longitude', 'time', 'p', 'height', 'altitude'])

            # Intersect available variables with the cumulative allowed list (case-insensitive check)
            avail_vars = [v for v in avail_vars if v in allowed_vars or v.lower() in allowed_vars or v.upper() in allowed_vars]
        # --------------------------------------------------

        # --- VARIABLE DISPLAY FORMATTER ---
        # 1. Start with an empty map
        var_display_map = {}

        # 2. Add standard variables from config.py
        for k, v in GLOBAL_VAR_CONFIG.items():
            var_display_map[k] = v.get('display_name', k)

        # 3. Add SHIPS parameters from SHIPS_PREDICTOR_META
        # This unpacks the (unit, description) tuple automatically
        for k, (unit, desc) in SHIPS_PREDICTOR_META.items():
            var_display_map[k] = f"{desc} ({unit})"

        # 4. Update with track/coordinate variables
        var_display_map.update({
            'lat': 'Latitude (deg)', 'latitude': 'Latitude (deg)', 
            'clat': 'Center Latitude (deg)', 'lon': 'Longitude (deg)', 
            'longitude': 'Longitude (deg)', 'clon': 'Center Longitude (deg)',
            'time': 'Time (UTC)', 'altitude': 'Altitude (m)', 
            'height': 'Height (m)', 'p': 'Pressure (hPa)',
            'pmin': 'Minimum Pressure (hPa)', 
            'vmax': 'Maximum Wind Speed (m/s)', 
            'rmw': 'Radius of Max Winds (km)'
        })

        def format_var_name(short_name):
            # Check for exact case, then upper/lower case fallbacks
            long_name = var_display_map.get(
                short_name, 
                var_display_map.get(short_name.upper(), 
                                   var_display_map.get(short_name.lower(), short_name))
            )
            # Display format: "Description (Unit) (short_name)"
            if long_name != short_name:
                return f"{long_name} ({short_name})"
            return short_name
        # ----------------------------------

        # Pass the format_func into the updated wrapper!
        multiselect_with_controls('Contains variable:', avail_vars, 'ui_vars', format_func=format_var_name)

    # --- New SHIPS Environment Filters ---
    with st.sidebar.container(border=True):
        st.markdown("#### Filter Rows by SHIPS Parameter")
        st.checkbox("Include files missing SHIPS data", key="ui_ships_inc_nan")
        
        slider_mask_ships = get_dropdown_mask(db_df, ['SHIPS'], has_vars)
        slider_df_ships = db_df[slider_mask_ships]
        
        for col, config in SHIPS_CONFIG.items():
            if col not in db_df.columns:
                continue
                
            g_min, g_max = ships_global_bounds[col]
            
            t_min = float(np.floor(slider_df_ships[col].min())) if not slider_df_ships[col].isna().all() else g_min
            t_max = float(np.ceil(slider_df_ships[col].max())) if not slider_df_ships[col].isna().all() else g_max
            if pd.isna(t_min): t_min = g_min
            if pd.isna(t_max): t_max = g_max
            if t_min >= t_max: t_max = t_min + config['step']
            
            state_key = f"ui_ships_{col}"
            last_t_min_key = f"_last_t_min_ships_{col}"
            last_t_max_key = f"_last_t_max_ships_{col}"
            
            last_t_min = st.session_state.get(last_t_min_key, g_min)
            last_t_max = st.session_state.get(last_t_max_key, g_max)
            curr_val = st.session_state.get(state_key, (g_min, g_max))
            
            if curr_val[0] <= last_t_min + 0.1 and curr_val[1] >= last_t_max - 0.1:
                new_val = (t_min, t_max)
            else:
                new_val = (max(t_min, min(curr_val[0], t_max)), max(t_min, min(curr_val[1], t_max)))
                if new_val[0] > new_val[1]: new_val = (t_min, t_max)
                
            st.session_state[state_key] = new_val
            st.session_state[last_t_min_key] = t_min
            st.session_state[last_t_max_key] = t_max
            
            sidebar_label(config['label'], size='label')
            st.slider(config['label'], min_value=g_min, max_value=g_max, step=config['step'], key=state_key, label_visibility="collapsed")

    st.sidebar.button("🔄 Reset All Filters", type="secondary", width="stretch", on_click=reset_all_filters)

    sync_namespace('ui_', 'explorer_state')

    # Detect if any SHIPS filter has been intentionally altered by the user
    is_ships_active = False
    if not st.session_state.ui_ships_inc_nan:
        is_ships_active = True
    for col, g_bounds in ships_global_bounds.items():
        curr = st.session_state.get(f"ui_ships_{col}", g_bounds)
        if abs(curr[0] - g_bounds[0]) > 0.1 or abs(curr[1] - g_bounds[1]) > 0.1:
            is_ships_active = True
            break

    return ExplorerIntent(
        unit            = unit,
        years           = list(st.session_state.ui_years),
        storms          = list(st.session_state.ui_storms),
        cats            = list(st.session_state.ui_cats),
        basins          = list(st.session_state.ui_basins),
        groups          = list(st.session_state.ui_groups),
        vars_           = list(st.session_state.ui_vars),
        int_range       = tuple(st.session_state.ui_int),
        slp_range       = tuple(st.session_state.ui_slp),
        sort_col        = st.session_state.get('ui_sort_col',   'Year'),
        sort_order      = st.session_state.get('ui_sort_order', 'Ascending'),
        g_min_i_unit    = g_min_i_unit,
        g_max_i_unit    = g_max_i_unit,
        init_min_p      = init_min_p,
        init_max_p      = init_max_p,
        is_ships_active = is_ships_active
    )
