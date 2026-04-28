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
from ui_components import spacer, sidebar_label, multiselect_with_controls, section_divider, init_state, sync_namespace, safe_slider, dynamic_range_slider

# --- SHIPS Parameter Definitions ---
SHIPS_CONFIG = {
    'incv_kt':    {'label': '6-h Intensity Change (kt)',                             'step': 5.0},
    'dtl_km':     {'label': 'Distance to Land (km)',                                 'step': 5.0},
    'shrd_kt':    {'label': 'Shear Magnitude (kt)',                                  'step': 1.0},
    'shtd_deg':   {'label': 'Shear Direction (deg)',                                 'step': 10.0},
    'rhmd_pct':   {'label': 'Mid-Level Rel. Hum. (%)',                               'step': 1.0},
    'nsst_degc':  {'label': 'Analyzed SST from Navy NCODA (deg C)',                  'step': 0.25},
    'nohc_kjcm2': {'label': 'Analyzed Ocean Heat Content from Navy NCODA (kJ/cm^2)', 'step': 1.0},
    'vmpi_kt':    {'label': 'Max. Potential Intensity (kt)',                         'step': 1.0},
}

# --- Geographic Region Definitions ---
GEO_REGIONS = {
    "Global (All)": {'Basin': 'All', 'lat': None, 'lon': None},
    "Main Development Region (MDR)": {'Basin': 'North Atlantic', 'lat': (10.0, 20.0), 'lon': (-60.0, -20.0)},
    "Gulf of Mexico": {'Basin': 'North Atlantic', 'lat': (18.0, 30.0), 'lon': (-98.0, -81.0)},
    "Caribbean Sea": {'Basin': 'North Atlantic', 'lat': (9.0, 22.0), 'lon': (-89.0, -60.0)},
    "Western Atlantic": {'Basin': 'North Atlantic', 'lat': (20.0, 45.0), 'lon': (-80.0, -60.0)},
    "Eastern Pacific (EPAC)": {'Basin': 'Eastern Pacific', 'lat': (5.0, 30.0), 'lon': (-140.0, -80.0)},
    "Central Pacific (CPAC)": {'Basin': 'Central Pacific', 'lat': (5.0, 30.0), 'lon': (-180.0, -140.0)},
    "Custom": {'Basin': 'All', 'lat': None, 'lon': None}
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

    # --- Geographic Filtering (Cycle-Based) ---
    if 'Geography' not in skip_filters:
        lat_b = st.session_state.get('ui_lat')
        lon_b = st.session_state.get('ui_lon')

        if lat_b and lon_b:
            m &= ((df['Lat'] >= lat_b[0]) & (df['Lat'] <= lat_b[1]) & \
                  (df['Lon'] >= lon_b[0]) & (df['Lon'] <= lon_b[1]))
    
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

    # Calculate global DB bounds for Lat/Lon
    db_lat_min = float(np.floor(db_df['Lat'].min())) if not db_df['Lat'].isna().all() else -90.0
    db_lat_max = float(np.ceil(db_df['Lat'].max())) if not db_df['Lat'].isna().all() else 90.0
    db_lon_min = float(np.floor(db_df['Lon'].min())) if not db_df['Lon'].isna().all() else -180.0
    db_lon_max = float(np.ceil(db_df['Lon'].max())) if not db_df['Lon'].isna().all() else 180.0

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
        'ui_geo_mode': 'Passed Through',
        'ui_region': 'Global (All)',
        'ui_lat': (db_lat_min, db_lat_max),
        'ui_lon': (db_lon_min, db_lon_max),
        'ui_unit': "knots", 'prev_unit': "knots",
        'ui_int': (float(np.floor(raw_min_i * MS_TO_KTS)), float(np.ceil(raw_max_i * MS_TO_KTS))),
        'ui_slp': (init_min_p, init_max_p),
        'ui_ships_inc_nan': True,
        'ui_sort_col': 'Year', 'ui_sort_order': 'Ascending',
    }
    
    # Initialize state for SHIPS sliders
    for col, bounds in ships_global_bounds.items():
        default_state[f"ui_ships_{col}"] = bounds
        default_state[f"_last_t_min_ui_ships_{col}"] = bounds[0]
        default_state[f"_last_t_max_ui_ships_{col}"] = bounds[1]

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
        st.session_state.ui_geo_mode = 'Passed Through'
        st.session_state.ui_region = 'Global (All)'
        st.session_state.ui_lat    = (db_lat_min, db_lat_max)
        st.session_state.ui_lon    = (db_lon_min, db_lon_max)
        st.session_state.ui_sort_col   = 'Year'
        st.session_state.ui_sort_order = 'Ascending'
        
        # Reset internal tracker states for dynamic range wrappers
        st.session_state._last_t_min_ui_int = float(np.floor(raw_min_i * cur_mult))
        st.session_state._last_t_max_ui_int = float(np.ceil(raw_max_i * cur_mult))
        st.session_state._last_t_min_ui_slp = init_min_p
        st.session_state._last_t_max_ui_slp = init_max_p
        
        st.session_state.ui_ships_inc_nan = True
        for c, b in ships_global_bounds.items():
            st.session_state[f"ui_ships_{c}"] = b
            st.session_state[f"_last_t_min_ui_ships_{c}"] = b[0]
            st.session_state[f"_last_t_max_ui_ships_{c}"] = b[1]

    st.sidebar.markdown(f"### 🌍 Apply Filters Below to List Matching Files")
    
    with st.sidebar.container(border=True):
        st.markdown("#### Filter by Storm Information")

        # --- ANTI-RESET HELPER ---
        def get_safe_options(filtered_series, session_key):
            """Prevents Streamlit from secretly deleting selections when cross-filters narrow the options."""
            avail = list(filtered_series.dropna().unique())
            current_sel = st.session_state.get(session_key, [])
            for item in current_sel:
                if item not in avail:
                    avail.append(item)
            try:
                return sorted(avail)
            except TypeError:
                return avail # Fallback just in case of mixed data types

        filter_mappings = [
            ("Year",        "ui_years",  "Year",        "Year"),
            ("Name",        "ui_storms", "Storm",       "Storm"),
            ("Storm Basin", "ui_basins", "Basin",       "Basin"),
        ]
        
        for label, key, col, skip_arg in filter_mappings:
            filtered_series = db_df[get_dropdown_mask(db_df, skip_arg, has_vars)][col]
            avail = get_safe_options(filtered_series, key)
            multiselect_with_controls(label, avail, key)
            section_divider()

        # --- GEOGRAPHIC LOCATION SECTION ---
        st.markdown("#### Geographic Location")
        
        avail_basins_in_db = db_df['Basin'].dropna().unique()
        avail_regions = [r for r, conf in GEO_REGIONS.items() if conf['Basin'] == 'All' or conf['Basin'] in avail_basins_in_db]
        
        def clip_bounds(val_tuple, global_min, global_max):
            v_min = max(val_tuple[0], global_min)
            v_max = min(val_tuple[1], global_max)
            return (global_min, global_max) if v_min > v_max else (v_min, v_max)

        def on_region_change():
            reg = st.session_state.get("ui_region", "Global (All)")
            if reg in GEO_REGIONS and GEO_REGIONS[reg]['lat'] is not None:
                st.session_state.ui_lat = clip_bounds(GEO_REGIONS[reg]['lat'], db_lat_min, db_lat_max)
                st.session_state.ui_lon = clip_bounds(GEO_REGIONS[reg]['lon'], db_lon_min, db_lon_max)
            elif reg == "Global (All)":
                st.session_state.ui_lat = (db_lat_min, db_lat_max)
                st.session_state.ui_lon = (db_lon_min, db_lon_max)

        def on_geo_slider_change():
            st.session_state.ui_region = "Custom"
            
        st.selectbox("Filter Region ('Custom' Unfreezes Lat/Lon Sliders):", avail_regions, key="ui_region", on_change=on_region_change)
        spacer('sm')
        disable_sliders = st.session_state.get("ui_region", "Global (All)") != "Custom"
        
        sidebar_label("Longitude (deg)", size="label")
        safe_slider("Longitude", min_value=db_lon_min, max_value=db_lon_max, step=1.0, key="ui_lon", 
                    label_visibility="collapsed", on_change=on_geo_slider_change, disabled=disable_sliders)
        
        sidebar_label("Latitude (deg)", size="label")
        safe_slider("Latitude", min_value=db_lat_min, max_value=db_lat_max, step=1.0, key="ui_lat", 
                    label_visibility="collapsed", on_change=on_geo_slider_change, disabled=disable_sliders)
        
        section_divider()

        # --- INTENSITY & MSLP GROUPING ---
        filtered_cats = db_df[get_dropdown_mask(db_df, "TC_Category", has_vars)]["TC_Category"]
        avail_cats = get_safe_options(filtered_cats, "ui_cats")
        multiselect_with_controls("Filter by Category", avail_cats, "ui_cats")
        
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
            
            # Align internal tracking keys for the wrapper conversion
            last_min_old = st.session_state.get('_last_t_min_ui_int', old_g_min)
            last_max_old = st.session_state.get('_last_t_max_ui_int', old_g_max)
            st.session_state._last_t_min_ui_int = last_min_old * MS_TO_KTS if unit == "knots" else last_min_old / MS_TO_KTS
            st.session_state._last_t_max_ui_int = last_max_old * MS_TO_KTS if unit == "knots" else last_max_old / MS_TO_KTS

        slider_mask = get_dropdown_mask(db_df, ['Intensity', 'MSLP'], has_vars)
        slider_df   = db_df[slider_mask]

        t_min_i  = float(np.floor(slider_df['Intensity_ms'].min() * mult)) if not slider_df.empty else g_min_i_unit
        t_max_i  = float(np.ceil( slider_df['Intensity_ms'].max() * mult)) if not slider_df.empty else g_max_i_unit
        
        dynamic_range_slider("Intensity", global_min=g_min_i_unit, global_max=g_max_i_unit, 
                             data_min=t_min_i, data_max=t_max_i, 
                             step=5.0 if unit == "knots" else 1.0, 
                             key="ui_int", label_visibility="collapsed")

        sidebar_label('MSLP (hPa)', size='label')
        t_min_p = float(np.floor(slider_df['MSLP_hPa'].min())) if not slider_df.empty else init_min_p
        t_max_p = float(np.ceil( slider_df['MSLP_hPa'].max())) if not slider_df.empty else init_max_p
        
        dynamic_range_slider("MSLP", global_min=init_min_p, global_max=init_max_p, 
                             data_min=t_min_p, data_max=t_max_p, 
                             step=1.0, key="ui_slp", label_visibility="collapsed")

    with st.sidebar.container(border=True):
        st.markdown("#### Filter by Available Data")
        
        df_groups    = db_df[get_dropdown_mask(db_df, 'Groups', has_vars)]
        avail_groups = [g for g in EXPECTED_GROUPS if g in df_groups.columns and pd.to_numeric(df_groups[g], errors='coerce').fillna(0).sum() > 0]
        
        for sel_g in st.session_state.get('ui_groups', []):
            if sel_g not in avail_groups:
                avail_groups.append(sel_g)
        avail_groups = [g for g in EXPECTED_GROUPS if g in avail_groups] + [g for g in avail_groups if g not in EXPECTED_GROUPS]

        multiselect_with_controls('Contains Aircraft/Platform/Track Group:', avail_groups, 'ui_groups')

        section_divider()

        df_vars    = db_df[get_dropdown_mask(db_df, 'Vars', has_vars)]
        avail_vars = (sorted(set(v.strip() for v_str in df_vars['Observation_Variables'] if isinstance(v_str, str) for v in v_str.split(',') if v.strip() and v.strip().lower() != 'nan')) if has_vars else [])

        # --- RESTRICT TO OBSERVED VARIABLES ONLY ---
        excluded_vars = set([k.lower() for k, v in GLOBAL_VAR_CONFIG.items() if v.get('is_coord', False)])
        excluded_vars.update([k.lower() for k in SHIPS_PREDICTOR_META.keys()])
        excluded_vars.update(['lat', 'latitude', 'clat', 'lon', 'longitude', 'clon', 'time', 'rmw', 'vmax', 'pmin'])

        avail_vars = [
            v for v in avail_vars 
            if v.lower() not in excluded_vars 
            and not v.lower().endswith('err') 
            and not v.lower().endswith('_err') 
            and not v.lower().endswith('error')
        ]

        active_groups = st.session_state.get('ui_groups', [])
        if active_groups:
            allowed_vars = set()
            instrument_mappings = {
                'sfmr': ['SFC_WSPD', 'RAIN_RATE'],
                'tdr': ['DBZ', 'VR', 'w', 'u', 'v', 'dz', 'vt'],
                'flight_level': ['T', 'Td', 'wspd', 'wdir', 'u', 'v', 'w', 'hwspd', 'theta', 'theta_e'],
                'dropsonde': ['T', 'RH', 'wspd', 'wdir', 'u', 'v', 'vt', 'mr', 'theta', 'theta_e'],
                'axbt': ['SST', 'T', 'depth']
            }
            
            for g in active_groups:
                g_lower = g.lower()
                matched = False
                for inst, ivars in instrument_mappings.items():
                    if inst in g_lower:
                        allowed_vars.update(ivars)
                        allowed_vars.update([iv.lower() for iv in ivars])
                        matched = True
                
                if not matched:
                    obs_vars = [k for k, v in GLOBAL_VAR_CONFIG.items() if not v.get('is_derived', False) and not v.get('is_coord', False)]
                    allowed_vars.update(obs_vars)

            avail_vars = [v for v in avail_vars if v in allowed_vars or v.lower() in allowed_vars or v.upper() in allowed_vars]

        var_display_map = {}
        for k, v in GLOBAL_VAR_CONFIG.items():
            var_display_map[k] = v.get('display_name', k)
        for k, (ships_unit, desc) in SHIPS_PREDICTOR_META.items():
            var_display_map[k] = f"{desc} ({ships_unit})"
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
            long_name = var_display_map.get(
                short_name, var_display_map.get(short_name.upper(), var_display_map.get(short_name.lower(), short_name))
            )
            return f"{long_name} ({short_name})" if long_name != short_name else short_name

        for sel_v in st.session_state.get('ui_vars', []):
            if sel_v not in avail_vars:
                avail_vars.append(sel_v)
        avail_vars = sorted(avail_vars)

        multiselect_with_controls('Contains Observed Variable:', avail_vars, 'ui_vars', format_func=format_var_name)

    # --- SHIPS Environment Filters ---
    with st.sidebar.container(border=True):
        st.markdown("#### Filter by SHIPS Parameter")
        st.checkbox("Show all files regardless of whether they contain SHIPS data", key="ui_ships_inc_nan")
        
        slider_mask_ships = get_dropdown_mask(db_df, ['SHIPS'], has_vars)
        slider_df_ships = db_df[slider_mask_ships]
        
        for col, config in SHIPS_CONFIG.items():
            if col not in db_df.columns: continue
                
            g_min, g_max = ships_global_bounds[col]
            
            t_min = float(np.floor(slider_df_ships[col].min())) if not slider_df_ships[col].isna().all() else g_min
            t_max = float(np.ceil(slider_df_ships[col].max())) if not slider_df_ships[col].isna().all() else g_max
            if pd.isna(t_min): t_min = g_min
            if pd.isna(t_max): t_max = g_max
            
            state_key = f"ui_ships_{col}"
            sidebar_label(config['label'], size='label')
            dynamic_range_slider(config['label'], global_min=g_min, global_max=g_max, 
                                 data_min=t_min, data_max=t_max, 
                                 step=config['step'], key=state_key, label_visibility="collapsed")

    st.sidebar.button("🔄 Reset All Filters", type="secondary", width="stretch", on_click=reset_all_filters)

    sync_namespace('ui_', 'explorer_state')

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
