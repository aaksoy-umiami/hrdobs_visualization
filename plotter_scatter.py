# -*- coding: utf-8 -*-
"""
plotter_scatter.py
------------------
Scatter plotting methods and trendline calculations for StormPlotter.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ui_layout import (
    CLR_PRIMARY, CLR_PLOT_BG, CLR_PLOT_GRID,
    FS_PLOT_TICK, TARGET_PLOT_TICKS, PLOT_TITLE_Y,
)
from config import GLOBAL_VAR_CONFIG
from data_utils import decode_metadata

class ScatterMixin:

    def plot_scatter(self, group_name, variable, coord_var, color_var=None,
                     nbinsx=None, nbinsy=None, reverse_axes=False, marker_size_pct=100, 
                     custom_colorscale=None, coordinate_system="Cartesian", active_trendlines=None,
                     selected_indices=None, selection_mode="Include", show_marginals=False, show_kde=False,
                     map_option="None"):
                     
        if group_name not in self.data:
            return None

        df = self.data[group_name].copy()
        if variable not in df.columns or coord_var not in df.columns:
            return None

        plot_df = df.dropna(subset=[variable, coord_var])
        if plot_df.empty:
            return None

        x_vals    = plot_df[variable].values
        y_vals    = plot_df[coord_var].values
        x_var_col = variable
        y_var_col = coord_var

        if reverse_axes:
            x_vals, y_vals        = y_vals, x_vals
            x_var_col, y_var_col  = coord_var, variable

        x_name = self._get_var_display_name(group_name, x_var_col)
        y_name = self._get_var_display_name(group_name, y_var_col)
        _color_suffix = (
            f", Color: {self._get_var_display_name(group_name, color_var)}"
            if color_var and color_var in plot_df.columns
            else ""
        )
        nice_title = self._format_title(group_name, y_var_col,
                                        f"vs. {x_name}{_color_suffix}" + 
                                        (f" | Polar" if coordinate_system == "Polar" else ""))

        xaxis_dict = dict(
            title=x_name,
            tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
            showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
            showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True
        )
        yaxis_dict = dict(
            title=y_name,
            tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
            showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
            showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True
        )
        if (x_var_col.lower() == 'p'
                or 'pres' in x_var_col.lower()
                or x_var_col.lower().endswith('_p')):
            xaxis_dict['autorange'] = 'reversed'
        if (y_var_col.lower() == 'p'
                or 'pres' in y_var_col.lower()
                or y_var_col.lower().endswith('_p')):
            yaxis_dict['autorange'] = 'reversed'
            
        if map_option == "Show Map" and coordinate_system == "Cartesian":
            yaxis_dict['scaleanchor'] = 'x'
            yaxis_dict['scaleratio'] = 1

        # Apply time axis conversions
        x_vals = self._apply_time_axis(x_var_col, x_vals, xaxis_dict)
        y_vals = self._apply_time_axis(y_var_col, y_vals, yaxis_dict, is_x=False)

        fig = go.Figure()
        stats_list = []
        
        # In Scatter mode, everything is always centered at 0.5
        title_x = 0.5
        
        fit_colors = {
            "Linear": "#000000",               # Black
            "Quadratic (2nd Deg)": "#e31a1c",  # Red
            "Cubic (3rd Deg)": "#1f78b4",      # Blue
            "Logarithmic": "#33a02c",          # Green
            "Exponential": "#ff7f00"           # Orange
        }

        sz = max(1, int(5 * marker_size_pct / 100))
        
        color_vals = np.full(len(plot_df), np.nan)
        if color_var and color_var in plot_df.columns:
            color_vals = plot_df[color_var].values
            var_conf   = GLOBAL_VAR_CONFIG.get(color_var.lower(), {})
            cmap       = custom_colorscale if custom_colorscale else var_conf.get('colorscale', 'Viridis')
            cmid       = var_conf.get('cmid', None)
            
            # Colorbar matches the main plot height
            cb_dict = dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK))
                
            marker_dict = dict(
                size=sz,
                color=color_vals,
                colorscale=cmap,
                cmid=cmid,
                showscale=True,
                colorbar=cb_dict
            )
        else:
            marker_dict = dict(size=sz, color='#B6BABD')

        # --- HOVER DATA EXTRACTION ---
        cols_lower = {c.lower(): c for c in df.columns}
        t_col = cols_lower.get('time')
        t_vals = plot_df[t_col].values if t_col else np.full(len(plot_df), np.nan)

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

        def make_scatter_hover(x, y, t, z, c_val):
            parts = [f"{x_name}: {x:,.2f}", f"{y_name}: {y:,.2f}"]
            if color_var:
                parts.append(f"{color_var}: {c_val:,.2f}" if not pd.isna(c_val) else f"{color_var}: NaN")
            if not pd.isna(t):
                s = f"{t:.0f}"
                if len(s) == 14:
                    parts.append(f"Time: {s[8:10]}:{s[10:12]}:{s[12:14]} UTC")
            if not pd.isna(z):
                parts.append(f"{z_name_hover}: {z:,.1f} {z_unit_hover}".strip())
            return "<br>".join(parts)
            
        text_arr = [make_scatter_hover(x, y, t, z, c) for x, y, t, z, c in zip(x_vals, y_vals, t_vals, z_vals_hover, color_vals)]

        trace_kwargs = dict(
            mode='markers',
            marker=marker_dict,
            text=text_arr,
            hoverinfo='text',
            name="Data",
            showlegend=False
        )

        active_indices = None
        if selected_indices is not None and len(selected_indices) > 0:
            safe_indices = set(i for i in selected_indices if i < len(x_vals))
            
            if selection_mode == "Exclude":
                active_indices = [i for i in range(len(x_vals)) if i not in safe_indices]
            else:
                active_indices = list(safe_indices)
                
            trace_kwargs['selectedpoints'] = active_indices
            trace_kwargs['unselected'] = dict(marker=dict(opacity=0.15))

        if coordinate_system == "Polar":
            if 'azimuth' in x_var_col.lower():
                theta_vals, r_vals = x_vals, y_vals
                r_name = y_name
            else:
                r_vals, theta_vals = x_vals, y_vals
                r_name = x_name
                
            fig.add_trace(go.Scatterpolar(
                r=r_vals, theta=theta_vals,
                **trace_kwargs
            ))
            
            fig.update_layout(
                polar=dict(
                    radialaxis=dict(title=r_name, tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY)),
                    angularaxis=dict(direction='clockwise', rotation=90, tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY))
                )
            )
        else:
            # Use full domain for Scatter
            xaxis_dict['domain'] = [0.0, 1.0]
            yaxis_dict['domain'] = [0.0, 1.0]

            fig.add_trace(go.Scatter(
                x=x_vals, y=y_vals,
                **trace_kwargs
            ))
            
            if map_option == "Show Map" and coordinate_system == "Cartesian":
                is_x_lon = x_var_col.lower() in ['lon', 'longitude', 'clon']
                is_y_lat = y_var_col.lower() in ['lat', 'latitude', 'clat']
                is_x_lat = x_var_col.lower() in ['lat', 'latitude', 'clat']
                is_y_lon = y_var_col.lower() in ['lon', 'longitude', 'clon']
                
                if (is_x_lon and is_y_lat) or (is_x_lat and is_y_lon):
                    valid_mask = np.isfinite(x_vals) & np.isfinite(y_vals)
                    if valid_mask.sum() > 0:
                        x_valid = x_vals[valid_mask]
                        y_valid = y_vals[valid_mask]
                        x_min, x_max = np.min(x_valid), np.max(x_valid)
                        y_min, y_max = np.min(y_valid), np.max(y_valid)
                        
                        lat_min, lat_max = (y_min, y_max) if is_y_lat else (x_min, x_max)
                        lon_min, lon_max = (x_min, x_max) if is_x_lon else (y_min, y_max)
                        domain_bounds = {'lat_min': lat_min, 'lat_max': lat_max, 'lon_min': lon_min, 'lon_max': lon_max}
                        
                        from basemap import get_basemap_traces
                        traces = get_basemap_traces(domain_bounds)
                        for t in traces:
                            if not is_x_lon:
                                t.x, t.y = t.y, t.x
                            fig.add_trace(t)
                            fig.data = (fig.data[-1],) + fig.data[:-1]

                        # Enforce data limits so Plotly doesn't zoom out to the basemap
                        x_pad = max((x_max - x_min) * 0.05, 0.05)
                        y_pad = max((y_max - y_min) * 0.05, 0.05)
                        fig.update_layout(
                            xaxis_range=[x_min - x_pad, x_max + x_pad],
                            yaxis_range=[y_min - y_pad, y_max + y_pad]
                        )

            if active_indices is not None:
                mask = np.zeros(len(x_vals), dtype=bool)
                mask[active_indices] = True
                valid = np.isfinite(x_vals) & np.isfinite(y_vals) & mask
            else:
                valid = np.isfinite(x_vals) & np.isfinite(y_vals)

            # Mathematical Fits Calculation
            if valid.sum() >= 4:
                x_fit = x_vals[valid]
                y_fit = y_vals[valid]
                x_line = np.linspace(x_fit.min(), x_fit.max(), 150)
                
                def get_metrics(yt, yp):
                    ss_res = np.sum((yt - yp)**2)
                    ss_tot = np.sum((yt - np.mean(yt))**2)
                    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                    r = np.corrcoef(yt, yp)[0, 1] if (np.std(yt) > 0 and np.std(yp) > 0) else 0
                    return r, r2

                try:
                    m, b = np.polyfit(x_fit, y_fit, 1)
                    yp = m * x_fit + b
                    yl = m * x_line + b
                    r, r2 = get_metrics(y_fit, yp)
                    eq = f"y = {m:.4g}x {'+' if b >= 0 else '-'} {abs(b):.4g}"
                    stats_list.append({"Fit Name": "Linear", "Equation": eq, "R": f"{r:.4f}", "R²": f"{r2:.4f}", "_x": x_line, "_y": yl})
                except Exception: pass

                try:
                    a, b, c = np.polyfit(x_fit, y_fit, 2)
                    yp = a * x_fit**2 + b * x_fit + c
                    yl = a * x_line**2 + b * x_line + c
                    r, r2 = get_metrics(y_fit, yp)
                    eq = f"y = {a:.4g}x² {'+' if b >= 0 else '-'} {abs(b):.4g}x {'+' if c >= 0 else '-'} {abs(c):.4g}"
                    stats_list.append({"Fit Name": "Quadratic (2nd Deg)", "Equation": eq, "R": f"{r:.4f}", "R²": f"{r2:.4f}", "_x": x_line, "_y": yl})
                except Exception: pass
                
                try:
                    a, b, c, d = np.polyfit(x_fit, y_fit, 3)
                    yp = a * x_fit**3 + b * x_fit**2 + c * x_fit + d
                    yl = a * x_line**3 + b * x_line**2 + c * x_line + d
                    r, r2 = get_metrics(y_fit, yp)
                    eq = f"y = {a:.4g}x³ {'+' if b >= 0 else '-'} {abs(b):.4g}x² {'+' if c >= 0 else '-'} {abs(c):.4g}x {'+' if d >= 0 else '-'} {abs(d):.4g}"
                    stats_list.append({"Fit Name": "Cubic (3rd Deg)", "Equation": eq, "R": f"{r:.4f}", "R²": f"{r2:.4f}", "_x": x_line, "_y": yl})
                except Exception: pass
                
                try:
                    mask_fit = x_fit > 0
                    if mask_fit.sum() >= 3:
                        m, b = np.polyfit(np.log(x_fit[mask_fit]), y_fit[mask_fit], 1)
                        yp = m * np.log(x_fit[mask_fit]) + b
                        yl = m * np.log(x_line[x_line > 0]) + b
                        r, r2 = get_metrics(y_fit[mask_fit], yp)
                        eq = f"y = {m:.4g} ln(x) {'+' if b >= 0 else '-'} {abs(b):.4g}"
                        stats_list.append({"Fit Name": "Logarithmic", "Equation": eq, "R": f"{r:.4f}", "R²": f"{r2:.4f}", "_x": x_line[x_line > 0], "_y": yl})
                except Exception: pass
                
                try:
                    mask_fit = y_fit > 0
                    if mask_fit.sum() >= 3:
                        m, b = np.polyfit(x_fit[mask_fit], np.log(y_fit[mask_fit]), 1)
                        A = np.exp(b)
                        yp = A * np.exp(m * x_fit[mask_fit])
                        yl = A * np.exp(m * x_line)
                        r, r2 = get_metrics(y_fit[mask_fit], yp)
                        eq = f"y = {A:.4g} e^({m:.4g}x)"
                        stats_list.append({"Fit Name": "Exponential", "Equation": eq, "R": f"{r:.4f}", "R²": f"{r2:.4f}", "_x": x_line, "_y": yl})
                except Exception: pass

            active_list = active_trendlines if active_trendlines else []
            has_lines = False
            
            for stat in stats_list:
                if stat["Fit Name"] in active_list:
                    has_lines = True
                    fig.add_trace(go.Scatter(
                        x=stat["_x"], y=stat["_y"], mode='lines',
                        line=dict(color=fit_colors.get(stat["Fit Name"], "black"), width=3, dash='dash'),
                        name=stat["Fit Name"], showlegend=True
                    ))
                del stat["_x"]
                del stat["_y"]

            fig.update_layout(
                xaxis=xaxis_dict, yaxis=yaxis_dict,
                showlegend=has_lines,
                legend=dict(
                    orientation="h",
                    yanchor="top", y=-0.2,
                    xanchor="center", x=0.5,
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="#D3D3D3",
                    borderwidth=1
                )
            )

        # Standard margins for scatter mode
        plot_margin_r = 40
        plot_margin_t = self._title_top_margin(nice_title) - 20

        fig.update_layout(
            title={'text': nice_title, 'x': title_x, 'xanchor': 'center',
                   'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
            width=800, height=600 if coordinate_system == "Cartesian" else 750,
            plot_bgcolor=CLR_PLOT_BG,
            paper_bgcolor=CLR_PLOT_BG,
            margin=dict(l=60, r=plot_margin_r, t=plot_margin_t, b=80),
        )
        return fig, stats_list
    