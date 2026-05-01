# -*- coding: utf-8 -*-
"""
Purpose:
    Provides methods for generating 2D radial-height profile plots, including decomposition of wind vectors.

Functions/Classes:
    - RadialHeightMixin: Mixin class for generating radial-height profile plots.
    - RadialHeightMixin._decompose_radial_tangential: Converts U and V wind components into Radial and Tangential components.
    - RadialHeightMixin.plot_radial_height: Generates a 2D radial-height profile plot.
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
    GLOBAL_VAR_CONFIG, EARTH_R_KM, RH_RING_CANDIDATES
)

from vector_utils import build_2d_vector_traces


class RadialHeightMixin:

    def _decompose_radial_tangential(self, u, v, azimuth_deg):
        """
        Converts U and V wind components into Radial and Tangential components.
        """
        phi = np.radians(azimuth_deg)
        v_radial = u * np.sin(phi) + v * np.cos(phi)
        v_tangential = -u * np.cos(phi) + v * np.sin(phi)
        return v_radial, v_tangential

    def plot_radial_height(self, group_name, variable, sr_track_grp,
                           domain_bounds=None, thinning_pct=None,
                           marker_size_pct=100, vec_scale=1.0, time_bounds=None,
                           color_scale="Linear scale", rh_z_col=None,
                           custom_colorscale=None):
        """
        Generates a 2D radial-height profile plot.
        """
                           
        if group_name not in self.data:
            return None, None

        df         = self.data[group_name]
        cols_lower = {c.lower(): c for c in df.columns}

        lat_col  = next((cols_lower[c] for c in ['lat', 'latitude', 'clat']  if c in cols_lower), None)
        lon_col  = next((cols_lower[c] for c in ['lon', 'longitude', 'clon'] if c in cols_lower), None)
        time_col = cols_lower.get('time')

        if rh_z_col and rh_z_col in df.columns:
            z_col = rh_z_col
        else:
            z_col = next((cols_lower[c] for c in
                          ['height', 'ght', 'altitude', 'elev', 'pres', 'pressure', 'p']
                          if c in cols_lower), None)

        if not all([lat_col, lon_col, time_col, z_col, variable in df.columns]):
            return None, None

        plot_df, constraint_lbl = self._apply_filters(
            df, req_cols=[lat_col, lon_col, time_col, z_col, variable],
            z_con=None, time_bounds=time_bounds, thinning_pct=thinning_pct,
            domain_bounds=domain_bounds, filter_spatial=False
        )

        if plot_df.empty:
            return None, None

        result = self._to_storm_relative(
            plot_df[lon_col].values, plot_df[lat_col].values,
            plot_df[time_col].values, sr_track_grp, "Relative to North"
        )
        if result is None:
            return None, None

        _, _, range_km, azimuth_deg, _ = result

        sr_max_range = None
        if domain_bounds and '_sr_max_range_km' in domain_bounds:
            sr_max_range = float(domain_bounds['_sr_max_range_km'])
        if sr_max_range is not None:
            mask        = range_km <= sr_max_range
            range_km    = range_km[mask]
            azimuth_deg = azimuth_deg[mask]
            plot_df     = plot_df[mask]

        if plot_df.empty:
            return None, None

        plot_df['_rh_range_km']    = range_km

        z_vals     = plot_df[z_col].values
        color_vals = plot_df[variable].values

        is_pres = any(p in z_col.lower() for p in ['pres', 'pressure', 'p'])
        z_meta  = self.var_attrs.get(group_name, {}).get(z_col, {})
        z_units = decode_metadata(z_meta.get('units', 'hPa' if is_pres else 'm'))
        if is_pres and 'Pa' in z_units and 'hPa' not in z_units:
            z_vals  = z_vals / 100.0
            z_units = 'hPa'
        z_label = f"{'Pressure' if is_pres else 'Height'} ({z_units})"

        var_conf   = GLOBAL_VAR_CONFIG.get(variable.lower(), {})
        cmap       = custom_colorscale if custom_colorscale else var_conf.get('colorscale', 'Jet')
        cmid_conf  = var_conf.get('cmid')
        cmid       = float(cmid_conf) if cmid_conf is not None else None
        cb_tickvals, cb_ticktext = None, None

        _color_work = color_vals.copy().astype(float)
        if variable.lower() == 'time':
            _ax         = {}
            _color_work = self._apply_time_axis(variable, _color_work, _ax, is_x=False)
            cb_tickvals = _ax.get('tickvals')
            cb_ticktext = _ax.get('ticktext')

        cmin_conf = var_conf.get('cmin')
        cmax_conf = var_conf.get('cmax')
        cmin = float(cmin_conf) if cmin_conf is not None else float(np.nanmin(_color_work))
        cmax = float(cmax_conf) if cmax_conf is not None else float(np.nanmax(_color_work))

        if color_scale == "Log scale":
            pos_mask = _color_work > 0
            log_c    = np.full_like(_color_work, np.nan, dtype=float)
            log_c[pos_mask] = np.log10(_color_work[pos_mask])
            _color_work = log_c
            real_cmin   = cmin if cmin > 0 else (float(np.nanmin(color_vals[pos_mask]))
                                                  if pos_mask.any() else 1e-3)
            real_cmax   = cmax if cmax > 0 else (float(np.nanmax(color_vals[pos_mask]))
                                                  if pos_mask.any() else 1.0)
            cmin = np.log10(real_cmin)
            cmax = np.log10(real_cmax)
            cmid = None
            mn, mx      = int(np.floor(cmin)), int(np.ceil(cmax))
            cb_tickvals = np.arange(mn, mx + 1, dtype=float) if mx > mn else [cmin, cmax]
            cb_ticktext = [f"1e{int(p)}" if p < -3 or p > 3 else f"{10**p:g}"
                           for p in cb_tickvals]

        x_max_raw    = float(np.nanmax(range_km)) if len(range_km) > 0 else 200.0
        x_max        = sr_max_range if sr_max_range is not None else x_max_raw
        _candidates  = RH_RING_CANDIDATES
        ring_spacing = next((c for c in _candidates if 3 <= x_max / c <= 8), _candidates[-1])
        x_axis_max   = np.ceil(x_max / ring_spacing) * ring_spacing

        has_z_bounds = (domain_bounds and 'z_min' in domain_bounds and
                        domain_bounds.get('z_col') == z_col)
        if is_pres:
            if has_z_bounds:
                y_axis_min = domain_bounds['z_min']
                y_axis_max = domain_bounds['z_max']
            else:
                y_min_raw = float(np.nanmin(z_vals)) if len(z_vals) > 0 else 100.0
                y_max_raw = float(np.nanmax(z_vals)) if len(z_vals) > 0 else 1013.0
                for step in [10, 25, 50, 100]:
                    y_axis_min = np.floor(y_min_raw / step) * step
                    y_axis_max = np.ceil(y_max_raw  / step) * step
                    if (y_axis_max - y_axis_min) / step <= 20:
                        break
            y_range   = [y_axis_max, y_axis_min]
            y_autorev = False
        else:
            if has_z_bounds:
                y_axis_min = domain_bounds['z_min']
                y_axis_max = domain_bounds['z_max']
            else:
                y_max_raw = float(np.nanmax(z_vals)) if len(z_vals) > 0 else 15000.0
                for step in [500, 1000, 2000, 2500, 5000, 10000]:
                    y_axis_max = np.ceil(y_max_raw / step) * step
                    if y_axis_max / step <= 20:
                        break
                y_axis_min = 0
            y_range   = [y_axis_min, y_axis_max]
            y_autorev = False

        sz_mult      = marker_size_pct / 100.0
        display_name = self._get_var_display_name(group_name, variable)
        z_disp_label = 'Pressure' if is_pres else 'Height'
        z_unit_str   = z_units

        t_vals = plot_df[time_col].values
        offset = self.metadata.get('time_offset_seconds', 0.0)
        
        def make_rh_hover(r, z, v, t):
            parts = [f"Range: {r:.1f} km", f"{z_disp_label}: {z:.1f} {z_unit_str}"]
            if not pd.isna(v):
                parts.append(f"{display_name}: {v:,.2f}")
            if not pd.isna(t):
                from datetime import datetime, timezone
                if t > 1.9e13:
                    s = f"{t:.0f}"
                    if len(s) == 14:
                        parts.append(f"Time: {s[8:10]}:{s[10:12]}:{s[12:14]} UTC")
                else:
                    dt = datetime.fromtimestamp(t - offset, timezone.utc)
                    parts.append(f"Time: {dt.strftime('%H:%M:%S')} UTC")
            return "<br>".join(parts)
            
        hover_text = [make_rh_hover(r, z, v, t) for r, z, v, t in zip(range_km, z_vals, color_vals, t_vals)]

        fig = go.Figure()

        is_vector = variable.lower() in ['wind_vec_hz', 'wind_vec_3d']
        
        if is_vector and 'u' in cols_lower and 'v' in cols_lower:
            u_col, v_col = cols_lower['u'], cols_lower['v']
            u_vals, v_vals = plot_df[u_col].values, plot_df[v_col].values
            
            v_radial, _ = self._decompose_radial_tangential(u_vals, v_vals, azimuth_deg)
            w_col = cols_lower.get('w')
            w_vals = plot_df[w_col].values if w_col and w_col in plot_df.columns else np.zeros_like(u_vals)
            
            max_span_x = np.nanmax(range_km) - np.nanmin(range_km)
            max_span_z = np.nanmax(z_vals) - np.nanmin(z_vals)
            if pd.isna(max_span_x) or max_span_x == 0: max_span_x = 1.0
            if pd.isna(max_span_z) or max_span_z == 0: max_span_z = 1.0
            
            z_scale = max_span_z / max_span_x
            
            vector_traces = build_2d_vector_traces(
                x0=range_km, y0=z_vals, u=v_radial, v=w_vals,
                color_vals=_color_work, cmap=cmap, cmin=cmin, cmax=cmax, cmid=cmid,
                cb_tickvals=cb_tickvals, cb_ticktext=cb_ticktext,
                hover_text=hover_text, display_name=display_name,
                vec_scale=vec_scale, y_scale_factor=z_scale, arrow_fraction=0.05
            )
            for trace in vector_traces: fig.add_trace(trace)
            
        else:
            marker_dict = dict(
                size=9 * sz_mult,
                color=_color_work,
                colorscale=cmap,
                cmin=cmin, cmax=cmax, cmid=cmid,
                showscale=True,
                colorbar=dict(
                    len=0.8, thickness=15,
                    tickfont=dict(size=FS_PLOT_TICK),
                    tickvals=cb_tickvals,
                    ticktext=cb_ticktext,
                )
            )

            fig.add_trace(go.Scatter(
                x=range_km, y=z_vals,
                mode='markers',
                marker=marker_dict,
                text=hover_text,
                hoverinfo='text',
                showlegend=False,
            ))

        nice_title = self._format_title(group_name, variable,
                                        "Radial-Height Profile | Storm-Relative")
        _MT = self._title_top_margin(nice_title)

        fig.update_layout(
            title={'text': nice_title, 'x': 0.5, 'xanchor': 'center',
                   'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
            width=800, height=600,
            autosize=False,
            showlegend=False,
            xaxis=dict(
                title='Radius from Storm Center (km)',
                range=[0, x_axis_max],
                dtick=ring_spacing, tick0=0,
                tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                showgrid=True, gridcolor=CLR_PLOT_GRID, zeroline=False,
                showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
            ),
            yaxis=dict(
                title=z_label,
                range=y_range,
                tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
                showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
            ),
            plot_bgcolor=CLR_PLOT_BG,
            paper_bgcolor=CLR_PLOT_BG,
            margin=dict(l=100, r=100, t=_MT, b=60),
        )

        return fig, plot_df