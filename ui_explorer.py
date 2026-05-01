# -*- coding: utf-8 -*-
"""
Purpose:
    Serves as the entry point for the Global Dataset Explorer tab, coordinating filter inputs, summary plots, and table rendering.

Functions/Classes:
    - render_explorer_tab: Retrieves data, applies user constraints, and generates the filtered summary plots and data tables.
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

from config import EXPECTED_GROUPS
from data_utils import load_inventory_db

from ui_explorer_controls import render_explorer_controls, get_dropdown_mask, MS_TO_KTS, SHIPS_CONFIG
from ui_components import spacer
from ui_explorer_table import display_explorer_table, display_summary_table
from ui_explorer_plots import render_explorer_summary_plots

def render_explorer_tab():
    """
    Retrieves data, applies user constraints, and generates the filtered summary plots and data tables.
    """

    DB_PATH = "hrdobs_inventory_db.csv"
    if not os.path.exists(DB_PATH):
        st.warning(f"Database file `{DB_PATH}` not found. Please run your batch script to generate it!")
        return

    db_df    = load_inventory_db(DB_PATH)
    has_vars = 'Observation_Variables' in db_df.columns

    raw_min_i = float(db_df['Intensity_ms'].min(skipna=True))
    raw_max_i = float(db_df['Intensity_ms'].max(skipna=True))
    raw_min_p = float(db_df['MSLP_hPa'].min(skipna=True))
    raw_max_p = float(db_df['MSLP_hPa'].max(skipna=True))

    intent = render_explorer_controls(
        db_df, has_vars,
        raw_min_i, raw_max_i,
        raw_min_p, raw_max_p,
    )

    int_changed = (
        abs(intent.int_range[0] - intent.g_min_i_unit) > 0.1 or
        abs(intent.int_range[1] - intent.g_max_i_unit) > 0.1
    )
    slp_changed = (
        abs(intent.slp_range[0] - intent.init_min_p) > 0.1 or
        abs(intent.slp_range[1] - intent.init_max_p) > 0.1
    )
    any_active = any([
        intent.years, intent.storms, intent.cats, intent.basins,
        intent.groups, intent.vars_,
        int_changed, slp_changed,
        getattr(intent, 'is_ships_active', False) 
    ])

    if not any_active:
        spacer('lg')
        spacer('lg')
        st.info("👈 **Ready to explore?**\nPlease make a selection from the filters to begin.")
        return

    with st.spinner("Filtering database and generating tables..."):

        final_df = db_df[get_dropdown_mask(db_df, None, has_vars)].copy()
        if final_df.empty:
            st.warning("No files match the current combination of filters.")
            return

        final_df['Lon'] = final_df['Lon'].abs()

        df_no_geo_mask = get_dropdown_mask(db_df, ['Geography'], has_vars)
        df_no_geo_base = db_df[df_no_geo_mask]
        
        if not df_no_geo_base.empty:
            storm_keys = df_no_geo_base[['Storm', 'Year']].drop_duplicates()
            df_no_geo = db_df.merge(storm_keys, on=['Storm', 'Year'], how='inner').copy()
            df_no_geo['Lon'] = df_no_geo['Lon'].abs()
        else:
            df_no_geo = pd.DataFrame()

        spacer('lg')

        with st.expander("🗂️ View Summary Table of Filtered Results", expanded=False):
            display_summary_table(final_df, intent.unit)

        render_explorer_summary_plots(final_df, intent.unit, df_no_geo)

        spacer('md')
        st.markdown(f"#### 🔎 Found **{len(final_df)}/{len(db_df)}** matching files")

        def reset_table_sort():
            st.session_state.ui_sort_col   = 'Year'
            st.session_state.ui_sort_order = 'Ascending'

        with st.container(border=True):
            sort_options = {
                "Year": "Year", "Storm Name": "Storm", "Basin": "Basin",
                "Cycle (Time)": "Cycle_Raw", "Latitude": "Lat", "Longitude": "Lon",
                "Intensity": "Intensity_ms", "MSLP": "MSLP_hPa",
                "Intensity Category": "TC_Category",
            }
            for g in EXPECTED_GROUPS:
                if g in final_df.columns:
                    sort_options[g.replace('_', ' ').title()] = g

            sc1, sc2, sc3, sc4, sc5 = st.columns([1.6, 1.5, 1.1, 0.5, 1.5])
            with sc1:
                st.selectbox("Sort Table By Column:", list(sort_options.keys()),
                            key="ui_sort_col")
            with sc2:
                st.radio("Sort Direction:", ["Ascending", "Descending"],
                        key="ui_sort_order", horizontal=True)
            with sc3:
                spacer('lg')
                st.button("🔄 Reset Sort", key="btn_reset_sort", type="secondary",
                        width="stretch", on_click=reset_table_sort)

            sort_col_internal = sort_options.get(
                st.session_state.get('ui_sort_col', 'Year'), 'Year'
            )
            is_asc = st.session_state.get('ui_sort_order', 'Ascending') == "Ascending"

            sort_cols = [sort_col_internal]
            asc_list  = [is_asc]
            for tb in ['Year', 'Storm', 'Cycle_Raw']:
                if tb != sort_col_internal:
                    sort_cols.append(tb)
                    asc_list.append(True)

            final_df = final_df.sort_values(by=sort_cols, ascending=asc_list)
            
            header_lines = [
                f"# HRDOBS Dataset Explorer Export",
                f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"# Total Filtered Cycles: {len(final_df)} (out of {len(db_df)} total)",
                f"#",
                f"# --- ACTIVE FILTERS ---"
            ]
            
            has_filters = False
            if intent.years: 
                header_lines.append(f"# Years: {', '.join(map(str, intent.years))}"); has_filters = True
            if intent.storms: 
                header_lines.append(f"# Storms: {', '.join(intent.storms)}"); has_filters = True
            if intent.cats: 
                header_lines.append(f"# Intensity Categories: {', '.join(intent.cats)}"); has_filters = True
            if intent.basins: 
                header_lines.append(f"# Basins: {', '.join(intent.basins)}"); has_filters = True
            if intent.groups: 
                header_lines.append(f"# Required Groups: {', '.join(intent.groups)}"); has_filters = True
            if intent.vars_: 
                header_lines.append(f"# Required Variables: {', '.join(intent.vars_)}"); has_filters = True
                
            if abs(intent.int_range[0] - intent.g_min_i_unit) > 0.1 or abs(intent.int_range[1] - intent.g_max_i_unit) > 0.1:
                header_lines.append(f"# Intensity Range: {intent.int_range[0]:.1f} - {intent.int_range[1]:.1f} {intent.unit}")
                has_filters = True
                
            if abs(intent.slp_range[0] - intent.init_min_p) > 0.1 or abs(intent.slp_range[1] - intent.init_max_p) > 0.1:
                header_lines.append(f"# MSLP Range: {intent.slp_range[0]:.1f} - {intent.slp_range[1]:.1f} hPa")
                has_filters = True

            if getattr(intent, 'is_ships_active', False):
                inc_nan = st.session_state.get('ui_ships_inc_nan', True)
                header_lines.append(f"# Include missing SHIPS data: {inc_nan}")
                
                for col, config in SHIPS_CONFIG.items():
                    state_key = f"ui_ships_{col}"
                    last_min_key = f"_last_t_min_ships_{col}"
                    last_max_key = f"_last_t_max_ships_{col}"
                    
                    if state_key in st.session_state and last_min_key in st.session_state:
                        curr_min, curr_max = st.session_state[state_key]
                        default_min = st.session_state[last_min_key]
                        default_max = st.session_state[last_max_key]
                        
                        if abs(curr_min - default_min) > 0.1 or abs(curr_max - default_max) > 0.1:
                            header_lines.append(f"# {config['label']}: {curr_min:.1f} - {curr_max:.1f}")
                            
                has_filters = True

            if not has_filters:
                header_lines.append("# None")

            header_lines.append("#" + "-"*50)
            
            header_str = "\n".join(header_lines) + "\n"
            csv_data = header_str.encode('utf-8') + final_df.to_csv(index=False).encode('utf-8')

            with sc5:
                spacer('lg')
                st.download_button(
                    label="⬇️ Download Results as CSV",
                    data=csv_data,
                    file_name=f"hrdobs_filtered_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime='text/csv', type="secondary", width="stretch",
                )

        spacer('sm')
        display_explorer_table(final_df, intent.unit, sort_col_internal, is_asc)