# -*- coding: utf-8 -*-

"""
ui_explorer_table.py
----------
Formats and renders the filtered inventory results as a styled HTML multi-index table with group-separated columns and hover tooltips on storm names.

"""

import pandas as pd
import streamlit as st
from config import EXPECTED_GROUPS

def display_explorer_table(final_df, unit, sort_col_internal, is_asc):
    """Formats and renders the Pandas dataframe as a custom HTML block."""
    MS_TO_KTS = 1.94384
    
    final_df['Storm_Display'] = final_df.apply(lambda x: f"{x['Storm']}|||{x['Constructed_File_Name']}", axis=1)

    base_cols = ['Year', 'Storm_Display', 'Basin', 'Cycle_Display', 'Lat', 'Lon', 'Intensity_ms', 'MSLP_hPa', 'TC_Category']
    display_df = final_df[base_cols + EXPECTED_GROUPS].copy()
    display_df['Intensity_ms'] *= (MS_TO_KTS if unit == "knots" else 1.0)
    
    multi_cols = []
    fmt_map = {}
    numeric_cols = []
    group_starts = []
    current_top = None

    target_raw_col = {"Storm": "Storm_Display", "Cycle_Raw": "Cycle_Display"}.get(sort_col_internal, sort_col_internal)
    sort_tup_old = None

    for i, raw_col in enumerate(display_df.columns):
        if raw_col == 'Year': tup = ('Basic Data', 'Year')
        elif raw_col == 'Storm_Display': tup = ('Basic Data', 'Storm')
        elif raw_col == 'Basin': tup = ('Basic Data', 'Basin')
        elif raw_col == 'Cycle_Display': tup = ('Basic Data', 'Cycle')
        elif raw_col == 'Lat': tup = ('Basic Data', 'Lat<br>°N'); fmt_map[tup] = '{:,.1f}'; numeric_cols.append(tup)
        elif raw_col == 'Lon': tup = ('Basic Data', 'Lon<br>°W'); fmt_map[tup] = '{:,.1f}'; numeric_cols.append(tup)
        elif raw_col == 'Intensity_ms': tup = ('Basic Data', f'Intensity<br>({unit})'); fmt_map[tup] = '{:,.2f}'; numeric_cols.append(tup)
        elif raw_col == 'MSLP_hPa': tup = ('Basic Data', 'MSLP<br>(hPa)'); fmt_map[tup] = '{:,.1f}'; numeric_cols.append(tup)
        elif raw_col == 'TC_Category': tup = ('Basic Data', 'Category')
        else:
            top = 'Basic Data'
            if raw_col.startswith('dropsonde_'): top = 'Dropsondes'; bottom = raw_col.replace('dropsonde_', '').upper()
            elif raw_col.startswith('flight_level_hdobs_'): top = 'Flight Level'; bottom = raw_col.replace('flight_level_hdobs_', '').upper()
            elif raw_col.startswith('sfmr_'): top = 'SFMR'; bottom = raw_col.replace('sfmr_', '').upper()
            elif raw_col.startswith('tdr_'): top = 'Tail Doppler Radar (TDR)'; bottom = raw_col.replace('tdr_', '').upper()
            elif raw_col.startswith('track_'):
                top = 'Track Data'
                bottom = 'Best Track' if 'best' in raw_col.lower() else 'Spline' if 'spline' in raw_col.lower() else 'Vortex' if 'vortex' in raw_col.lower() else raw_col
            tup = (top, bottom); fmt_map[tup] = '{:,.0f}'; numeric_cols.append(tup)
        
        if tup[0] != current_top:
            group_starts.append(i + 1)
            current_top = tup[0]
        multi_cols.append(tup)
        
        if raw_col == target_raw_col:
            sort_tup_old = tup
            
    is_default_sort = (sort_col_internal == "Year" and is_asc)
    
    if sort_tup_old and not is_default_sort:
        arrow = "\xa0▲" if is_asc else "\xa0▼"
        sort_tup_new = (sort_tup_old[0], f"{sort_tup_old[1]}{arrow}")
        
        multi_cols = [sort_tup_new if c == sort_tup_old else c for c in multi_cols]
        if sort_tup_old in fmt_map: fmt_map[sort_tup_new] = fmt_map.pop(sort_tup_old)
        if sort_tup_old in numeric_cols: numeric_cols = [sort_tup_new if c == sort_tup_old else c for c in numeric_cols]
            
    display_df.columns = pd.MultiIndex.from_tuples(multi_cols)
    for c in numeric_cols: display_df[c] = pd.to_numeric(display_df[c], errors='coerce')

    def make_storm_hover(val):
        if '|||' in str(val):
            name, filename = str(val).split('|||')
            return f'<span title="{filename}" style="cursor:help; border-bottom: 1px dotted #ccc;">{name}</span>'
        return val

    fmt_map[('Basic Data', 'Storm')] = make_storm_hover

    thick_sel = ", ".join([f"th:nth-child({idx}), td:nth-child({idx})" for idx in group_starts])
    
    styled_html = (
        display_df.style
        .format(fmt_map, na_rep='')
        .set_properties(**{'text-align': 'center', 'padding': '4px', 'font-size': '13px'})
        .set_table_styles([
            {'selector': 'table', 'props': [('width', '100%'), ('border-collapse', 'collapse'), ('border', '2px solid black')]},
            {'selector': 'th', 'props': [('background-color', '#f0f2f6'), ('padding', '6px'), ('border', '1px solid #ddd'), ('text-align', 'center')]},
            {'selector': thick_sel, 'props': [('border-left', '2px solid black')]},
            {'selector': 'th.col_heading.level0', 'props': [('border-top', '2px solid black'), ('border-bottom', '2px solid black'), ('border-right', '2px solid black'), ('text-align', 'center')]},
            {'selector': 'th.col_heading.level1', 'props': [('border-bottom', '2px solid black'), ('min-width', '80px')]},
            {'selector': 'th:last-child, td:last-child', 'props': [('border-right', '2px solid black')]},
            {'selector': 'td', 'props': [('border-bottom', '1px solid #eee'), ('text-align', 'center')]}
        ]).hide(axis="index").to_html(escape=False)
    )
    
    st.markdown(f"<div style='height: 700px; overflow-y: auto;'>{styled_html}</div>", unsafe_allow_html=True)
    
