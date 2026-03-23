# -*- coding: utf-8 -*-
"""
ui_analysis.py
--------------
Main layout and rendering logic for the Statistical Analysis tab.
"""

import streamlit as st
import numpy as np
from scipy.stats import gaussian_kde
from ui_layout import apply_viewer_compaction_css
from ui_analysis_controls import render_analysis_controls
from plotter import StormPlotter


def _apply_log_transform(data_pack, sel_group, variable, coord_var,
                          log_var, log_coord_var):
    """
    Inject temporary log10 columns into data_pack['data'][sel_group].
    Returns (plot_var_col, plot_coord_col, restore_fn).
    """
    df = data_pack['data'][sel_group]
    added_cols = []

    def _make_log_col(col):
        log_col = f"_log10_{col}"
        if log_col not in df.columns:
            raw = df[col].values.astype(float)
            with np.errstate(divide='ignore', invalid='ignore'):
                log_vals = np.where(raw > 0, np.log10(raw), np.nan)
            df[log_col] = log_vals
            added_cols.append(log_col)
            orig_attrs = (data_pack.get('var_attrs', {})
                          .get(sel_group, {}).get(col, {}))
            orig_units = orig_attrs.get('units', '')
            orig_long  = orig_attrs.get('long_name', col)
            data_pack.setdefault('var_attrs', {}).setdefault(sel_group, {})[log_col] = {
                'long_name': orig_long or col,
                'units': f"{orig_units}, Log Scale" if orig_units else "Log Scale",
            }
        return log_col

    out_var   = _make_log_col(variable)  if log_var                       else variable
    out_coord = _make_log_col(coord_var) if (log_coord_var and coord_var) else coord_var

    def restore():
        for c in added_cols:
            if c in df.columns:
                df.drop(columns=[c], inplace=True)
            data_pack.get('var_attrs', {}).get(sel_group, {}).pop(c, None)

    return out_var, out_coord, restore


def _render_stats_table(vals, units, log_applied):
    if len(vals) == 0:
        return
    try:
        mode_val = (float(np.mean(vals)) if np.std(vals) < 1e-9
                    else float(np.linspace(vals.min(), vals.max(), 500)
                               [np.argmax(gaussian_kde(vals)(
                                   np.linspace(vals.min(), vals.max(), 500)))]))
    except Exception:
        mode_val = float(np.median(vals))

    import pandas as pd
    df_stats = pd.DataFrame({
        'Count':    [f"{len(vals):,}"],
        'Mean':     [f"{np.mean(vals):.4g}"],
        'Median':   [f"{np.median(vals):.4g}"],
        'Mode':     [f"{mode_val:.4g}"],
        'Std Dev':  [f"{np.std(vals):.4g}"],
    })
    _, col_center, _ = st.columns([1, 8, 1])
    with col_center:
        st.dataframe(df_stats, width="stretch", hide_index=True)


def render_analysis_tab():
    apply_viewer_compaction_css()

    if 'analysis_state' not in st.session_state:
        st.session_state.analysis_state = {}
    for k, v in st.session_state.analysis_state.items():
        if k not in st.session_state:
            st.session_state[k] = v

    intent = render_analysis_controls()

    if not intent.data_pack:
        st.info("👈 Please upload an AI-Ready HDF5 file in the sidebar to begin analysis.")
        return

    data_pack = intent.data_pack

    if intent.sel_group and 'TRACK' in intent.sel_group.upper():
        return

    if not intent.variable:
        return

    plot_var, plot_coord, restore = _apply_log_transform(
        data_pack, intent.sel_group,
        intent.variable, intent.coord_var,
        intent.log_var, intent.log_coord_var,
    )

    plotter = StormPlotter(
        data_pack['data'], data_pack['track'],
        data_pack['meta'], data_pack['var_attrs']
    )

    try:
        if intent.analysis_type == "Histogram Analysis (1D)":
            fig = plotter.plot_histogram(
                intent.sel_group, plot_var,
                nbins=intent.hist_bins_x,
                normalization=intent.normalization,
                reverse_axes=intent.reverse_axes,
                render_as_line=intent.render_as_line,
            )
            if fig:
                _, col_center, _ = st.columns([1, 8, 1])
                with col_center:
                    st.plotly_chart(fig, use_container_width=True)
                df_grp = data_pack['data'].get(intent.sel_group)
                if df_grp is not None and plot_var in df_grp.columns:
                    vals = df_grp[plot_var].dropna().values
                    var_attrs = data_pack.get('var_attrs', {})
                    orig_units = (var_attrs.get(intent.sel_group, {})
                                  .get(intent.variable, {}).get('units', ''))
                    _render_stats_table(vals, orig_units, intent.log_var)
            else:
                st.warning("Could not generate 1D histogram for this variable.")

        elif intent.analysis_type == "Histogram Analysis (2D)":
            if plot_coord:
                fig = plotter.plot_histogram_2d(
                    intent.sel_group, plot_var, plot_coord,
                    nbinsx=intent.hist_bins_x,
                    nbinsy=intent.hist_bins_y,
                    reverse_axes=intent.reverse_axes,
                    normalization=intent.normalization,
                )
                if fig:
                    _, col_center, _ = st.columns([1, 8, 1])
                    with col_center:
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Could not generate 2D histogram for these variables.")
            else:
                st.warning("No coordinate variable available to plot.")

        elif intent.analysis_type == "Scatter Analysis":
            if plot_coord:
                fig = plotter.plot_scatter(
                    intent.sel_group, plot_var, plot_coord,
                    color_var=intent.scatter_color_var,
                    show_trendline=intent.scatter_trendline,
                    reverse_axes=intent.reverse_axes,
                    marker_size_pct=intent.scatter_marker_size,
                )
                if fig:
                    _, col_center, _ = st.columns([1, 8, 1])
                    with col_center:
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Could not generate scatter plot for these variables.")
            else:
                st.warning("Please select a second variable to plot against.")

    finally:
        restore()
