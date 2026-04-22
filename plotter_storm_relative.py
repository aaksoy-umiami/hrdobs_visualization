# -*- coding: utf-8 -*-
"""
plotter_storm_relative.py
-------------------------
Storm-relative horizontal mapping methods for StormPlotter.
"""

import math
import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.colors
import streamlit as st

from data_utils import decode_metadata
from ui_layout import (
    CLR_PRIMARY, CLR_PLOT_BG, CLR_PLOT_GRID,
    FS_PLOT_TICK, TARGET_PLOT_TICKS, PLOT_TITLE_Y,
)
from config import (
    GLOBAL_VAR_CONFIG, EARTH_R_KM, DEFAULT_SR_MAX_RANGE, 
    SR_RING_CANDIDATES
)

from vector_utils import build_2d_vector_traces


class StormRelativeMixin:

    def _rotate_vectors_to_storm_motion(self, u, v, heading_deg):
        """
        Rotates U and V wind components so that 'Up' aligns with the provided heading.
        """
        theta = np.radians(heading_deg)
        u_rot = u * np.cos(theta) - v * np.sin(theta)
        v_rot = u * np.sin(theta) + v * np.cos(theta)
        return u_rot, v_rot

    def _to_storm_relative(self, obs_lons, obs_lats, obs_times, track_grp, up_convention):
        from datetime import datetime, timezone

        track_df = self.data[track_grp]
        tcols    = {c.lower(): c for c in track_df.columns}
        t_col    = tcols.get('time')
        lat_col  = next((tcols[c] for c in ['lat', 'latitude', 'clat']  if c in tcols), None)
        lon_col  = next((tcols[c] for c in ['lon', 'longitude', 'clon'] if c in tcols), None)
        if not all([t_col, lat_col, lon_col]):
            return None

        offset = self.metadata.get('time_offset_seconds', 0.0)
        def _ts(v):
            from datetime import datetime, timezone
            try:
                if pd.isna(v): return np.nan
                if v > 1.9e13:
                    dt = datetime.strptime(f"{v:.0f}", '%Y%m%d%H%M%S')
                    return dt.replace(tzinfo=timezone.utc).timestamp()
                return float(v) - offset
            except Exception:
                return np.nan

        track_epochs = np.array([_ts(v) for v in track_df[t_col].values])
        track_lats   = track_df[lat_col].values.astype(float)
        track_lons   = track_df[lon_col].values.astype(float)

        order        = np.argsort(track_epochs)
        track_epochs = track_epochs[order]
        track_lats   = track_lats[order]
        track_lons   = track_lons[order]

        obs_epochs = np.array([_ts(v) for v in obs_times])

        cen_lats = np.interp(obs_epochs, track_epochs, track_lats)
        cen_lons = np.interp(obs_epochs, track_epochs, track_lons)

        dlat     = np.radians(obs_lats - cen_lats)
        dlon     = np.radians(obs_lons - cen_lons)
        mean_lat = np.radians((obs_lats + cen_lats) / 2.0)
        x_km     = EARTH_R_KM * dlon * np.cos(mean_lat)
        y_km     = EARTH_R_KM * dlat

        range_km    = np.sqrt(x_km**2 + y_km**2)
        azimuth_deg = np.degrees(np.arctan2(x_km, y_km)) % 360

        mean_heading = None
        if up_convention == "Storm Motion":
            # 1. Try to get explicit heading from new metadata
            sm_heading = self.metadata.get('info', {}).get('storm_motion_heading_deg')
            if sm_heading is not None:
                try:
                    mean_heading = float(str(sm_heading).strip("[]b'\" "))
                except Exception:
                    pass
            
            # 2. Fallback to track calculation if metadata is missing/unparseable
            if mean_heading is None:
                dlat_tr     = np.diff(track_lats)
                dlon_tr     = np.diff(track_lons)
                mean_lat_tr = np.radians((track_lats[:-1] + track_lats[1:]) / 2.0)
                dy_tr       = EARTH_R_KM * np.radians(dlat_tr)
                dx_tr       = EARTH_R_KM * np.radians(dlon_tr) * np.cos(mean_lat_tr)
                headings    = np.degrees(np.arctan2(dx_tr, dy_tr)) % 360
                mean_heading = float(np.nanmedian(headings))
        elif up_convention == "850-200 hPa Shear":
            if 'ships_params' in self.data and 'shtd_deg' in self.data['ships_params'].columns:
                mean_heading = float(self.data['ships_params']['shtd_deg'].iloc[0])
        elif up_convention == "Vortex-Removed 850-200 hPa Shear":
            if 'ships_params' in self.data and 'sddc_deg' in self.data['ships_params'].columns:
                mean_heading = float(self.data['ships_params']['sddc_deg'].iloc[0])

        if mean_heading is not None and up_convention != "North":
            theta_rad = np.radians(mean_heading)
            x_rot     = x_km * np.cos(theta_rad) - y_km * np.sin(theta_rad)
            y_rot     = x_km * np.sin(theta_rad) + y_km * np.cos(theta_rad)

            x_km, y_km = x_rot, y_rot
            azimuth_deg = (azimuth_deg - mean_heading) % 360

        return x_km, y_km, range_km, azimuth_deg, mean_heading

    def get_sr_max_range(self, group_name, sr_track_grp, df_override=None):
        if group_name not in self.data or sr_track_grp not in self.data:
            return DEFAULT_SR_MAX_RANGE
        df         = df_override if df_override is not None else self.data[group_name]
        cols_lower = {c.lower(): c for c in df.columns}
        lat_col    = next((cols_lower[c] for c in ['lat', 'latitude', 'clat']  if c in cols_lower), None)
        lon_col    = next((cols_lower[c] for c in ['lon', 'longitude', 'clon'] if c in cols_lower), None)
        time_col   = cols_lower.get('time')
        if not all([lat_col, lon_col, time_col]):
            return DEFAULT_SR_MAX_RANGE
        df = df.dropna(subset=[lat_col, lon_col, time_col])
        if df.empty:
            return DEFAULT_SR_MAX_RANGE
        result = self._to_storm_relative(
            df[lon_col].values, df[lat_col].values,
            df[time_col].values, sr_track_grp, "North"
        )
        if result is None:
            return DEFAULT_SR_MAX_RANGE
        _, _, range_km, _, _ = result
        raw_max      = float(np.nanmax(range_km))
        ring_spacing = 25.0 if raw_max <= 150 else 50.0 if raw_max <= 500 else 100.0
        return float(np.ceil(raw_max / ring_spacing) * ring_spacing)

    def plot_storm_relative(self, group_name, variable, z_con,
                            domain_bounds, sr_track_grp,
                            up_convention="North",
                            thinning_pct=None, marker_size_pct=100,
                            vec_scale=1.0, time_bounds=None, color_scale="Linear scale",
                            show_center=True, cen_mode="Location Marker",
                            cen_vector_dir="North", custom_colorscale=None):
                            
        if group_name not in self.data:
            return None, None

        df = self.data[group_name]
        cols_lower = {c.lower(): c for c in df.columns}

        lat_col  = next((cols_lower[c] for c in ['lat', 'latitude', 'clat']  if c in cols_lower), None)
        lon_col  = next((cols_lower[c] for c in ['lon', 'longitude', 'clon'] if c in cols_lower), None)
        time_col = cols_lower.get('time')
        
        if not all([lat_col, lon_col, time_col, variable in df.columns]):
            return None, None

        plot_df, constraint_lbl = self._apply_filters(
            df, req_cols=[lat_col, lon_col, time_col, variable], z_con=z_con,
            time_bounds=time_bounds, thinning_pct=thinning_pct,
            domain_bounds=domain_bounds, filter_spatial=False
        )

        if plot_df.empty:
            return None, None

        result = self._to_storm_relative(
            plot_df[lon_col].values, plot_df[lat_col].values,
            plot_df[time_col].values, sr_track_grp, up_convention
        )
        if result is None:
            return None, None

        x_km, y_km, range_km, azimuth_deg, mean_heading = result

        sr_max_range = None
        if domain_bounds and '_sr_max_range_km' in domain_bounds:
            sr_max_range = float(domain_bounds['_sr_max_range_km'])
        if sr_max_range is not None:
            mask        = range_km <= sr_max_range
            x_km        = x_km[mask]
            y_km        = y_km[mask]
            range_km    = range_km[mask]
            azimuth_deg = azimuth_deg[mask]
            plot_df     = plot_df[mask]

        if plot_df.empty:
            return None, None

        plot_df['_sr_x_km']    = x_km
        plot_df['_sr_y_km']    = y_km
        plot_df['_sr_range']   = range_km
        plot_df['_sr_az']      = azimuth_deg

        _var_conf_sr = GLOBAL_VAR_CONFIG.get(variable.lower(), {})
        _filtered_sr_vals = plot_df[variable].values
        if variable.lower() == 'time':
            _tr = self._convert_time_to_relative(_filtered_sr_vals)
            if _tr is not None:
                _filtered_sr_vals = _tr[0]
        _full_cmin = float(_var_conf_sr['cmin']) if _var_conf_sr.get('cmin') is not None else (
            float(np.nanmin(_filtered_sr_vals)) if len(_filtered_sr_vals) > 0 else 0.0)
        _full_cmax = float(_var_conf_sr['cmax']) if _var_conf_sr.get('cmax') is not None else (
            float(np.nanmax(_filtered_sr_vals)) if len(_filtered_sr_vals) > 0 else 1.0)
        if variable.lower() == 'time':
            _full_cmin = max(_full_cmin, -10800.0)
            _full_cmax = min(_full_cmax,  10800.0)

        var_conf   = GLOBAL_VAR_CONFIG.get(variable.lower(), {})
        cmap       = custom_colorscale if custom_colorscale else var_conf.get('colorscale', 'Jet')
        cmid_conf  = var_conf.get('cmid')
        color_vals = plot_df[variable].values
        
        display_name = self._get_var_display_name(group_name, variable)
        cb_title     = display_name

        cb_tickvals, cb_ticktext = None, None
        if variable.lower() == 'time':
            _ax         = {}
            color_vals  = self._apply_time_axis(variable, color_vals, _ax, is_x=False)
            cb_tickvals = _ax.get('tickvals')
            cb_ticktext = _ax.get('ticktext')
            cb_title    = "Time rel. to cycle center"

        cmin = _full_cmin
        cmax = _full_cmax
        cmid = float(cmid_conf) if cmid_conf is not None else None

        if color_scale == "Log scale":
            pos_mask = color_vals > 0
            log_c    = np.full_like(color_vals, np.nan, dtype=float)
            log_c[pos_mask] = np.log10(color_vals[pos_mask])
            color_vals = log_c
            real_cmin  = (_full_cmin if _full_cmin > 0
                          else (float(np.nanmin(plot_df[variable].values[plot_df[variable].values > 0]))
                                if pos_mask.any() else 1e-3))
            real_cmax  = (_full_cmax if _full_cmax > 0
                          else (float(np.nanmax(plot_df[variable].values[plot_df[variable].values > 0]))
                                if pos_mask.any() else 1.0))
            cmin = np.log10(real_cmin)
            cmax = np.log10(real_cmax)
            cmid = None
            mn, mx     = int(np.floor(cmin)), int(np.ceil(cmax))
            cb_tickvals = np.arange(mn, mx + 1, dtype=float) if mx > mn else [cmin, cmax]
            cb_ticktext = [f"1e{int(p)}" if p < -3 or p > 3 else f"{10**p:g}"
                           for p in cb_tickvals]

        sz_mult  = marker_size_pct / 100.0
        raw_max  = float(np.nanmax(range_km)) if len(range_km) > 0 else 200.0
        padded   = sr_max_range if sr_max_range is not None else raw_max

        _candidates  = SR_RING_CANDIDATES
        ring_spacing = next(
            (c for c in _candidates if 3 <= padded / c <= 8),
            _candidates[-1] if padded > 250 else _candidates[0]
        )
        max_range  = np.ceil(padded / ring_spacing) * ring_spacing
        ring_radii = np.arange(ring_spacing, max_range + ring_spacing * 0.01, ring_spacing)

        theta_ring = np.linspace(0, 2 * np.pi, 360)
        spoke_len  = max_range

        fig = go.Figure()

        for r in ring_radii:
            fig.add_trace(go.Scatter(
                x=r * np.sin(theta_ring),
                y=r * np.cos(theta_ring),
                mode='lines',
                line=dict(color=CLR_PLOT_GRID, width=1, dash='dot'),
                showlegend=False, hoverinfo='skip',
                name=f'{r:.0f} km ring'
            ))

        for angle_deg in [0, 90, 180, 270]:
            sx = spoke_len * np.sin(np.radians(angle_deg))
            sy = spoke_len * np.cos(np.radians(angle_deg))
            fig.add_trace(go.Scatter(
                x=[0, sx], y=[0, sy],
                mode='lines',
                line=dict(color=CLR_PLOT_GRID, width=1),
                showlegend=False, hoverinfo='skip'
            ))

        # --- HOVER DATA EXTRACTION ---
        z_col_hover = next((cols_lower[c] for c in ['height', 'ght', 'altitude', 'elev', 'pres', 'pressure', 'p'] if c in cols_lower), None)
        if z_col_hover and z_col_hover in plot_df.columns:
            z_vals_hover = plot_df[z_col_hover].values.astype(float)
        else:
            z_vals_hover = np.full(len(plot_df), np.nan)

        z_unit_hover = ""
        z_name_hover = z_col_hover.replace('_', ' ').title() if z_col_hover else "Z"
        if z_col_hover:
            z_meta = self.var_attrs.get(group_name, {}).get(z_col_hover, {})
            z_unit_hover = decode_metadata(z_meta.get('units', ''))
            if 'Pa' in z_unit_hover and 'hPa' not in z_unit_hover:
                z_vals_hover = z_vals_hover / 100.0
                z_unit_hover = "hPa"
        
        offset = self.metadata.get('time_offset_seconds', 0.0)
        def make_sr_hover(r, a, v, t, z):
            parts = [f"Range: {r:.1f} km", f"Az: {a:.1f}°"]
            if not pd.isna(v):
                parts.append(f"{cb_title}: {v:,.2f}")
            if not pd.isna(t):
                from datetime import datetime, timezone
                if t > 1.9e13:
                    s = f"{t:.0f}"
                    if len(s) == 14:
                        parts.append(f"Time: {s[8:10]}:{s[10:12]}:{s[12:14]} UTC")
                else:
                    dt = datetime.fromtimestamp(t - offset, timezone.utc)
                    parts.append(f"Time: {dt.strftime('%H:%M:%S')} UTC")
            if not pd.isna(z):
                parts.append(f"{z_name_hover}: {z:,.1f} {z_unit_hover}".strip())
            return "<br>".join(parts)

        t_vals = plot_df[time_col].values
        hover_text = [make_sr_hover(r, a, v, t, z) for r, a, v, t, z in zip(range_km, azimuth_deg, plot_df[variable].values, t_vals, z_vals_hover)]

        is_vector = variable.lower() in ['wind_vec_hz', 'wind_vec_3d']
        
        if is_vector and 'u' in cols_lower and 'v' in cols_lower:
            u_col, v_col = cols_lower['u'], cols_lower['v']
            u_vals, v_vals = plot_df[u_col].values, plot_df[v_col].values
            
            if up_convention != "Relative to North" and mean_heading is not None:
                u_rot, v_rot = self._rotate_vectors_to_storm_motion(u_vals, v_vals, mean_heading)
            else:
                u_rot, v_rot = u_vals, v_vals
                
            vector_traces = build_2d_vector_traces(
                x0=x_km, y0=y_km, u=u_rot, v=v_rot,
                color_vals=color_vals, cmap=cmap, cmin=cmin, cmax=cmax, cmid=cmid,
                cb_tickvals=cb_tickvals, cb_ticktext=cb_ticktext,
                hover_text=hover_text, display_name=display_name,
                vec_scale=vec_scale, y_scale_factor=1.0, arrow_fraction=0.05
            )
            for trace in vector_traces: fig.add_trace(trace)
            
        else:
            marker_dict = dict(
                size=9 * sz_mult,
                color=color_vals,
                colorscale=cmap,
                cmin=cmin, cmax=cmax, cmid=cmid,
                showscale=True,
                colorbar=dict(
                    len=0.8, thickness=15,
                    tickfont=dict(size=FS_PLOT_TICK),
                    tickvals=cb_tickvals,
                    ticktext=cb_ticktext
                )
            )

            fig.add_trace(go.Scatter(
                x=x_km, y=y_km,
                mode='markers',
                marker=marker_dict,
                text=hover_text,
                hoverinfo='text',
                showlegend=False
            ))

        if show_center:
            vector_dir = None
            if cen_mode == "Vector With Dir:":
                if cen_vector_dir == "North":
                    vector_dir = 0.0
                elif cen_vector_dir == "Storm Motion":
                    sm_heading = self.metadata.get('info', {}).get('storm_motion_heading_deg')
                    if sm_heading is not None:
                        try:
                            vector_dir = float(str(sm_heading).strip("[]b'\" "))
                        except Exception:
                            st.toast("⚠️ Could not parse storm direction for vector. Falling back to X.", icon="⚠️")
                    else:
                        st.toast("⚠️ Storm motion missing from metadata. Falling back to X.", icon="⚠️")
                elif cen_vector_dir == "850-200 hPa Shear":
                    if 'ships_params' in self.data and 'shtd_deg' in self.data['ships_params'].columns:
                        vector_dir = float(self.data['ships_params']['shtd_deg'].iloc[0])
                elif cen_vector_dir == "Vortex-Removed 850-200 hPa Shear":
                    if 'ships_params' in self.data and 'sddc_deg' in self.data['ships_params'].columns:
                        vector_dir = float(self.data['ships_params']['sddc_deg'].iloc[0])

            if vector_dir is not None:
                # Rotate the arrow based on our new up_convention
                if up_convention != "Relative to North" and mean_heading is not None:
                    rotated_dir = vector_dir - mean_heading
                else:
                    rotated_dir = vector_dir
                    
                rot_rad = math.radians(rotated_dir)
                dx      = math.sin(rot_rad)
                dy      = math.cos(rot_rad)

                arrow_len  = max_range * 0.12
                tip_x      = dx * arrow_len
                tip_y      = dy * arrow_len

                wing_len   = arrow_len * 0.3
                wing_angle = math.radians(150)
                base_angle = math.atan2(dx, dy)
                w1_x       = tip_x + wing_len * math.sin(base_angle + wing_angle)
                w1_y       = tip_y + wing_len * math.cos(base_angle + wing_angle)
                w2_x       = tip_x + wing_len * math.sin(base_angle - wing_angle)
                w2_y       = tip_y + wing_len * math.cos(base_angle - wing_angle)

                fig.add_trace(go.Scatter(
                    x=[0, tip_x, w1_x, tip_x, w2_x],
                    y=[0, tip_y, w1_y, tip_y, w2_y],
                    mode='lines',
                    line=dict(color=CLR_PRIMARY, width=2),
                    showlegend=False, hoverinfo='skip'
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=[0], y=[0], mode='markers+text',
                    marker=dict(symbol='x', size=14, color=CLR_PRIMARY,
                                line=dict(width=2)),
                    text=['TC'], textposition='top center',
                    textfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                    showlegend=False, hoverinfo='text',
                    hovertext=['Storm center']
                ))

        # Dynamic Axis Titles Based on Convention
        if up_convention == "North":
            up_label = "North"
            x_ax_title = "East–West Distance from Center (km)"
            y_ax_title = "North–South Distance from Center (km)"
        elif up_convention == "Storm Motion":
            up_label = "Storm Motion"
            x_ax_title = "Cross-Track Distance from Center (km)"
            y_ax_title = "Along-Track Distance from Center (km)"
        elif up_convention == "850-200 hPa Shear":
            up_label = "850-200 hPa Shear"
            x_ax_title = "Cross-Shear Distance from Center (km)"
            y_ax_title = "Along-Shear Distance from Center (km)"
        elif up_convention == "Vortex-Removed 850-200 hPa Shear":
            up_label = "Vortex-Removed 850-200 hPa Shear"
            x_ax_title = "Cross-Shear Distance from Center (km)"
            y_ax_title = "Along-Shear Distance from Center (km)"
        else:
            up_label = up_convention
            x_ax_title = "Cross-Track Distance from Center (km)"
            y_ax_title = "Along-Track Distance from Center (km)"

        nice_title   = self._format_title(group_name, variable,
                                          f"Storm-Relative | Up: {up_label}")
        _MT          = self._title_top_margin(nice_title)
        _FIG_W       = 700
        _ML, _MR, _MB = 100, 100, 80
        _FIG_H        = _FIG_W

        axis_lim = max_range

        fig.update_layout(
            title={'text': nice_title, 'x': 0.5, 'xanchor': 'center',
                   'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
            width=_FIG_W, height=_FIG_H,
            autosize=False,
            showlegend=False,
            xaxis=dict(
                title=x_ax_title,
                tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                range=[-axis_lim, axis_lim],
                dtick=ring_spacing, tick0=0,
                showgrid=True, gridcolor=CLR_PLOT_GRID, zeroline=False,
                showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                constrain='domain', scaleanchor='y', scaleratio=1,
            ),
            yaxis=dict(
                title=y_ax_title,
                tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                range=[-axis_lim, axis_lim],
                dtick=ring_spacing, tick0=0,
                showgrid=True, gridcolor=CLR_PLOT_GRID, zeroline=False,
                showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                constrain='domain',
            ),
            plot_bgcolor=CLR_PLOT_BG,
            paper_bgcolor=CLR_PLOT_BG,
            margin=dict(autoexpand=False, l=_ML, r=_MR, t=_MT, b=_MB),
        )

        return fig, plot_df
    