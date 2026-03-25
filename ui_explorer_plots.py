# -*- coding: utf-8 -*-
"""
ui_explorer_plots.py
--------------------
Standalone module for rendering summary visualizations in the Dataset Explorer tab.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from basemap import get_basemap_traces
from ui_layout import (
    CLR_PLOT_BG, CLR_PRIMARY, FS_PLOT_TICK, 
    PLOT_HEIGHT_MAP, PLOT_MARGINS_MAP, 
    PLOT_HEIGHT_SUMMARY, PLOT_MARGINS_SUMMARY
)
from config import (
    CAT_COLORS, CAT_ORDER, CAT_FULL_NAMES, PLATFORM_COLORS, MS_TO_KTS,
    DOMAIN_LAT_MIN, DOMAIN_LAT_MAX, DOMAIN_LON_MIN, DOMAIN_LON_MAX
)

def render_explorer_summary_plots(df: pd.DataFrame, unit: str):
    """
    Renders an expandable section containing summary visualizations 
    for the currently filtered Dataset Explorer inventory.
    """
    with st.expander("📊 View Summary Graphics of Filtered Results", expanded=False):
        if df.empty:
            st.info("No data available to plot.")
            return

        # ---------------------------------------------------------------------
        # 1. Prepare Master Unclipped Dataframe (For the 3 Bottom Plots)
        # ---------------------------------------------------------------------
        plot_df = df.copy()

        if 'Storm' in plot_df.columns and 'Year' in plot_df.columns:
            plot_df['Storm_ID'] = plot_df['Storm'].astype(str) + ' (' + plot_df['Year'].astype(str) + ')'
        else:
            plot_df['Storm_ID'] = 'Unknown'

        # Convert Intensity and apply display units
        if 'Intensity_ms' in plot_df.columns:
            plot_df['Intensity_Converted'] = pd.to_numeric(plot_df['Intensity_ms'], errors='coerce') * (MS_TO_KTS if unit == 'knots' else 1.0)
            if unit == 'knots':
                plot_df['Intensity_Str'] = plot_df['Intensity_Converted'].round().astype('Int64').astype(str)
            else:
                plot_df['Intensity_Str'] = plot_df['Intensity_Converted'].map('{:.1f}'.format)
        else:
            plot_df['Intensity_Converted'] = np.nan
            plot_df['Intensity_Str'] = "N/A"

        # ---------------------------------------------------------------------
        # 2. Prepare Clipped Dataframe (Strictly for the Top Map)
        # ---------------------------------------------------------------------
        if 'Lat' in plot_df.columns and 'Lon' in plot_df.columns:
            plot_df['Lat'] = pd.to_numeric(plot_df['Lat'], errors='coerce')
            plot_df['Lon'] = pd.to_numeric(plot_df['Lon'], errors='coerce')
            
            # Negate Longitude for standard Western Hemisphere mapping
            plot_df['Lon_Plot'] = -plot_df['Lon'].abs()
            
            mask = (
                (plot_df['Lat'] >= DOMAIN_LAT_MIN) & (plot_df['Lat'] <= DOMAIN_LAT_MAX) &
                (plot_df['Lon_Plot'] >= DOMAIN_LON_MIN) & (plot_df['Lon_Plot'] <= DOMAIN_LON_MAX)
            )
            map_df = plot_df[mask].dropna(subset=['Lat', 'Lon_Plot']).copy()
            
            if 'Year' in map_df.columns and 'Storm' in map_df.columns and 'Cycle_Raw' in map_df.columns:
                map_df = map_df.sort_values(by=['Year', 'Storm', 'Cycle_Raw'])
        else:
            map_df = pd.DataFrame()

        # =====================================================================
        # TOP ROW: The Geographic Map 
        # =====================================================================
        if map_df.empty:
            st.info("No valid coordinates fall within the map domain.")
        else:
            fig = go.Figure()
            
            domain_bounds = {
                'lat_min': DOMAIN_LAT_MIN, 'lat_max': DOMAIN_LAT_MAX, 
                'lon_min': DOMAIN_LON_MIN, 'lon_max': DOMAIN_LON_MAX
            }
            
            # Layer 0: Basemap
            for bm_trace in get_basemap_traces(domain_bounds):
                bm_trace.line.color = 'rgba(100, 100, 100, 0.6)'
                fig.add_trace(bm_trace)

            # Layer 1: Connecting Track Lines
            for storm_id in map_df['Storm_ID'].unique():
                storm_data = map_df[map_df['Storm_ID'] == storm_id]
                fig.add_trace(go.Scatter(
                    x=storm_data['Lon_Plot'], y=storm_data['Lat'], mode='lines',
                    line=dict(width=1.5, color='rgba(100, 100, 100, 0.4)'),
                    showlegend=False, hoverinfo='skip'
                ))

            # Layer 2: Category Markers
            existing_cats = set(map_df['TC_Category'].unique())
            current_cats = [c for c in CAT_ORDER if c in existing_cats] + [c for c in existing_cats if c not in CAT_ORDER]

            for cat in current_cats:
                cat_data = map_df[map_df['TC_Category'] == cat]
                if not cat_data.empty:
                    hover_text = (
                        "<b>" + cat_data['Storm_ID'] + "</b><br>" +
                        "Cycle: " + cat_data['Cycle_Display'].astype(str) + "<br>" +
                        "Lat: " + cat_data['Lat'].map('{:.2f}'.format) + "<br>" +
                        "Lon: " + cat_data['Lon'].map('{:.2f}'.format) + "<br>" +
                        "Intensity: " + cat_data['Intensity_Str'] + f" {unit}<br>" +
                        "MSLP: " + pd.to_numeric(cat_data['MSLP_hPa'], errors='coerce').map('{:.1f}'.format) + " hPa"
                    )
                    fig.add_trace(go.Scatter(
                        x=cat_data['Lon_Plot'], y=cat_data['Lat'], mode='markers',
                        marker=dict(size=7, color=CAT_COLORS.get(cat, '#ffffff'), line=dict(width=1, color='black')),
                        name=cat, text=hover_text, hoverinfo='text'
                    ))

            fig.update_layout(
                title={'text': "Geographic Distribution by Intensity Category", 'x': 0.5, 'xanchor': 'center', 'xref': 'paper'},
                margin=PLOT_MARGINS_MAP, paper_bgcolor=CLR_PLOT_BG, plot_bgcolor=CLR_PLOT_BG, height=PLOT_HEIGHT_MAP,
                xaxis=dict(title='Longitude', range=[DOMAIN_LON_MIN, DOMAIN_LON_MAX], showgrid=True, gridcolor='rgba(200, 200, 200, 0.4)',
                           zeroline=False, dtick=10, showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                           tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY)),
                yaxis=dict(title='Latitude', range=[DOMAIN_LAT_MIN, DOMAIN_LAT_MAX], showgrid=True, gridcolor='rgba(200, 200, 200, 0.4)',
                           zeroline=False, dtick=10, showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                           scaleanchor='x', scaleratio=1, constrain='domain', tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY)),
                legend=dict(title=dict(text='Category'), yanchor="top", y=0.96, xanchor="left", x=0.01,
                            bgcolor="rgba(255, 255, 255, 0.85)", bordercolor="black", borderwidth=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        # =====================================================================
        # BOTTOM ROW: 3 Summary Plots
        # =====================================================================
        c1, c2, c3 = st.columns(3)

        # --- Plot 1: Histogram of Categories ---
        with c1:
            counts = plot_df['TC_Category'].value_counts() if 'TC_Category' in plot_df.columns else pd.Series()
            # Show all categories except 'Unknown' when it has zero count
            active_cats    = [cat for cat in CAT_ORDER
                              if cat != 'Unknown' or counts.get(cat, 0) > 0]
            ordered_counts = [counts.get(cat, 0) for cat in active_cats]
            hover_texts_hist = [f"<b>{CAT_FULL_NAMES.get(cat, cat)}</b><br>Cycles: {int(cnt):,}"
                                 for cat, cnt in zip(active_cats, ordered_counts)]

            fig_hist = go.Figure(data=[
                go.Bar(
                    x=active_cats, y=ordered_counts,
                    marker_color=[CAT_COLORS.get(cat, '#ffffff') for cat in active_cats],
                    marker_line=dict(width=1, color='black'),
                    hovertext=hover_texts_hist, hoverinfo='text'
                )
            ])
            
            fig_hist.update_layout(
                title={'text': "Cycles by Category", 'x': 0.5, 'xanchor': 'center', 'xref': 'paper'},
                margin=PLOT_MARGINS_SUMMARY, paper_bgcolor=CLR_PLOT_BG, plot_bgcolor=CLR_PLOT_BG, height=PLOT_HEIGHT_SUMMARY,
                xaxis=dict(title='', tickangle=-45, showgrid=False, showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                           tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY), fixedrange=True, automargin=False),
                yaxis=dict(title='File Count', showgrid=True, gridcolor='rgba(200, 200, 200, 0.4)',
                           showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                           tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY), fixedrange=True, automargin=False)
            )
            
            # Ground Line
            fig_hist.add_shape(type='line', xref='paper', yref='y', x0=0, x1=1, y0=0, y1=0, line=dict(color=CLR_PRIMARY, width=2))
            st.plotly_chart(fig_hist, use_container_width=True)

        # --- Plot 2: Wind-Pressure Relationship ---
        with c2:
            if 'MSLP_hPa' in plot_df.columns:
                wp_df = plot_df.copy()
                wp_df['MSLP_hPa'] = pd.to_numeric(wp_df['MSLP_hPa'], errors='coerce')
                wp_df = wp_df.dropna(subset=['Intensity_Converted', 'MSLP_hPa'])
            else:
                wp_df = pd.DataFrame()
            
            if wp_df.empty:
                st.info("Not enough valid data for Wind-Pressure plot.")
            else:
                fig_wp = go.Figure()
                
                # Markers
                for cat in CAT_ORDER:
                    cat_data = wp_df[wp_df['TC_Category'] == cat] if 'TC_Category' in wp_df.columns else pd.DataFrame()
                    if not cat_data.empty:
                        hover_t = ("<b>" + cat_data['Storm_ID'] + "</b><br>" + "Intensity: " + cat_data['Intensity_Str'] + f" {unit}<br>" +
                                   "MSLP: " + cat_data['MSLP_hPa'].map('{:.1f}'.format) + " hPa")
                        fig_wp.add_trace(go.Scatter(
                            x=cat_data['Intensity_Converted'], y=cat_data['MSLP_hPa'], mode='markers',
                            marker=dict(size=6, color=CAT_COLORS.get(cat, '#ffffff'), line=dict(width=0.5, color='black'), opacity=0.8),
                            name=cat, text=hover_t, hoverinfo='text', showlegend=False
                        ))

                # Regression Line & X-Axis Formatting
                x = wp_df['Intensity_Converted']
                y = wp_df['MSLP_hPa']
                if len(x) > 0:
                    x_min, x_max = x.min(), x.max()
                    if x_min == x_max: 
                        x_max += 1
                    
                    x_ticks = np.linspace(x_min, x_max, 4).round().astype(int) if unit == 'knots' else np.linspace(x_min, x_max, 4)
                    tick_fmt = '.0f' if unit == 'knots' else '.1f'
                    
                    if len(x) > 1 and x.nunique() > 1:
                        slope, intercept = np.polyfit(x, y, 1)
                        r_sq = (np.corrcoef(x, y)[0, 1] ** 2) * 100
                        
                        fig_wp.add_trace(go.Scatter(
                            x=np.array([x.min(), x.max()]), y=slope * np.array([x.min(), x.max()]) + intercept,
                            mode='lines', line=dict(color='black', width=2, dash='dash'), hoverinfo='skip', showlegend=False
                        ))
                        fig_wp.add_annotation(
                            x=0.96, y=0.96, xref='paper', yref='paper', xanchor='right', yanchor='top',
                            text=f"R² = {r_sq:.2f}%", showarrow=False, bgcolor="rgba(255, 255, 255, 0.85)", 
                            bordercolor="black", borderwidth=1, font=dict(color="black", size=12)
                        )

                fig_wp.update_layout(
                    title={'text': "Wind-Pressure Rel.", 'x': 0.5, 'xanchor': 'center', 'xref': 'paper'}, 
                    margin=PLOT_MARGINS_SUMMARY, paper_bgcolor=CLR_PLOT_BG, plot_bgcolor=CLR_PLOT_BG, height=PLOT_HEIGHT_SUMMARY,
                    xaxis=dict(title=f'Intensity ({unit})', tickmode='array', tickvals=x_ticks, tickformat=tick_fmt,   
                               showgrid=True, gridcolor='rgba(200, 200, 200, 0.4)', showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                               tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY), fixedrange=True, automargin=False),
                    yaxis=dict(title='MSLP (hPa)', showgrid=True, gridcolor='rgba(200, 200, 200, 0.4)',
                               showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                               tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY), fixedrange=True, automargin=False)
                )
                st.plotly_chart(fig_wp, use_container_width=True)

        # --- Plot 3: Observations Bar Chart ---
        with c3:
            def get_metrics(*cols):
                """Safely aggregate sums and counts for specified columns."""
                sv, m = 0, pd.Series(False, index=plot_df.index)
                for c in cols:
                    if c in plot_df.columns:
                        nc = pd.to_numeric(plot_df[c], errors='coerce').fillna(0)
                        sv += nc.sum()
                        m = m | (nc > 0)
                return sv, m.sum()

            # Assemble data groupings matching configuration definitions
            obs_data = [
                # Group 1: Dropsondes
                [
                    (*get_metrics('dropsonde_noaa42', 'dropsonde_noaa43'), PLATFORM_COLORS['NOAA P-3'], 'NOAA P-3'), 
                    (*get_metrics('dropsonde_noaa49'), PLATFORM_COLORS['NOAA G-IV'], 'NOAA G-IV'), 
                    (*get_metrics('dropsonde_usaf'), PLATFORM_COLORS['Air Force'], 'Air Force'), 
                    (*get_metrics('dropsonde_ghawk'), PLATFORM_COLORS['NASA Global Hawk'], 'NASA Global Hawk')
                ],
                # Group 2: Flight Level
                [
                    (*get_metrics('flight_level_hdobs_noaa42', 'flight_level_hdobs_noaa43'), PLATFORM_COLORS['NOAA P-3'], 'NOAA P-3'), 
                    (*get_metrics('flight_level_hdobs_noaa49'), PLATFORM_COLORS['NOAA G-IV'], 'NOAA G-IV'), 
                    (*get_metrics('flight_level_hdobs_usaf'), PLATFORM_COLORS['Air Force'], 'Air Force')
                ],
                # Group 3: SFMR
                [
                    (*get_metrics('sfmr_noaa42', 'sfmr_noaa43'), PLATFORM_COLORS['NOAA P-3'], 'NOAA P-3'), 
                    (*get_metrics('sfmr_usaf'), PLATFORM_COLORS['Air Force'], 'Air Force')
                ],
                # Group 4: TDR
                [
                    (*get_metrics('tdr_noaa42', 'tdr_noaa43'), PLATFORM_COLORS['NOAA P-3'], 'NOAA P-3'), 
                    (*get_metrics('tdr_noaa49'), PLATFORM_COLORS['NOAA G-IV'], 'NOAA G-IV')
                ],
                # Group 5: Tracks
                [(*get_metrics('track_vortex_message'), PLATFORM_COLORS['Tracks'], 'Tracks')], 
                [(*get_metrics('track_best_track'), PLATFORM_COLORS['Tracks'], 'Tracks')], 
                [(*get_metrics('track_spline_track'), PLATFORM_COLORS['Tracks'], 'Tracks')]
            ]

            group_labels = ['Dropsondes', 'Flight Level', 'SFMR', 'TDR', 'Vortex Msg.', 'Best Track', 'High-Res. Track']
            barWidth, groupGap = 0.35, 0.8
            x_vals, y_vals, colors, hover_texts, groupCenters, currX = [], [], [], [], [], 0

            # Compute explicit mathematical spacing for bar groups
            for idx, bars in enumerate(obs_data):
                k = len(bars)
                if k == 0: 
                    currX += groupGap
                    groupCenters.append(np.nan)
                    continue
                
                xi = currX + np.arange(k) * barWidth
                groupCenters.append(np.mean(xi))
                
                for j, (ov, cv, clr, plat) in enumerate(bars):
                    x_vals.append(xi[j])
                    y_vals.append(ov if ov > 0 else 0)
                    colors.append(clr)
                    hover_texts.append(f"<b>{plat}</b><br>Cycles: {int(cv):,}<br>Obs: {int(ov):,}")
                
                currX += k * barWidth + groupGap

            fig_obs = go.Figure(data=[
                go.Bar(
                    x=x_vals, y=y_vals, marker_color=colors, marker_line=dict(width=1, color='black'), 
                    width=barWidth, hovertext=hover_texts, hoverinfo='text', showlegend=False
                )
            ])
            
            # Inject interactive horizontal legend
            for label, color in PLATFORM_COLORS.items():
                fig_obs.add_trace(go.Scatter(
                    x=[None], y=[None], mode='markers', name=label, 
                    marker=dict(symbol='square', size=6, color=color, line=dict(width=1, color='black')), 
                    showlegend=True
                ))

            fig_obs.update_layout(
                title={'text': "Number of Observations", 'x': 0.5, 'xanchor': 'center', 'xref': 'paper'}, 
                margin=PLOT_MARGINS_SUMMARY, paper_bgcolor=CLR_PLOT_BG, plot_bgcolor=CLR_PLOT_BG, height=PLOT_HEIGHT_SUMMARY,
                xaxis=dict(title='', tickvals=groupCenters, ticktext=group_labels, tickangle=-45, showgrid=False, showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                           tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY), fixedrange=True, range=[-barWidth, currX - groupGap + barWidth], automargin=False),
                yaxis=dict(title='', type='log', range=[0, 10], dtick=1, showgrid=True, gridcolor='rgba(200, 200, 200, 0.4)', showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                           tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY), fixedrange=True, automargin=False),
                legend=dict(orientation="h", yanchor="top", y=0.99, xanchor="center", x=0.5, bgcolor="rgba(255, 255, 255, 0.85)", bordercolor="black", borderwidth=1, font=dict(size=9, color="black"), itemsizing="trace")
            )
            
            # Ground Line
            fig_obs.add_shape(type='line', xref='paper', yref='paper', x0=0, x1=1, y0=0, y1=0, line=dict(color=CLR_PRIMARY, width=2))
            st.plotly_chart(fig_obs, use_container_width=True)
            