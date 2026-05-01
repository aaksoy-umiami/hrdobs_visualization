# -*- coding: utf-8 -*-
"""
Purpose:
    Handles Cartesian and geographic mapping methods, generating 2D and 3D spatial plots with optional flight tracks.

Functions/Classes:
    - CartesianMixin: Mixin class providing geographic plotting capabilities.
    - CartesianMixin.plot: Generates a 2D or 3D Cartesian geographic plot.
    - add_flight_tracks: Overlays aircraft flight paths onto an existing geographic plot.
"""

import math
import re
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui_layout import (
    CLR_PRIMARY, CLR_PLOT_BG, CLR_PLOT_GRID,
    FS_PLOT_TICK, TARGET_PLOT_TICKS, PLOT_TITLE_Y,
)
from config import SURFACE_PRESSURE_HPA
from plotter_base import (
    _CONE_DOMAIN_FRACTION,
    _FIG_HEIGHT_BASE,
    _FIG_HEIGHT_Z_THRESHOLD,
    _FIG_HEIGHT_Z_STRETCH,
)
from data_utils import decode_metadata
from vector_utils import build_2d_vector_traces, build_3d_vector_traces


class CartesianMixin:
    
    def plot(self, group_name, variable, z_con, domain_bounds, show_center,
             is_3d=False, z_col=None, thinning_pct=None, marker_size_pct=100,
             time_bounds=None, z_ratio=0.3, vec_scale=1.0, show_basemap=False,
             cen_mode="Location Marker", cen_vector_dir="North", color_scale="Linear scale", custom_colorscale=None):
        """
        Generates a 2D or 3D Cartesian geographic plot for a specific variable.
        """
             
        if group_name not in self.data:
            return None, None

        df = self.data[group_name]
        is_track = 'TRACK' in group_name.upper()

        cols_lower = {c.lower(): c for c in df.columns}
        x_col = next((cols_lower[c] for c in ['lon', 'longitude', 'clon'] if c in cols_lower), None)
        y_col = next((cols_lower[c] for c in ['lat', 'latitude',  'clat'] if c in cols_lower), None)

        if not x_col or not y_col:
            return None, None

        req_cols = [x_col, y_col]
        if not is_track and variable in df.columns:
            req_cols.append(variable)
        if z_col and z_col in df.columns:
            req_cols.append(z_col)

        plot_df, constraint_lbl = self._apply_filters(
            df, req_cols=req_cols, z_con=z_con, time_bounds=time_bounds, 
            thinning_pct=thinning_pct, domain_bounds=domain_bounds if not is_track else None, 
            filter_spatial=True
        )

        if plot_df.empty:
            return None, None

        lats, lons = plot_df[y_col].values, plot_df[x_col].values
        sz_mult  = marker_size_pct / 100.0
        is_vector = variable.lower() in ['wind_vec_hz', 'wind_vec_3d']
        z_vals = plot_df[z_col].values.copy() if (is_3d and z_col and z_col in plot_df.columns) else None

        color_array, cmap, cmin, cmax, cmid, cb_tickvals, cb_ticktext, cb_title, display_name, base_color_array = \
            self._prepare_colorscale(group_name, variable, plot_df, color_scale, custom_colorscale, is_track)

        # Hover data extraction
        t_col = cols_lower.get('time')
        t_vals = plot_df[t_col].values if t_col else np.full(len(plot_df), np.nan)

        z_col_hover = z_col if z_col else next((cols_lower[c] for c in ['height', 'ght', 'altitude', 'elev', 'pres', 'pressure', 'p'] if c in cols_lower), None)
        z_vals_hover = plot_df[z_col_hover].values.astype(float) if (z_col_hover and z_col_hover in plot_df.columns) else np.full(len(plot_df), np.nan)

        z_unit_hover = ""
        z_name_hover = z_col_hover.replace('_', ' ').title() if z_col_hover else "Z"
        if z_col_hover:
            z_meta = self.var_attrs.get(group_name, {}).get(z_col_hover, {})
            z_unit_hover = decode_metadata(z_meta.get('units', ''))
            if 'Pa' in z_unit_hover and 'hPa' not in z_unit_hover:
                z_vals_hover = z_vals_hover / 100.0
                z_unit_hover = "hPa"

        # Observation error and base value extraction
        var_lower = variable.lower()
        is_error_var = var_lower.endswith('err') or var_lower.endswith('_err') or var_lower.endswith('error') or var_lower.endswith('_error')
        
        err_vals = np.full(len(plot_df), np.nan)
        base_vals = np.full(len(plot_df), np.nan)
        err_name_hover = ""
        base_name_hover = ""

        if is_error_var:
            base_cands = [
                var_lower[:-3] if var_lower.endswith('err') else None,
                var_lower[:-4] if var_lower.endswith('_err') else None,
                var_lower[:-5] if var_lower.endswith('error') else None,
                var_lower[:-6] if var_lower.endswith('_error') else None
            ]
            if var_lower == 'wspd_hz_comp_err': base_cands.append('wspd_hz_comp')
            if var_lower == 'wspd_3d_comp_err': base_cands.append('wspd_3d_comp')
            base_cands = [c for c in base_cands if c]

            base_col = next((cols_lower[c] for c in base_cands if c in cols_lower), None)
            if base_col and base_col in plot_df.columns:
                base_vals = plot_df[base_col].values.astype(float)
                base_name_hover = self._get_var_display_name(group_name, base_col)
        else:
            err_cands = [f"{var_lower}err", f"{var_lower}_err", f"{var_lower}_error", f"{var_lower}error"]
            if var_lower in ['wspd_hz_comp', 'wind_vec_hz']: err_cands.append('wspd_hz_comp_err')
            if var_lower in ['wspd_3d_comp', 'wind_vec_3d']: err_cands.append('wspd_3d_comp_err')
            
            err_col = next((cols_lower[c] for c in err_cands if c in cols_lower), None)
            if err_col and err_col in plot_df.columns:
                err_vals = plot_df[err_col].values.astype(float)
                err_name_hover = self._get_var_display_name(group_name, err_col)

        offset = self.metadata.get('time_offset_seconds', 0.0)
        def make_hover(v, t, z, err_v, base_v):
            parts = []
            if not pd.isna(v):
                if is_vector: parts.append(f"Magnitude: {v:,.1f}")
                else:         parts.append(f"{display_name}: {v:,.2f}")
            
            if not pd.isna(err_v):
                parts.append(f"{err_name_hover}: {err_v:,.2f}")
            elif not pd.isna(base_v):
                parts.append(f"{base_name_hover}: {base_v:,.2f}")

            if not pd.isna(t):
                from datetime import datetime, timezone
                if t > 1.9e13:
                    s = f"{t:.0f}"
                    if len(s) == 14: parts.append(f"Time: {s[8:10]}:{s[10:12]}:{s[12:14]} UTC")
                else:
                    dt = datetime.fromtimestamp(t - offset, timezone.utc)
                    parts.append(f"Time: {dt.strftime('%H:%M:%S')} UTC")
            if not pd.isna(z): parts.append(f"{z_name_hover}: {z:,.1f} {z_unit_hover}".strip())
            return "<br>".join(parts) if parts else "NaN"

        text_arr = [make_hover(v, t, z, ev, bv) for v, t, z, ev, bv in zip(base_color_array, t_vals, z_vals_hover, err_vals, base_vals)]

        fig = go.Figure()

        if is_vector:
            u_col, v_col = cols_lower.get('u'), cols_lower.get('v')
            u_vals, v_vals = plot_df[u_col].values, plot_df[v_col].values
            
            if is_3d and z_vals is not None:
                w_col  = cols_lower.get('w')
                w_vals = plot_df[w_col].values if variable.lower() == 'wind_vec_3d' and w_col else np.zeros_like(u_vals)
                
                max_span_x = max(np.nanmax(lons) - np.nanmin(lons), np.nanmax(lats) - np.nanmin(lats))
                z_span = np.nanmax(z_vals) - np.nanmin(z_vals)
                z_scale = (z_span / max_span_x) if max_span_x > 0 else 1.0
                
                vector_traces = build_3d_vector_traces(
                    x0=lons, y0=lats, z0=z_vals, u=u_vals, v=v_vals, w=w_vals,
                    color_vals=color_array, cmap=cmap, cmin=cmin, cmax=cmax, cmid=cmid,
                    cb_tickvals=cb_tickvals, cb_ticktext=cb_ticktext,
                    hover_text=text_arr, display_name=display_name,
                    vec_scale=vec_scale, z_scale_factor=z_scale, arrow_fraction=_CONE_DOMAIN_FRACTION
                )
                for trace in vector_traces: fig.add_trace(trace)
                
            else:
                vector_traces = build_2d_vector_traces(
                    x0=lons, y0=lats, u=u_vals, v=v_vals,
                    color_vals=color_array, cmap=cmap, cmin=cmin, cmax=cmax, cmid=cmid,
                    cb_tickvals=cb_tickvals, cb_ticktext=cb_ticktext,
                    hover_text=text_arr, display_name=display_name,
                    vec_scale=vec_scale, y_scale_factor=1.0, arrow_fraction=_CONE_DOMAIN_FRACTION
                )
                for trace in vector_traces: fig.add_trace(trace)

        elif is_3d and z_vals is not None:
            fig.add_trace(go.Scatter3d(
                x=lons, y=lats, z=z_vals, mode='markers',
                marker=dict(
                    size=4 * sz_mult, color=color_array, colorscale=cmap,
                    colorbar=dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK),
                                  tickvals=cb_tickvals, ticktext=cb_ticktext),
                    cmin=cmin, cmax=cmax, cmid=cmid, opacity=0.8
                ),
                text=text_arr, hoverinfo='text+x+y+z',
                name=group_name, showlegend=False
            ))
        else:
            marker_dict = dict(
                size=9 * sz_mult, color=color_array, colorscale=cmap,
                colorbar=dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK),
                              tickvals=cb_tickvals, ticktext=cb_ticktext),
                cmin=cmin, cmax=cmax, cmid=cmid
            )
            fig.add_trace(go.Scatter(
                x=lons, y=lats, mode='markers', marker=marker_dict,
                text=text_arr, hoverinfo='text+x+y', name=group_name, showlegend=False
            ))

        if show_center and self.metadata.get('storm_center'):
            clat, clon = self.metadata['storm_center']
            use_3d     = is_3d and (z_vals is not None)

            hover_parts = [
                "<b>Storm Center</b>",
                f"Lat: {clat:.2f}, Lon: {clon:.2f}"
            ]

            motion_dir = None
            if cen_mode == "Vector With Dir:":
                if cen_vector_dir == "North":
                    motion_dir = 0.0
                elif cen_vector_dir == "Storm Motion":
                    sm_heading = self.metadata.get('info', {}).get('storm_motion_heading_deg')
                    if sm_heading is not None:
                        try:
                            motion_dir = float(str(sm_heading).strip("[]b'\" "))
                        except Exception:
                            st.toast("⚠️ Could not parse storm direction for vector. Falling back to X.", icon="⚠️")
                    else:
                        st.toast("⚠️ Storm motion missing from metadata. Falling back to X.", icon="⚠️")
                elif cen_vector_dir == "850-200 hPa Shear":
                    if 'ships_params' in self.data and 'shtd_deg' in self.data['ships_params'].columns:
                        motion_dir = float(self.data['ships_params']['shtd_deg'].iloc[0])
                elif cen_vector_dir == "Vortex-Removed 850-200 hPa Shear":
                    if 'ships_params' in self.data and 'sddc_deg' in self.data['ships_params'].columns:
                        motion_dir = float(self.data['ships_params']['sddc_deg'].iloc[0])

            if motion_dir is not None:
                hover_parts.append(f"Vector: {cen_vector_dir}")
                hover_parts.append(f"Direction: {motion_dir:.1f}°")

            center_hover_text = "<br>".join(hover_parts)

            if motion_dir is not None:
                theta = math.radians(90 - motion_dir)

                if domain_bounds:
                    span      = max(domain_bounds['lat_max'] - domain_bounds['lat_min'],
                                    domain_bounds['lon_max'] - domain_bounds['lon_min'])
                    arrow_len = max(span * 0.04, 0.06)
                else:
                    arrow_len = 0.33

                tip_lon = clon + arrow_len * math.cos(theta)
                tip_lat = clat + arrow_len * math.sin(theta)

                wing_len = arrow_len * 0.3
                w1_lon   = tip_lon + wing_len * math.cos(theta + math.radians(150))
                w1_lat   = tip_lat + wing_len * math.sin(theta + math.radians(150))
                w2_lon   = tip_lon + wing_len * math.cos(theta - math.radians(150))
                w2_lat   = tip_lat + wing_len * math.sin(theta - math.radians(150))

                a_lon = [clon, tip_lon, w1_lon, tip_lon, w2_lon]
                a_lat = [clat, tip_lat, w1_lat, tip_lat, w2_lat]

                if use_3d:
                    is_pres  = z_col and any(p in z_col.lower() for p in ['pres', 'pressure', 'p'])
                    z_bottom = np.nanmax(z_vals) if is_pres else np.nanmin(z_vals)
                    fig.add_trace(go.Scatter3d(
                        x=[clon], y=[clat], z=[z_bottom], mode='markers',
                        marker=dict(symbol='circle', size=6, color='black'),
                        name='Center Location', showlegend=False, 
                        hoverinfo='text', hovertext=[center_hover_text]
                    ))
                    fig.add_trace(go.Scatter3d(
                        x=a_lon, y=a_lat, z=[z_bottom] * 5, mode='lines',
                        line=dict(color='black', width=3),
                        name='Storm Motion', showlegend=False, 
                        hoverinfo='text', hovertext=[center_hover_text] * 5
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=[clon], y=[clat], mode='markers',
                        marker=dict(symbol='circle', size=10, color='black'),
                        name='Center Location', showlegend=False, 
                        hoverinfo='text', hovertext=[center_hover_text]
                    ))
                    fig.add_trace(go.Scatter(
                        x=a_lon, y=a_lat, mode='lines',
                        line=dict(color='black', width=2.5),
                        name='Storm Motion', showlegend=False, 
                        hoverinfo='text', hovertext=[center_hover_text] * 5
                    ))
            else:
                if use_3d:
                    is_pres  = z_col and any(p in z_col.lower() for p in ['pres', 'pressure', 'p'])
                    z_bottom = np.nanmax(z_vals) if is_pres else np.nanmin(z_vals)
                    fig.add_trace(go.Scatter3d(
                        x=[clon], y=[clat], z=[z_bottom], mode='markers',
                        marker=dict(symbol='x', size=5, color='black',
                                    line=dict(color='black', width=1.5)),
                        name='Center', showlegend=False, 
                        hoverinfo='text', hovertext=[center_hover_text]
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=[clon], y=[clat], mode='markers',
                        marker=dict(symbol='x', size=12, color='black',
                                    line=dict(color='black', width=1.5)),
                        name='Center', showlegend=False, 
                        hoverinfo='text', hovertext=[center_hover_text]
                    ))

        nice_title = self._format_title(group_name, variable, constraint_lbl)

        x_range, y_range, z_range = None, None, None
        if domain_bounds:
            x_range = [domain_bounds['lon_min'], domain_bounds['lon_max']]
            y_range = [domain_bounds['lat_min'], domain_bounds['lat_max']]
            if 'z_min' in domain_bounds:
                z_range = [domain_bounds['z_min'], domain_bounds['z_max']]
                if domain_bounds.get('z_col') and any(
                        p in domain_bounds['z_col'].lower()
                        for p in ['pres', 'pressure', 'p']):
                    z_range = [domain_bounds['z_max'], domain_bounds['z_min']]

        if is_3d and z_vals is not None:
            z_ax_title = z_col
            if z_col:
                is_pres = any(p in z_col.lower() for p in ['pres', 'pressure', 'p'])
                z_meta = self.var_attrs.get(group_name, {}).get(z_col, {})
                z_units = decode_metadata(z_meta.get('units', 'hPa' if is_pres else 'm'))
                
                if is_pres and 'Pa' in z_units and 'hPa' not in z_units:
                    z_units = 'hPa'
                    
                if is_pres:
                    z_ax_title = f"Pressure ({z_units})"
                elif any(h in z_col.lower() for h in ['height', 'ght', 'altitude', 'elev']):
                    z_ax_title = f"Height ({z_units})"

            scene_dict = dict(
                aspectmode='manual',
                aspectratio=dict(x=1, y=1, z=z_ratio),
                xaxis_title="Longitude (deg)", yaxis_title="Latitude (deg)", zaxis_title=z_ax_title,
                xaxis=dict(range=x_range, nticks=20), yaxis=dict(range=y_range, nticks=20),
                zaxis=dict(range=z_range, nticks=10)
            )

            if z_col and any(p in z_col.lower() for p in ['pres', 'pressure', 'p']):
                scene_dict['zaxis']['autorange'] = 'reversed'

            scene_dict['camera'] = dict(eye=dict(x=1.5, y=-1.5, z=1.0 + (z_ratio * 0.8)))

            dynamic_height = (_FIG_HEIGHT_BASE
                              if z_ratio <= _FIG_HEIGHT_Z_THRESHOLD
                              else int(_FIG_HEIGHT_BASE +
                                       (z_ratio - _FIG_HEIGHT_Z_THRESHOLD) * _FIG_HEIGHT_Z_STRETCH))

            fig.update_layout(
                title={'text': nice_title, 'x': 0.5, 'xanchor': 'center',
                       'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
                width=800, height=dynamic_height,
                showlegend=False,
                scene=scene_dict,
                margin=dict(l=60, r=40, b=40, t=self._title_top_margin(nice_title))
            )
        else:
            _FIG_W          = 700
            _ML, _MR, _MB   = 100, 100, 80
            _MT             = self._title_top_margin(nice_title)
            if domain_bounds and domain_bounds.get('lat_max') is not None:
                lat_range = domain_bounds['lat_max'] - domain_bounds['lat_min']
                lon_range = domain_bounds['lon_max'] - domain_bounds['lon_min']
                aspect    = lat_range / lon_range if lon_range > 0 else 1.0
            else:
                aspect = 1.0
            _PA_W = _FIG_W - _ML - _MR
            _PA_H = int(max(280, min(700, _PA_W * aspect)))
            _FIG_H = _PA_H + _MT + _MB

            if show_basemap and domain_bounds:
                from plotter_basemap import get_basemap_traces
                for bm_trace in get_basemap_traces(domain_bounds):
                    fig.add_trace(bm_trace)
                    fig.data = (fig.data[-1],) + fig.data[:-1]

            fig.update_layout(
                title={'text': nice_title, 'x': 0.5, 'xanchor': 'center',
                       'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
                width=_FIG_W, height=_FIG_H,
                autosize=False,
                showlegend=False,
                xaxis=dict(
                    title='Longitude (deg)',
                    tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                    range=x_range,
                    showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
                    showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                    constrain='domain',
                ),
                yaxis=dict(
                    title='Latitude (deg)',
                    tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                    range=y_range,
                    showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
                    showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                    scaleanchor='x', scaleratio=1,
                    constrain='domain',
                ),
                plot_bgcolor=CLR_PLOT_BG,
                paper_bgcolor=CLR_PLOT_BG,
                margin=dict(autoexpand=False, l=_ML, r=_MR, t=_MT, b=_MB),
            )

        return fig, plot_df

def add_flight_tracks(fig, data_pack, track_mapping, plot_track, selected_platform,
                      is_3d, is_target_pres, proj_option="Bottom Only",
                      domain_bounds=None):
    """
    Overlays aircraft flight paths onto an existing geographic plot.
    """
    for plat, track_group in track_mapping.items():
        track_df  = data_pack['data'][track_group]
        t_lat_c   = next((c for c in track_df.columns if c.lower() in ['lat', 'latitude']),  None)
        t_lon_c   = next((c for c in track_df.columns if c.lower() in ['lon', 'longitude']), None)
        is_visible = plot_track and selected_platform == plat

        if t_lat_c and t_lon_c:
            if not is_3d:
                use_geo = len(fig.data) > 0 and fig.data[0].type == 'scattergeo'
                if use_geo:
                    fig.add_trace(go.Scattergeo(
                        lon=track_df[t_lon_c], lat=track_df[t_lat_c], mode='lines',
                        line=dict(color='black', width=1), name=f'{plat} Flight Track',
                        showlegend=False, visible=is_visible
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=track_df[t_lon_c], y=track_df[t_lat_c], mode='lines',
                        line=dict(color='black', width=1), name=f'{plat} Flight Track',
                        showlegend=False, visible=is_visible
                    ))
            else:
                t_z_options = [c for c in track_df.columns
                               if c.lower() in (
                                   ['pres', 'pressure', 'p'] if is_target_pres
                                   else ['height', 'ght', 'altitude', 'elev', 'pressure_altitude']
                               )]
                t_z_c = t_z_options[0] if t_z_options else None

                if t_z_c:
                    t_z_vals = track_df[t_z_c].copy()

                    fig.add_trace(go.Scatter3d(
                        x=track_df[t_lon_c], y=track_df[t_lat_c], z=t_z_vals,
                        mode='lines', line=dict(color='black', width=2),
                        name=f'{plat} Flight Track', showlegend=False, visible=is_visible
                    ))

                    show_bottom = proj_option in ["Bottom Only", "Bottom + Sides"]
                    show_sides  = proj_option in ["Sides Only",  "Bottom + Sides"]

                    if show_bottom:
                        if domain_bounds and 'z_min' in domain_bounds:
                            floor_z = (domain_bounds['z_max'] if is_target_pres
                                       else domain_bounds['z_min'])
                        else:
                            floor_z = (max(SURFACE_PRESSURE_HPA, np.nanmax(t_z_vals))
                                       if is_target_pres
                                       else min(0.0, np.nanmin(t_z_vals)))

                        z_shadow = np.full_like(t_z_vals, floor_z)
                        fig.add_trace(go.Scatter3d(
                            x=track_df[t_lon_c], y=track_df[t_lat_c], z=z_shadow,
                            mode='lines', line=dict(color='lightgray', width=2),
                            name=f'{plat} Surface Reflection',
                            showlegend=False, visible=is_visible
                        ))

                    if show_sides:
                        lon_wall   = (domain_bounds['lon_min'] if domain_bounds
                                      else track_df[t_lon_c].min())
                        lat_wall   = (domain_bounds['lat_max'] if domain_bounds
                                      else track_df[t_lat_c].max())

                        lon_shadow = np.full_like(track_df[t_lon_c], lon_wall)
                        fig.add_trace(go.Scatter3d(
                            x=lon_shadow, y=track_df[t_lat_c], z=t_z_vals,
                            mode='lines', line=dict(color='lightgray', width=2),
                            name=f'{plat} Lon Wall Reflection',
                            showlegend=False, visible=is_visible
                        ))

                        lat_shadow = np.full_like(track_df[t_lat_c], lat_wall)
                        fig.add_trace(go.Scatter3d(
                            x=track_df[t_lon_c], y=lat_shadow, z=t_z_vals,
                            mode='lines', line=dict(color='lightgray', width=2),
                            name=f'{plat} Lat Wall Reflection',
                            showlegend=False, visible=is_visible
                        ))
    return fig