# -*- coding: utf-8 -*-

"""
ui_explorer_table.py
----------
Formats and renders the filtered inventory results as a styled HTML multi-index table with group-separated columns and hover tooltips on storm names.
It also includes a summary table renderer that groups active results by individual storms.
"""

import pandas as pd
import streamlit as st
from config import EXPECTED_GROUPS, CAT_ORDER, MS_TO_KTS

def display_summary_table(final_df, unit):
    """Formats and renders a summary table grouped by storm."""
    if final_df.empty:
        st.info("No data to summarize.")
        return

    mult = MS_TO_KTS if unit == "knots" else 1.0

    df = final_df.copy()
    
    # Safely extract Storm ID from filename (e.g., 'hrdobs_BERYL02L_2024...' -> 'BERYL02L')
    extracted_id = df['Constructed_File_Name'].str.extract(r'(?i)([A-Z]+\d{2}[A-Z])')[0]
    df['Storm_ID'] = extracted_id.str.upper().fillna(df['Storm'])

    # Natural lifecycle order for categories
    cat_order = {c: i for i, c in enumerate(CAT_ORDER)}

    summary_data = []

    # Sort to ensure chronological order for cycles
    df = df.sort_values(by=['Storm_ID', 'Cycle_Raw'])

    for storm_id, grp in df.groupby('Storm_ID', sort=False):
        year = grp['Year'].iloc[0]
        total_cycles = len(grp)

        # Extract sorting keys
        start_cycle = grp['Cycle_Raw'].iloc[0]
        storm_num = str(storm_id)[-3:] if len(str(storm_id)) >= 3 else str(storm_id)

        # Date Range
        c_min_disp = grp['Cycle_Display'].iloc[0].replace('\xa0', ' ')
        c_max_disp = grp['Cycle_Display'].iloc[-1].replace('\xa0', ' ')
        date_range = f"{c_min_disp} - {c_max_disp}" if c_min_disp != c_max_disp else c_min_disp

        # Lat/Lon ranges
        lat_min, lat_max = grp['Lat'].min(), grp['Lat'].max()
        lat_range = f"{lat_min:.1f} - {lat_max:.1f}" if pd.notna(lat_min) else ""

        lon_min, lon_max = grp['Lon'].min(), grp['Lon'].max()
        lon_range = f"{lon_min:.1f} - {lon_max:.1f}" if pd.notna(lon_min) else ""

        # Intensity/MSLP ranges
        int_min, int_max = grp['Intensity_ms'].min() * mult, grp['Intensity_ms'].max() * mult
        int_range = f"{int_min:.1f} - {int_max:.1f}" if pd.notna(int_min) else ""

        p_min, p_max = grp['MSLP_hPa'].min(), grp['MSLP_hPa'].max()
        p_range = f"{p_min:.1f} - {p_max:.1f}" if pd.notna(p_min) else ""

        # SHIPS Ranges
        def get_rng(col, fmt="{:.1f}"):
            if col not in grp.columns: return ""
            cmin, cmax = grp[col].min(), grp[col].max()
            if pd.isna(cmin) or pd.isna(cmax): return ""
            return f"{fmt.format(cmin)} - {fmt.format(cmax)}"
            
        shear_range = get_rng('shrd_kt')
        mpi_range = get_rng('vmpi_kt')
        rh_range = get_rng('rhmd_pct', "{:.0f}")

        # Sorted Unique Categories
        unique_cats = grp['TC_Category'].dropna().unique()
        sorted_cats = sorted(unique_cats, key=lambda x: cat_order.get(x, 99))
        cats_str = "-".join(sorted_cats)

        row = {
            'Year': year,
            '_Storm_Num': storm_num,       # Hidden column for sorting
            '_Start_Cycle': start_cycle,   # Hidden column for sorting
            'Storm': storm_id,
            'Total Cycles': total_cycles,
            'Date Range': date_range,
            'Lat Range': lat_range,
            'Lon Range': lon_range,
            'Intensity Range': int_range,
            'MSLP Range': p_range,
            'Categories': cats_str,
            'Shear Range': shear_range,
            'MPI Range': mpi_range,
            'RH Range': rh_range
        }

        # Observations / Cycles Count for each Platform
        for g in EXPECTED_GROUPS:
            if g in grp.columns:
                obs_sum = pd.to_numeric(grp[g], errors='coerce').fillna(0).sum()
                cycles_count = (pd.to_numeric(grp[g], errors='coerce').fillna(0) > 0).sum()
                if cycles_count > 0:
                    row[g] = f"{int(obs_sum):,} / {int(cycles_count)}"
                else:
                    row[g] = ""
            else:
                row[g] = ""

        summary_data.append(row)

    sum_df = pd.DataFrame(summary_data)

    # --- Apply the new sorting logic ---
    if not sum_df.empty:
        sum_df = sum_df.sort_values(by=['Year', '_Storm_Num', '_Start_Cycle'], ascending=[True, True, True])
        sum_df = sum_df.drop(columns=['_Storm_Num', '_Start_Cycle']).reset_index(drop=True)

    # Build MultiIndex structure dynamically
    multi_cols = []
    group_starts = []
    current_top = None

    raw_columns = ['Year', 'Storm', 'Total Cycles', 'Date Range', 'Lat Range', 'Lon Range', 'Intensity Range', 'MSLP Range', 'Categories', 'Shear Range', 'MPI Range', 'RH Range'] + EXPECTED_GROUPS

    final_cols = []
    for raw_col in raw_columns:
        if raw_col not in sum_df.columns:
            continue

        if raw_col == 'Year': tup = ('Basic Data', 'Year')
        elif raw_col == 'Storm': tup = ('Basic Data', 'Storm')
        elif raw_col == 'Total Cycles': tup = ('Basic Data', 'Total Cycles')
        elif raw_col == 'Date Range': tup = ('Basic Data', 'Date Range')
        elif raw_col == 'Lat Range': tup = ('Basic Data', 'Lat Range<br>°N')
        elif raw_col == 'Lon Range': tup = ('Basic Data', 'Lon Range<br>°W')
        elif raw_col == 'Intensity Range': tup = ('Basic Data', f'Intensity Range<br>({unit})')
        elif raw_col == 'MSLP Range': tup = ('Basic Data', 'MSLP Range<br>(hPa)')
        elif raw_col == 'Categories': tup = ('Basic Data', 'Categories')
        # --- New SHIPS Parameters ---
        elif raw_col == 'Shear Range': tup = ('SHIPS Environment', 'Shear Range<br>(kt)')
        elif raw_col == 'MPI Range': tup = ('SHIPS Environment', 'MPI Range<br>(kt)')
        elif raw_col == 'RH Range': tup = ('SHIPS Environment', 'Mid RH Range<br>(%)')
        # ----------------------------
        else:
            top = 'Basic Data'
            bottom = raw_col
            suffix = ' (Num. Observations / Cycles Available)'
            
            if raw_col.startswith('dropsonde_'): top = 'Dropsondes' + suffix; bottom = raw_col.replace('dropsonde_', '').upper()
            elif raw_col.startswith('flight_level_hdobs_'): top = 'Flight Level' + suffix; bottom = raw_col.replace('flight_level_hdobs_', '').upper()
            elif raw_col.startswith('sfmr_'): top = 'SFMR' + suffix; bottom = raw_col.replace('sfmr_', '').upper()
            elif raw_col.startswith('tdr_'): top = 'Tail Doppler Radar (TDR)' + suffix; bottom = raw_col.replace('tdr_', '').upper()
            elif raw_col.startswith('track_'):
                top = 'Track Data' + suffix
                bottom = 'Best Track' if 'best' in raw_col.lower() else 'Spline' if 'spline' in raw_col.lower() else 'Vortex' if 'vortex' in raw_col.lower() else raw_col
            tup = (top, bottom)

        if tup[0] != current_top:
            group_starts.append(len(multi_cols) + 1)
            current_top = tup[0]

        multi_cols.append(tup)
        final_cols.append(raw_col)

    sum_df = sum_df[final_cols]
    sum_df.columns = pd.MultiIndex.from_tuples(multi_cols)

    # Styling
    thick_sel = ", ".join([f"th:nth-child({idx}), td:nth-child({idx})" for idx in group_starts])

    styled_html = (
        sum_df.style
        .set_properties(**{'text-align': 'center', 'padding': '4px', 'font-size': '13px', 'white-space': 'nowrap'})
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

    st.markdown(f"<div style='max-height: 400px; overflow-x: auto; overflow-y: auto;'>{styled_html}</div>", unsafe_allow_html=True)


def display_explorer_table(final_df, unit, sort_col_internal, is_asc):
    """Formats and renders the Pandas dataframe as a custom HTML block."""
    
    final_df['Storm_Display'] = final_df.apply(lambda x: f"{x['Storm']}|||{x['Constructed_File_Name']}", axis=1)

    base_cols = ['Year', 'Storm_Display', 'Basin', 'Cycle_Display', 'Lat', 'Lon', 'Intensity_ms', 'MSLP_hPa', 'TC_Category']
    ships_cols = ['incv_kt', 'dtl_km', 'shrd_kt', 'shtd_deg', 'rhmd_pct', 'vmpi_kt']
    
    # Ensure SHIPS columns exist in the dataframe to avoid errors on older DBs
    ships_present = [c for c in ships_cols if c in final_df.columns]
    
    display_df = final_df[base_cols + ships_present + EXPECTED_GROUPS].copy()
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
        # --- New SHIPS Parameters ---
        elif raw_col == 'incv_kt': tup = ('SHIPS Environment', 'Int Change<br>(kt)'); fmt_map[tup] = '{:,.1f}'; numeric_cols.append(tup)
        elif raw_col == 'dtl_km': tup = ('SHIPS Environment', 'Dist to Land<br>(km)'); fmt_map[tup] = '{:,.0f}'; numeric_cols.append(tup)
        elif raw_col == 'shrd_kt': tup = ('SHIPS Environment', 'Shear Mag<br>(kt)'); fmt_map[tup] = '{:,.1f}'; numeric_cols.append(tup)
        elif raw_col == 'shtd_deg': tup = ('SHIPS Environment', 'Shear Dir<br>(deg)'); fmt_map[tup] = '{:,.0f}'; numeric_cols.append(tup)
        elif raw_col == 'rhmd_pct': tup = ('SHIPS Environment', 'Mid RH<br>(%)'); fmt_map[tup] = '{:,.0f}'; numeric_cols.append(tup)
        elif raw_col == 'vmpi_kt': tup = ('SHIPS Environment', 'MPI<br>(kt)'); fmt_map[tup] = '{:,.1f}'; numeric_cols.append(tup)
        # ----------------------------
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
    