# -*- coding: utf-8 -*-
"""
ui_explorer.py
--------------
Global Dataset Explorer tab entry point.

All sidebar filter controls live in ui_explorer_controls.py.
This module is responsible only for:
  1. Loading the inventory database
  2. Calling render_explorer_controls() to get an ExplorerIntent
  3. Detecting whether any filter is active
  4. Filtering the dataframe
  5. Rendering table controls (sort, download), summary table, and the results table
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime

from config import EXPECTED_GROUPS
from data_utils import load_inventory_db
from ui_explorer_controls import render_explorer_controls, get_dropdown_mask, MS_TO_KTS
from ui_components import spacer
from ui_explorer_table import display_explorer_table, display_summary_table
from ui_explorer_plots import render_explorer_summary_plots

def render_explorer_tab():

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

    # Render sidebar and collect intent
    intent = render_explorer_controls(
        db_df, has_vars,
        raw_min_i, raw_max_i,
        raw_min_p, raw_max_p,
    )

    # ------------------------------------------------------------------
    # Guard: show prompt when no filter is active
    # ------------------------------------------------------------------
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
    ])

    if not any_active:
        spacer('lg')
        spacer('lg')
        st.info("👈 **Ready to explore?**\nPlease make a selection from the filters to begin.")
        return

    # ------------------------------------------------------------------
    # Apply filters and validate result
    # ------------------------------------------------------------------
    final_df = db_df[get_dropdown_mask(db_df, None, has_vars)].copy()
    if final_df.empty:
        st.warning("No files match the current combination of filters.")
        return

    final_df['Lon'] = final_df['Lon'].abs()

    spacer('lg')

    # ------------------------------------------------------------------
    # 1. View Summary Table of Filtered Results
    # ------------------------------------------------------------------
    with st.expander("📋 View Summary Table of Filtered Results", expanded=False):
        display_summary_table(final_df, intent.unit)

    # ------------------------------------------------------------------
    # 2. View Summary Graphics of Filtered Results
    # ------------------------------------------------------------------
    render_explorer_summary_plots(final_df, intent.unit)

    # ------------------------------------------------------------------
    # 3. Results Count
    # ------------------------------------------------------------------
    spacer('md')
    st.markdown(f"#### 🔎 Found **{len(final_df)}** matching files")

    # ------------------------------------------------------------------
    # 4. Table Controls
    # ------------------------------------------------------------------
    def reset_table_sort():
        st.session_state.ui_sort_col   = 'Year'
        st.session_state.ui_sort_order = 'Ascending'

    with st.container(border=True):
        sort_options = {
            "Year": "Year", "Storm Name": "Storm", "Basin": "Basin",
            "Cycle (Time)": "Cycle_Raw", "Latitude": "Lat", "Longitude": "Lon",
            "Intensity": "Intensity_ms", "MSLP": "MSLP_hPa",
            "Category": "TC_Category",
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

        # Primary sort column + stable secondary tiebreakers
        sort_cols = [sort_col_internal]
        asc_list  = [is_asc]
        for tb in ['Year', 'Storm', 'Cycle_Raw']:
            if tb != sort_col_internal:
                sort_cols.append(tb)
                asc_list.append(True)

        final_df = final_df.sort_values(by=sort_cols, ascending=asc_list)
        csv_data = final_df.to_csv(index=False).encode('utf-8')

        with sc5:
            spacer('lg')
            st.download_button(
                label="⬇️ Download Results as CSV",
                data=csv_data,
                file_name=f"hrdobs_filtered_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime='text/csv', type="secondary", width="stretch",
            )

    # ------------------------------------------------------------------
    # 5. Full Styled Table
    # ------------------------------------------------------------------
    spacer('sm')
    display_explorer_table(final_df, intent.unit, sort_col_internal, is_asc)
