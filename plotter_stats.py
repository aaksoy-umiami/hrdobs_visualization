# -*- coding: utf-8 -*-
"""
plotter_stats.py
----------------
Statistical plotting methods for StormPlotter.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from config import GLOBAL_VAR_CONFIG, DEFAULT_HIST_BINS
from ui_layout import (
    CLR_PRIMARY, CLR_PLOT_BG, CLR_PLOT_GRID,
    CLR_EXTRA, FS_PLOT_TICK, TARGET_PLOT_TICKS, PLOT_TITLE_Y,
)
from plotter_spatial import StormPlotterSpatial

class StormPlotterStats(StormPlotterSpatial):

    def plot_histogram(self, group_name, variable, nbins=None,
                       normalization="None", reverse_axes=False,
                       render_as_line=False):
        if group_name not in self.data:
            return None

        df = self.data[group_name].copy()
        if variable not in df.columns:
            return None

        plot_df = df.dropna(subset=[variable])
        if plot_df.empty:
            return None

        vals         = plot_df[variable].values
        display_name = self._get_var_display_name(group_name, variable)
        nice_title   = self._format_title(group_name, variable, "")

        histnorm    = ('percent'
                       if normalization == "Full Normalization (all bins sum to 100%)"
                       else None)
        count_label = ('Percentage (%)'
                       if normalization == "Full Normalization (all bins sum to 100%)"
                       else 'Count')

        def _make_var_axis(is_x):
            d = dict(
                title=display_name,
                tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
                showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True
            )
            if (variable.lower() == 'p'
                    or 'pres' in variable.lower()
                    or variable.lower().endswith('_p')):
                d['autorange'] = 'reversed'
            return d

        def _make_count_axis():
            return dict(
                title=count_label,
                tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
                showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True
            )

        fig = go.Figure()

        if reverse_axes:
            var_axis   = _make_var_axis(is_x=False)
            plot_vals  = self._apply_time_axis(variable, vals, var_axis, is_x=False)
            count_axis = _make_count_axis()
            x_axis, y_axis = count_axis, var_axis
        else:
            var_axis   = _make_var_axis(is_x=True)
            plot_vals  = self._apply_time_axis(variable, vals, var_axis, is_x=True)
            count_axis = _make_count_axis()
            x_axis, y_axis = var_axis, count_axis

        n_bins  = nbins if nbins else DEFAULT_HIST_BINS
        finite  = plot_vals[np.isfinite(plot_vals)]
        counts, edges = np.histogram(finite, bins=n_bins)
        centers        = (edges[:-1] + edges[1:]) / 2
        widths         = edges[1:] - edges[:-1]
        display_counts = (counts / counts.sum() * 100
                          if normalization == "Full Normalization (all bins sum to 100%)"
                          else counts.astype(float))

        if render_as_line:
            if reverse_axes:
                fig.add_trace(go.Scatter(
                    x=display_counts, y=centers, mode='lines',
                    line=dict(color=CLR_EXTRA, width=2),
                    name=display_name, showlegend=False
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=centers, y=display_counts, mode='lines',
                    line=dict(color=CLR_EXTRA, width=2),
                    name=display_name, showlegend=False
                ))
        else:
            if reverse_axes:
                fig.add_trace(go.Bar(
                    x=display_counts, y=centers, orientation='h',
                    width=widths, marker_color=CLR_EXTRA, opacity=0.85,
                    name=display_name, showlegend=False
                ))
            else:
                fig.add_trace(go.Bar(
                    x=centers, y=display_counts, orientation='v',
                    width=widths, marker_color=CLR_EXTRA, opacity=0.85,
                    name=display_name, showlegend=False
                ))

        fig.update_layout(xaxis=x_axis, yaxis=y_axis, bargap=0)

        fig.update_layout(
            title={'text': nice_title, 'x': 0.5, 'xanchor': 'center',
                   'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
            width=800, height=600,
            showlegend=False,
            plot_bgcolor=CLR_PLOT_BG,
            paper_bgcolor=CLR_PLOT_BG,
            margin=dict(l=60, r=40, t=self._title_top_margin(nice_title), b=60),
        )
        return fig

    def _compute_2d_normalization(self, x_vals, y_vals, nbinsx, nbinsy, normalization):
        nx = nbinsx if nbinsx is not None else DEFAULT_HIST_BINS
        ny = nbinsy if nbinsy is not None else DEFAULT_HIST_BINS

        x_vals = np.asarray(x_vals, dtype=float)
        y_vals = np.asarray(y_vals, dtype=float)
        finite_mask = np.isfinite(x_vals) & np.isfinite(y_vals)
        x_vals = x_vals[finite_mask]
        y_vals = y_vals[finite_mask]

        if len(x_vals) == 0:
            return np.zeros((ny, nx)), np.zeros(nx), np.zeros(ny)

        H, xedges, yedges = np.histogram2d(x_vals, y_vals, bins=[nx, ny])
        H = H.T

        if normalization == "Normalize Fully":
            total = H.sum()
            if total > 0:
                H = (H / total) * 100.0
        elif normalization == "Normalize within each Y bin":
            row_sums = H.sum(axis=1, keepdims=True)
            H = np.divide(H, row_sums, out=np.zeros_like(H), where=row_sums != 0) * 100.0
        elif normalization == "Normalize within each X bin":
            col_sums = H.sum(axis=0, keepdims=True)
            H = np.divide(H, col_sums, out=np.zeros_like(H), where=col_sums != 0) * 100.0

        x_centers = (xedges[:-1] + xedges[1:]) / 2
        y_centers = (yedges[:-1] + yedges[1:]) / 2

        return H, x_centers, y_centers

    def plot_histogram_2d(self, group_name, variable, coord_var,
                          nbinsx=None, nbinsy=None, reverse_axes=False,
                          normalization="None", custom_colorscale=None):
        if group_name not in self.data:
            return None

        df = self.data[group_name].copy()
        if variable not in df.columns or coord_var not in df.columns:
            return None

        plot_df = df.dropna(subset=[variable, coord_var])
        if plot_df.empty:
            return None

        primary_name   = self._get_var_display_name(group_name, variable)
        secondary_name = self._get_var_display_name(group_name, coord_var)
        if reverse_axes:
            x_vals, y_vals  = plot_df[variable].values, plot_df[coord_var].values
            x_name          = f"{primary_name} (Primary)"
            y_name          = f"{secondary_name} (Secondary)"
            x_var_col, y_var_col = variable, coord_var
        else:
            x_vals, y_vals  = plot_df[coord_var].values, plot_df[variable].values
            x_name          = f"{secondary_name} (Secondary)"
            y_name          = f"{primary_name} (Primary)"
            x_var_col, y_var_col = coord_var, variable

        nice_title = self._format_title(group_name, variable,
                                        f"Binned by {secondary_name}")

        _var_key  = variable[len('_log10_'):] if variable.startswith('_log10_') else variable
        var_conf  = GLOBAL_VAR_CONFIG.get(_var_key.lower(), {})
        cmap_name = custom_colorscale if custom_colorscale else var_conf.get('colorscale', 'Viridis')

        try:
            import plotly.colors
            base_cmap  = plotly.colors.get_colorscale(cmap_name)
            custom_cmap = []
            for val, clr in base_cmap:
                if float(val) == 0.0:
                    custom_cmap.append([0.0, 'rgba(0,0,0,0)'])
                else:
                    custom_cmap.append([float(val), clr])
        except Exception:
            custom_cmap = cmap_name

        cb_title = ('Percentage (%)'
                    if normalization not in ("None", None)
                    else 'Count')

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

        x_vals = self._apply_time_axis(x_var_col, x_vals, xaxis_dict)
        y_vals = self._apply_time_axis(y_var_col, y_vals, yaxis_dict, is_x=False)

        _norm = normalization
        if normalization == "Normalize within each Primary bin":
            _norm = "Normalize within each X bin" if reverse_axes else "Normalize within each Y bin"
        elif normalization == "Normalize within each Secondary bin":
            _norm = "Normalize within each Y bin" if reverse_axes else "Normalize within each X bin"
        H, x_centers, y_centers = self._compute_2d_normalization(
            x_vals, y_vals, nbinsx, nbinsy, _norm)

        fig = go.Figure()
        fig.add_trace(go.Heatmap(
            z=H, x=x_centers, y=y_centers,
            colorscale=custom_cmap,
            zmin=0,
            colorbar=dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK))
        ))

        fig.update_layout(
            title={'text': nice_title, 'x': 0.5, 'xanchor': 'center',
                   'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
            width=800, height=600,
            showlegend=False,
            xaxis=xaxis_dict,
            yaxis=yaxis_dict,
            plot_bgcolor=CLR_PLOT_BG,
            paper_bgcolor=CLR_PLOT_BG,
            margin=dict(l=60, r=40, t=self._title_top_margin(nice_title), b=60),
        )
        return fig

    def plot_scatter(self, group_name, variable, coord_var, color_var=None,
                     show_trendline=False, reverse_axes=False,
                     marker_size_pct=100, custom_colorscale=None):
                     
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
                                        f"vs. {x_name}{_color_suffix}")

        if color_var and color_var in plot_df.columns:
            color_vals = plot_df[color_var].values
            var_conf   = GLOBAL_VAR_CONFIG.get(color_var.lower(), {})
            cmap       = custom_colorscale if custom_colorscale else var_conf.get('colorscale', 'Viridis')
            cmid       = var_conf.get('cmid', None)
        else:
            H, xedges, yedges = np.histogram2d(x_vals, y_vals, bins=50)
            xi         = np.clip(np.searchsorted(xedges, x_vals) - 1, 0, H.shape[0] - 1)
            yi         = np.clip(np.searchsorted(yedges, y_vals) - 1, 0, H.shape[1] - 1)
            color_vals = H[xi, yi]
            cmap       = custom_colorscale if custom_colorscale else "Viridis"
            cmid       = None

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

        x_vals = self._apply_time_axis(x_var_col, x_vals, xaxis_dict)
        y_vals = self._apply_time_axis(y_var_col, y_vals, yaxis_dict, is_x=False)

        fig = go.Figure()

        sz = max(1, int(5 * marker_size_pct / 100))
        if color_var and color_var in plot_df.columns:
            marker_dict = dict(
                size=sz,
                color=color_vals,
                colorscale=cmap,
                cmid=cmid,
                showscale=True,
                colorbar=dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK))
            )
        else:
            marker_dict = dict(size=sz, color=CLR_PRIMARY)

        fig.add_trace(go.Scatter(
            x=x_vals, y=y_vals,
            mode='markers',
            marker=marker_dict,
            name=x_name,
            showlegend=False
        ))

        if show_trendline:
            valid = np.isfinite(x_vals) & np.isfinite(y_vals)
            if valid.sum() >= 2:
                m, b    = np.polyfit(x_vals[valid], y_vals[valid], 1)
                x_line  = np.array([x_vals[valid].min(), x_vals[valid].max()])
                y_line  = m * x_line + b
                fig.add_trace(go.Scatter(
                    x=x_line, y=y_line, mode='lines',
                    line=dict(color=CLR_PRIMARY, width=2, dash='dash'),
                    name='Trendline', showlegend=False
                ))

        fig.update_layout(
            title={'text': nice_title, 'x': 0.5, 'xanchor': 'center',
                   'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
            width=800, height=600,
            showlegend=False,
            xaxis=xaxis_dict,
            yaxis=yaxis_dict,
            plot_bgcolor=CLR_PLOT_BG,
            paper_bgcolor=CLR_PLOT_BG,
            margin=dict(l=60, r=40, t=self._title_top_margin(nice_title), b=60),
        )
        return fig
    