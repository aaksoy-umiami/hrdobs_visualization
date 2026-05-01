# -*- coding: utf-8 -*-
"""
Purpose:
    Serves as the entry point for the Statistical Analysis tab, processing user configurations into data distributions, KDEs, and scatter plots.

Functions/Classes:
    - _apply_log_transform: Temporarily modifies data columns to a base-10 logarithmic scale for visualization.
    - _render_stats_table: Generates a table of summary statistics (count, mean, median, mode, std dev) for 1D distributions.
    - render_analysis_tab: Coordinates the analysis UI state, delegates to the plotter, and displays the resulting charts and statistics.
"""

import streamlit as st
import numpy as np
from scipy.stats import gaussian_kde
from ui_layout import apply_viewer_compaction_css
from ui_analysis_controls import render_analysis_controls
from plotter import StormPlotter
from ui_components import spacer


def _apply_log_transform(data_pack, sel_group, variable, coord_var,
                          log_var, log_coord_var):
    """
    Temporarily modifies data columns to a base-10 logarithmic scale for visualization.
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
    """
    Generates a table of summary statistics for 1D distributions.
    """
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
    """
    Coordinates the analysis UI state, delegates to the plotter, and displays the resulting charts and statistics.
    """
    apply_viewer_compaction_css()

    if 'analysis_state' not in st.session_state:
        st.session_state.analysis_state = {}
    for k, v in st.session_state.analysis_state.items():
        if k not in st.session_state:
            st.session_state[k] = v

    intent = render_analysis_controls()

    if not intent.data_pack:
        spacer('lg')
        spacer('lg')
        st.info("👈 **Ready to explore?**\nPlease upload an AI-Ready HDF5 file to the sidebar to begin.")
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

    helper_text = (
        "<div style='text-align: center; margin-bottom: 20px; color: #666; font-size: 0.95em;'>"
        "💡 <i><b>Tip:</b> Please hover over the plot with your mouse to reveal further controls in the top right corner, including zooming, panning, and downloading.</i>"
        "</div>"
    )

    try:
        if intent.analysis_type == "Histogram Analysis (1D)":
            fig = plotter.plot_histogram(
                intent.sel_group, plot_var,
                nbins=intent.hist_bins_x,
                normalization=intent.normalization,
                reverse_axes=intent.reverse_axes,
                render_as_line=intent.render_as_line,
                show_kde=intent.show_kde
            )
            if fig:
                st.markdown(helper_text, unsafe_allow_html=True)
                _, col_center, _ = st.columns([1, 8, 1])
                with col_center:
                    st.plotly_chart(fig, width="stretch")
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
                    custom_colorscale=intent.custom_colorscale,
                    coordinate_system=intent.coordinate_system,
                    show_kde=intent.show_kde,
                    show_marginals=intent.show_marginals,
                    map_option=intent.map_option
                )
                if fig:
                    st.markdown(helper_text, unsafe_allow_html=True)
                    _, col_center, _ = st.columns([1, 8, 1])
                    with col_center:
                        st.plotly_chart(fig, width="stretch")
                        if intent.coordinate_system == "Polar" and intent.show_kde:
                            st.caption("ℹ️ Density contours (KDE) are currently only overlaid in Cartesian coordinates.")
                        if intent.coordinate_system == "Polar" and intent.show_marginals:
                            st.caption("ℹ️ Marginal distributions are currently only available in Cartesian coordinates.")
                else:
                    st.warning("Could not generate 2D histogram for these variables.")
            else:
                st.warning("No coordinate variable available to plot.")

        elif intent.analysis_type == "Scatter Analysis":
            if plot_coord:
                if 'active_trendlines' not in st.session_state:
                    st.session_state.active_trendlines = []
                
                current_selection = None
                if "scatter_plot_interactive" in st.session_state:
                    sel_event = st.session_state["scatter_plot_interactive"]
                    if sel_event and "selection" in sel_event and sel_event["selection"].get("points"):
                        current_selection = [
                            p["point_index"] for p in sel_event["selection"]["points"]
                            if p.get("curve_number", 0) == 0
                        ]
                        if not current_selection:
                            current_selection = None

                selection_mode = st.session_state.get('scatter_sel_mode', 'Include')

                ret = plotter.plot_scatter(
                    intent.sel_group, plot_var, plot_coord,
                    nbinsx=intent.hist_bins_x,
                    nbinsy=intent.hist_bins_y,
                    color_var=intent.scatter_color_var,
                    reverse_axes=intent.reverse_axes,
                    marker_size_pct=intent.scatter_marker_size,
                    custom_colorscale=intent.custom_colorscale,
                    coordinate_system=intent.coordinate_system,
                    active_trendlines=st.session_state.active_trendlines,
                    selected_indices=current_selection,
                    selection_mode=selection_mode,
                    show_marginals=intent.show_marginals,
                    show_kde=intent.show_kde,
                    map_option=intent.map_option
                )
                
                if ret is not None:
                    fig, stats_list = ret

                    st.markdown(helper_text, unsafe_allow_html=True)
                    
                    _, col_center, _ = st.columns([1, 8, 1])
                    with col_center:
                        
                        st.plotly_chart(
                            fig, 
                            width="stretch", 
                            on_select="rerun", 
                            selection_mode=('box', 'lasso'),
                            key="scatter_plot_interactive"
                        )

                        st.write("") 
                        _, c_txt1, c_drop, c_txt2, _ = st.columns([0.5, 3.0, 1.5, 5.5, 0.5])
                        with c_txt1:
                            st.markdown("<div style='text-align: right; margin-top: 5px; font-size: 15px;'>Use Box/Lasso options to</div>", unsafe_allow_html=True)
                        with c_drop:
                            st.selectbox("Mode", ["Include", "Exclude"], key="scatter_sel_mode", label_visibility="collapsed")
                        with c_txt2:
                            st.markdown("<div style='margin-top: 5px; font-size: 15px;'>points from calculations below. Double-click on plot to reset.</div>", unsafe_allow_html=True)
                        st.write("") 

                        if stats_list:
                            import pandas as pd
                            if current_selection:
                                mode_lbl = "Included Subset" if selection_mode == "Include" else "Filtered Subset"
                                st.markdown(f"##### Regression Fits ({mode_lbl})")
                            else:
                                st.markdown("##### Regression Fits (All Data)")
                            
                            df_stats = pd.DataFrame(stats_list)
                            df_stats.insert(0, "Plot", df_stats["Fit Name"].isin(st.session_state.active_trendlines))
                            
                            edited_df = st.data_editor(
                                df_stats,
                                column_config={
                                    "Plot": st.column_config.CheckboxColumn("Plot", default=False),
                                    "Fit Name": st.column_config.TextColumn("Fit Type", disabled=True),
                                    "Equation": st.column_config.TextColumn("Equation", disabled=True),
                                    "R": st.column_config.TextColumn("R", disabled=True),
                                    "R²": st.column_config.TextColumn("R²", disabled=True),
                                },
                                hide_index=True,
                                width="stretch",
                                key="trendline_data_editor"
                            )
                            
                            new_active = edited_df[edited_df["Plot"]]["Fit Name"].tolist()
                            if new_active != st.session_state.active_trendlines:
                                st.session_state.active_trendlines = new_active
                                st.rerun()
                                
                        elif intent.coordinate_system == "Polar":
                            st.caption("ℹ️ Regression trendlines and marginals are only available in the Cartesian coordinate system.")
                else:
                    st.warning("Could not generate scatter plot for these variables.")
            else:
                st.warning("Please select a second variable to plot against.")

    finally:
        restore()