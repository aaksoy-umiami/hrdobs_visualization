# -*- coding: utf-8 -*-
"""
ui_viewer.py
------------
File Data Viewer tab entry point.

All sidebar controls live in ui_viewer_controls.py.
This module is responsible only for:
  1. Initialising session state
  2. Calling render_viewer_controls() to get a ViewerIntent
  3. Enforcing the auto-thinning guard
  4. Calling StormPlotter.plot() and add_flight_tracks()
  5. Displaying the resulting figure
"""

import streamlit as st
import numpy as np
import pandas as pd

from ui_layout import apply_viewer_compaction_css
from ui_viewer_controls import render_viewer_controls
from plotter import StormPlotter, add_flight_tracks

# Maximum scatter points before auto-thinning kicks in
_MAX_PLOT_POINTS = 50_000


def render_viewer_tab():
    apply_viewer_compaction_css()

    # Restore v_ keys from the persistence dict on first load
    if 'viewer_state' not in st.session_state:
        st.session_state.viewer_state = {}
    for k, v in st.session_state.viewer_state.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # Build the plotter (or a stub if no file is loaded yet)
    data_pack = st.session_state.get('data_pack')
    if data_pack is not None:
        plotter = StormPlotter(
            data_pack['data'], data_pack['track'],
            data_pack['meta'], data_pack['var_attrs']
        )
    else:
        plotter = None

    # Render all sidebar controls and collect intent
    intent = render_viewer_controls(plotter)

    if intent.data_pack is None:
        st.info("👈 Please upload an AI-Ready HDF5 file from the sidebar to visualize its contents.")
        return

    # Refresh plotter in case file was just loaded this run
    data_pack = intent.data_pack
    plotter   = StormPlotter(
        data_pack['data'], data_pack['track'],
        data_pack['meta'], data_pack['var_attrs']
    )

    if not intent.plot_var:
        return

    # ------------------------------------------------------------------
    # Auto-thinning guard
    # ------------------------------------------------------------------
    sel_group = intent.sel_group
    plot_var  = intent.plot_var

    if 'TRACK' not in sel_group.upper() and plot_var in data_pack['data'].get(sel_group, {}):
        df_sel     = data_pack['data'][sel_group]
        cols_lower = {c.lower(): c for c in df_sel.columns}
        x_c = next((cols_lower[c] for c in ['lon', 'longitude'] if c in cols_lower), None)
        y_c = next((cols_lower[c] for c in ['lat', 'latitude']  if c in cols_lower), None)
        domain = intent.domain_bounds

        req_cols = [c for c in [x_c, y_c, plot_var] if c]
        if intent.plot_z_col and intent.plot_z_col in df_sel.columns:
            req_cols.append(intent.plot_z_col)

        if all(req_cols):
            temp_df = df_sel.dropna(subset=req_cols)
            if domain:
                mask = (
                    (temp_df[y_c] >= domain['lat_min']) &
                    (temp_df[y_c] <= domain['lat_max']) &
                    (temp_df[x_c] >= domain['lon_min']) &
                    (temp_df[x_c] <= domain['lon_max'])
                )
                if intent.plot_z_col and 'z_min' in domain:
                    z_col = domain['z_col']
                    z_v   = (temp_df[z_col] / 100.0
                             if domain.get('z_convert') else temp_df[z_col])
                    mask &= (z_v >= domain['z_min']) & (z_v <= domain['z_max'])
                temp_df = temp_df[mask]

            valid_count  = len(temp_df)
            thin_pct_val = intent.thin_pct if intent.apply_thinning else 100
            expected     = int(valid_count * thin_pct_val / 100.0)

            if expected > _MAX_PLOT_POINTS and valid_count > 0:
                safe_pct = (_MAX_PLOT_POINTS / valid_count) * 100
                st.session_state._force_thinning    = True
                st.session_state._force_thin_pct    = max(5, int(safe_pct / 5) * 5)
                st.session_state.show_auto_thin_msg = True
                st.rerun()

    if st.session_state.pop('show_auto_thin_msg', False):
        st.toast(
            f"⚡ **Auto-Thinning Applied!**\n\nDataset inside domain was too large. "
            f"Automatically snapped thinning to **{st.session_state.v_thin_pct}%**.",
            icon="⚡"
        )

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------
    active_thinning = intent.thin_pct if intent.apply_thinning else None

    if intent.plot_type == "Radial-Height Profile" and intent.sr_track_grp:
        fig, plot_df = plotter.plot_radial_height(
            sel_group, plot_var,
            intent.sr_track_grp,
            domain_bounds=intent.domain_bounds,
            thinning_pct=active_thinning,
            marker_size_pct=intent.marker_sz,
            time_bounds=intent.time_bounds,
            color_scale=intent.color_scale,
            rh_z_col=intent.rh_z_col,
        )
    elif intent.plot_type == "Horizontal Storm-Relative" and intent.sr_track_grp:
        fig, plot_df = plotter.plot_storm_relative(
            sel_group, plot_var,
            intent.z_con, intent.domain_bounds,
            sr_track_grp=intent.sr_track_grp,
            up_convention=intent.sr_up_convention,
            thinning_pct=active_thinning,
            marker_size_pct=intent.marker_sz,
            time_bounds=intent.time_bounds,
            color_scale=intent.color_scale,
            show_center=intent.show_cen,
            cen_mode=intent.cen_mode,
        )
    else:
        fig, plot_df = plotter.plot(
            sel_group, plot_var,
            intent.z_con, intent.domain_bounds, intent.show_cen,
            is_3d=intent.is_3d,
            z_col=intent.plot_z_col if (intent.is_3d and intent.plot_z_col) else None,
            thinning_pct=active_thinning,
            marker_size_pct=intent.marker_sz,
            time_bounds=intent.time_bounds,
            z_ratio=intent.z_ratio,
            vec_scale=intent.vec_scale,
            show_basemap=intent.show_basemap,
            cen_mode=intent.cen_mode,
            color_scale=intent.color_scale,
        )

    if fig is not None:
        # Flight track overlay — Cartesian, SR, and RH modes handled separately
        if intent.plot_type == "Horizontal Cartesian":
            is_target_pres = intent.plot_z_col and any(
                p in intent.plot_z_col.lower() for p in ['pres', 'pressure', 'p']
            )
            fig = add_flight_tracks(
                fig, data_pack,
                intent.track_mapping, intent.plot_track,
                intent.selected_platform, intent.is_3d,
                is_target_pres, intent.track_proj,
                intent.domain_bounds
            )
        elif intent.plot_type == "Horizontal Storm-Relative" and intent.plot_track:
            import plotly.graph_objects as go
            for plat, track_group in intent.track_mapping.items():
                if plat != intent.selected_platform:
                    continue
                track_df = data_pack['data'].get(track_group)
                if track_df is None or track_df.empty:
                    continue
                tcl = {c.lower(): c for c in track_df.columns}
                t_lon_c = next((tcl[c] for c in ['lon', 'longitude'] if c in tcl), None)
                t_lat_c = next((tcl[c] for c in ['lat', 'latitude']  if c in tcl), None)
                t_time_c = tcl.get('time')
                if not (t_lon_c and t_lat_c and t_time_c):
                    continue
                tdf = track_df[[t_lon_c, t_lat_c, t_time_c]].dropna()
                if tdf.empty:
                    continue
                try:
                    result = plotter._to_storm_relative(
                        tdf[t_lon_c].values, tdf[t_lat_c].values,
                        tdf[t_time_c].values,
                        intent.sr_track_grp, intent.sr_up_convention
                    )
                    if result is not None:
                        x_km, y_km, _, _, _ = result
                        fig.add_trace(go.Scatter(
                            x=x_km, y=y_km, mode='lines',
                            line=dict(color='black', width=1),
                            name=f'{plat} Flight Track',
                            showlegend=False, hoverinfo='skip'
                        ))
                except Exception:
                    pass
        elif (intent.plot_type == "Radial-Height Profile" and
              intent.plot_track and intent.track_proj == "Show"):
            import plotly.graph_objects as go
            for plat, track_group in intent.track_mapping.items():
                if plat != intent.selected_platform:
                    continue
                track_df = data_pack['data'].get(track_group)
                if track_df is None or track_df.empty:
                    continue
                tcl = {c.lower(): c for c in track_df.columns}
                t_lon_c  = next((tcl[c] for c in ['lon', 'longitude'] if c in tcl), None)
                t_lat_c  = next((tcl[c] for c in ['lat', 'latitude']  if c in tcl), None)
                t_time_c = tcl.get('time')
                # Match the same Z column the observations are using
                if intent.rh_z_col and intent.rh_z_col.lower() in tcl:
                    t_z_c = tcl[intent.rh_z_col.lower()]
                else:
                    t_z_c = next((tcl[c] for c in
                                  ['height', 'ght', 'altitude', 'elev', 'pres', 'pressure', 'p']
                                  if c in tcl), None)
                if not (t_lon_c and t_lat_c and t_time_c and t_z_c):
                    continue
                tdf = track_df[[t_lon_c, t_lat_c, t_time_c, t_z_c]].dropna()
                if tdf.empty:
                    continue
                # Convert Pa → hPa for pressure if needed (to match obs axis)
                t_z_vals = tdf[t_z_c].values.copy().astype(float)
                is_pres_track = any(p in t_z_c.lower() for p in ['pres', 'pressure', 'p'])
                if is_pres_track and t_z_vals.max() > 1100:
                    t_z_vals = t_z_vals / 100.0
                try:
                    result = plotter._to_storm_relative(
                        tdf[t_lon_c].values, tdf[t_lat_c].values,
                        tdf[t_time_c].values,
                        intent.sr_track_grp, "Relative to North"
                    )
                    if result is not None:
                        _, _, track_range_km, _, _ = result
                        fig.add_trace(go.Scatter(
                            x=track_range_km, y=t_z_vals, mode='lines',
                            line=dict(color='black', width=1),
                            name=f'{plat} Flight Track',
                            showlegend=False, hoverinfo='skip'
                        ))
                        # Expand Y axis to include track z values outside obs range
                        current_range = fig.layout.yaxis.range
                        if current_range and len(t_z_vals) > 0:
                            t_z_min = float(np.nanmin(t_z_vals))
                            t_z_max = float(np.nanmax(t_z_vals))
                            is_pres_axis = (intent.rh_z_col and any(
                                p in intent.rh_z_col.lower() for p in ['pres', 'pressure', 'p']))
                            if is_pres_axis:
                                # Pressure: axis is [high_p, low_p] (reversed)
                                new_lo = min(current_range[1], t_z_min)  # lower pressure = higher altitude
                                new_hi = max(current_range[0], t_z_max)  # higher pressure = lower altitude
                                fig.update_layout(yaxis_range=[new_hi, new_lo])
                            else:
                                new_lo = min(current_range[0], t_z_min)
                                new_hi = max(current_range[1], t_z_max)
                                fig.update_layout(yaxis_range=[new_lo, new_hi])
                except Exception:
                    pass
        col_left, col_center, col_right = st.columns([1, 8, 1])
        with col_center:
            st.plotly_chart(fig, use_container_width=False)
