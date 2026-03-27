# -*- coding: utf-8 -*-
"""
plotter_histogram.py
--------------------
Histogram plotting methods for StormPlotter (1D and 2D).
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import gaussian_kde

from ui_layout import (
    CLR_PRIMARY, CLR_PLOT_BG, CLR_PLOT_GRID,
    CLR_EXTRA, FS_PLOT_TICK, TARGET_PLOT_TICKS, PLOT_TITLE_Y,
)
from config import GLOBAL_VAR_CONFIG, DEFAULT_HIST_BINS

class HistogramMixin:

    def plot_histogram(self, group_name, variable, nbins=None,
                       normalization="None", reverse_axes=False,
                       render_as_line=False, show_kde=False):
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

        is_pct      = (normalization in ["Normalize Fully", "Full Normalization (all bins sum to 100%)"])
        count_label = 'Percentage (%)' if is_pct else 'Count'

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
        
        display_counts = (counts / counts.sum() * 100 if is_pct else counts.astype(float))

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
                
        if show_kde and len(finite) > 1:
            try:
                kde = gaussian_kde(finite)
                x_grid = np.linspace(finite.min(), finite.max(), 300)
                kde_pdf = kde(x_grid)
                
                bin_width = widths[0] if len(widths) > 0 else 1.0
                if is_pct:
                    scaled_kde = kde_pdf * 100.0 * bin_width
                else:
                    scaled_kde = kde_pdf * len(finite) * bin_width

                if reverse_axes:
                    fig.add_trace(go.Scatter(
                        x=scaled_kde, y=x_grid, mode='lines',
                        line=dict(color='#808080', width=2.5, dash='dash'),
                        name='KDE', showlegend=False
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=x_grid, y=scaled_kde, mode='lines',
                        line=dict(color='#808080', width=2.5, dash='dash'),
                        name='KDE', showlegend=False
                    ))
            except Exception:
                pass 

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
            return np.zeros((ny, nx)), np.zeros(nx), np.zeros(ny), np.zeros(nx+1), np.zeros(ny+1)

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

        return H, x_centers, y_centers, xedges, yedges

    def plot_histogram_2d(self, group_name, variable, coord_var,
                          nbinsx=None, nbinsy=None, reverse_axes=False,
                          normalization="None", custom_colorscale=None,
                          coordinate_system="Cartesian", show_kde=False,
                          show_marginals=False):
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
                                        f"Binned by {secondary_name}" + 
                                        (f" | Polar" if coordinate_system == "Polar" else ""))

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
            
        H, x_centers, y_centers, x_edges, y_edges = self._compute_2d_normalization(
            x_vals, y_vals, nbinsx, nbinsy, _norm)

        fig = go.Figure()
        title_x = 0.5

        if coordinate_system == "Polar":
            r_base, r_len, t_val, t_width, c_val = [], [], [], [], []
            is_x_az = 'azimuth' in x_var_col.lower()
            
            if is_x_az:
                for i, t in enumerate(x_centers):
                    for j, r in enumerate(y_centers):
                        if H[j, i] > 0:
                            r_base.append(y_edges[j])
                            r_len.append(y_edges[j+1] - y_edges[j])
                            t_val.append(t)
                            t_width.append(x_edges[i+1] - x_edges[i])
                            c_val.append(H[j, i])
            else:
                for i, r in enumerate(x_centers):
                    for j, t in enumerate(y_centers):
                        if H[j, i] > 0:
                            r_base.append(x_edges[i])
                            r_len.append(x_edges[i+1] - x_edges[i])
                            t_val.append(t)
                            t_width.append(y_edges[j+1] - y_edges[j])
                            c_val.append(H[j, i])

            fig.add_trace(go.Barpolar(
                base=r_base, r=r_len, theta=t_val, width=t_width,
                marker=dict(
                    color=c_val, colorscale=custom_cmap,
                    showscale=True, colorbar=dict(title=cb_title, len=0.8, thickness=15)
                ),
                name=nice_title
            ))
            
            fig.update_layout(
                polar=dict(
                    angularaxis=dict(direction='clockwise', rotation=90, tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY)),
                    radialaxis=dict(title=y_name if is_x_az else x_name, tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY))
                )
            )
            
        else:
            cb_dict = dict(title=cb_title, len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK))
            if show_marginals:
                title_x = 0.375 
                cb_dict['x'] = 1.05 
                cb_dict['y'] = 0.375 
                cb_dict['len'] = 0.75
                
                xaxis_dict['domain'] = [0.0, 0.75]
                yaxis_dict['domain'] = [0.0, 0.75]
                xaxis_dict['anchor'] = 'y'
                yaxis_dict['anchor'] = 'x'
                
                fig.update_layout(
                    xaxis2=dict(
                        domain=[0.7795, 1.0], anchor='y3', showticklabels=True, zeroline=False,
                        showgrid=True, gridcolor=CLR_PLOT_GRID, 
                        showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                        tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY)
                    ),
                    yaxis3=dict(
                        domain=[0.0, 0.75], matches='y', anchor='x2', showticklabels=False, zeroline=False,
                        showgrid=True, gridcolor=CLR_PLOT_GRID, 
                        showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True
                    ),
                    xaxis3=dict(
                        domain=[0.0, 0.75], matches='x', anchor='y2', showticklabels=False, zeroline=False,
                        showgrid=True, gridcolor=CLR_PLOT_GRID, 
                        showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True
                    ),
                    yaxis2=dict(
                        domain=[0.795, 1.0], anchor='x3', showticklabels=True, zeroline=False,
                        showgrid=True, gridcolor=CLR_PLOT_GRID, 
                        showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                        tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY)
                    )
                )

            fig.add_trace(go.Heatmap(
                z=H, x=x_centers, y=y_centers,
                colorscale=custom_cmap,
                zmin=0,
                colorbar=cb_dict
            ))
            fig.update_layout(xaxis=xaxis_dict, yaxis=yaxis_dict)

            if show_kde:
                try:
                    valid = np.isfinite(x_vals) & np.isfinite(y_vals)
                    if valid.sum() > 2:
                        data = np.vstack([x_vals[valid], y_vals[valid]])
                        kde = gaussian_kde(data)
                        
                        x_grid = np.linspace(x_vals[valid].min(), x_vals[valid].max(), 100)
                        y_grid = np.linspace(y_vals[valid].min(), y_vals[valid].max(), 100)
                        X, Y = np.meshgrid(x_grid, y_grid)
                        positions = np.vstack([X.ravel(), Y.ravel()])
                        Z = np.reshape(kde(positions).T, X.shape)
                        
                        if _norm == "Normalize within each X bin":
                            col_sums = Z.sum(axis=0, keepdims=True)
                            Z = np.divide(Z, col_sums, out=np.zeros_like(Z), where=col_sums != 0)
                        elif _norm == "Normalize within each Y bin":
                            row_sums = Z.sum(axis=1, keepdims=True)
                            Z = np.divide(Z, row_sums, out=np.zeros_like(Z), where=row_sums != 0)
                        
                        fig.add_trace(go.Contour(
                            z=Z, x=x_grid, y=y_grid,
                            contours=dict(coloring='lines', showlabels=False),
                            line=dict(width=2.5), 
                            colorscale='Greys',
                            reversescale=True,
                            showscale=False,
                            name='2D KDE',
                            hoverinfo='skip'
                        ))
                except Exception:
                    pass

            if show_marginals:
                counts_x = H.sum(axis=0)
                counts_y = H.sum(axis=1)
                
                fig.add_trace(go.Bar(
                    x=x_centers, y=counts_x, xaxis='x3', yaxis='y2', 
                    marker_color=CLR_EXTRA, opacity=0.6, showlegend=False
                ))
                
                fig.add_trace(go.Bar(
                    y=y_centers, x=counts_y, xaxis='x2', yaxis='y3', orientation='h', 
                    marker_color=CLR_EXTRA, opacity=0.6, showlegend=False
                ))
                
                if show_kde:
                    valid = np.isfinite(x_vals) & np.isfinite(y_vals)
                    marg_x = x_vals[valid]
                    marg_y = y_vals[valid]

                    if len(marg_x) > 1 and np.var(marg_x) > 0:
                        x_g = np.linspace(marg_x.min(), marg_x.max(), 100)
                        if _norm == "Normalize within each X bin":
                            s_kde_x = np.full_like(x_g, 100.0)
                        else:
                            kde_x = gaussian_kde(marg_x)
                            area_x = counts_x.sum() * (x_edges[1] - x_edges[0])
                            s_kde_x = kde_x(x_g) * area_x
                            
                        fig.add_trace(go.Scatter(
                            x=x_g, y=s_kde_x, xaxis='x3', yaxis='y2', mode='lines', 
                            line=dict(color='#808080', width=2, dash='dash'), showlegend=False
                        ))
                        
                    if len(marg_y) > 1 and np.var(marg_y) > 0:
                        y_g = np.linspace(marg_y.min(), marg_y.max(), 100)
                        if _norm == "Normalize within each Y bin":
                            s_kde_y = np.full_like(y_g, 100.0)
                        else:
                            kde_y = gaussian_kde(marg_y)
                            area_y = counts_y.sum() * (y_edges[1] - y_edges[0])
                            s_kde_y = kde_y(y_g) * area_y
                            
                        fig.add_trace(go.Scatter(
                            y=y_g, x=s_kde_y, xaxis='x2', yaxis='y3', mode='lines', 
                            line=dict(color='#808080', width=2, dash='dash'), showlegend=False
                        ))

        plot_margin_r = 120 if (coordinate_system == "Cartesian" and show_marginals) else 40
        plot_margin_t = self._title_top_margin(nice_title) - 20

        fig.update_layout(
            title={'text': nice_title, 'x': title_x, 'xanchor': 'center',
                   'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
            width=800, height=600 if coordinate_system == "Cartesian" else 750,
            showlegend=False,
            plot_bgcolor=CLR_PLOT_BG,
            paper_bgcolor=CLR_PLOT_BG,
            margin=dict(l=60, r=plot_margin_r, t=plot_margin_t, b=60),
        )
        return fig
    