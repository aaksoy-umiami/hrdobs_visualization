# HRDOBS Dataset Explorer & Visualizer v1.0 — Package Structure

hrdobs_companion.py                  ← App entry point (tab routing, page setup, mobile detection)
│
├── ui_layout.py                     ← Page config, global CSS, design tokens, viewer styling overrides
│
├── [Tab 1] ui_explorer.py           ← Dataset Explorer tab (coordinating filters, plots, and tables)
│   ├── ui_explorer_controls.py      ← Sidebar filters (storm, year, geography, SHIPS, intensity, variables)
│   ├── ui_explorer_table.py         ← Styled HTML results table + storm-level multi-index summary
│   └── ui_explorer_plots.py         ← Summary visual graphics (Cartesian maps, scatter plots, histograms)
│
├── [Tab 2] ui_viewer.py             ← Single-File Plotter tab
│   ├── ui_viewer_controls.py        ← Sidebar controls (variable, plot type, plotting options)
│   ├── ui_viewer_file.py            ← File loading (manual upload or online repository), HDF5 memory processing, metadata/SHIPS inspection
│   └── ui_viewer_domain.py          ← Spatial and temporal domain limits (sliders, auto-fit/reset)
│
├── [Tab 3] ui_analysis.py           ← Single-File Statistical Analysis tab (data distributions, statistics)
│   └── ui_analysis_controls.py      ← Sidebar controls (analysis type, normalization, coordinate systems)
│
└── [Tab 4] ui_info.py               ← Info tab (About v1.0, Additional Sources, How To Use)


---------------------------------------------------------------------
## Architecture Philosophy & Design Pattern

The application strictly separates **UI state/collection** from **rendering logic** using a unidirectional data flow. 

1. **Sidebar Modules (`_controls.py`, `_domain.py`, `_file.py`):** These scripts handle all `st.sidebar` widgets and session state management. They collect user inputs and return an `Intent` dataclass (e.g., `ViewerIntent`, `AnalysisIntent`, `ExplorerIntent`).
2. **Main Tab Modules (`ui_*.py`):** These scripts receive the `Intent` dataclass and coordinate the main page layout. 
3. **Plotter Mixin Architecture (`plotter*.py`):** The core `StormPlotter` is built using a modular mixin pattern. `plotter_base.py` handles state, metadata, and data filtering, while specific plot types (Cartesian, Storm-Relative, Radial-Height, Histogram, Scatter) are separated into specialized mixin classes.
4. **Rendering:** Pure functions and classes take clean data and parameters from the `Intent` to generate visual outputs (Plotly figures or HTML tables) without reading Streamlit session state directly.

---------------------------------------------------------------------
## Shared Utilities

plotter.py                 ← Main assembler aggregating all plotting mixins into the `StormPlotter` class.

plotter_base.py            ← `StormPlotterBase`: Core class for shared state, data filtering, and variable metadata introspection.
plotter_cartesian.py       ← `CartesianMixin`: 2D/3D Cartesian geographic maps and flight track overlays.
plotter_storm_relative.py  ← `StormRelativeMixin`: Storm-relative horizontal mapping and vector rotation conventions.
plotter_radial_height.py   ← `RadialHeightMixin`: 2D radial-height profile plotting and vector decomposition.
plotter_histogram.py       ← `HistogramMixin`: 1D/2D histograms, KDE overlays, and marginal distributions.
plotter_scatter.py         ← `ScatterMixin`: Scatter plots with optional mathematical fit trendlines.
plotter_basemap.py         ← Black-line basemap helpers for geographic coastlines (loads TopoJSON).

vector_utils.py            ← Utility functions for calculating and rendering color-binned 2D/3D stick arrows in Plotly.
data_utils.py              ← HDF5/CSV data loading, metadata decoding, CF-compliant time parsing, and spatial derivations.

config.py                  ← App-wide Central Registry.
                              • Source of truth for variable defaults, colorscales, and coordinate flags.
                              • Contains EXPECTED_GROUPS, EXPECTED_META, SHIPS_PREDICTOR_META, and UNIT_CONVERSIONS.

ui_components.py           ← Reusable Streamlit widget helpers and session state synchronization.
                              • `safe_slider()`, `dynamic_range_slider()`, `multiselect_with_controls()`


---------------------------------------------------------------------
## Data Flow & Expected Schema

Uploaded .hdf5 file (v1.0 AI-Ready Format)
        │
        ▼
data_utils.load_data_from_h5()
        │   Reads HDF5 groups and variable attributes.
        │   Applies unit conversions (e.g., Pa → hPa).
        │
        ▼
data_utils.inject_derived_fields()
        │   Adds derived metrics (e.g., Distance from Center, Azimuths, 
        │   Computed 3D/Horizontal Winds, Wind Errors).
        │
        ▼
data_utils.compute_global_domain() & compute_vert_bounds()
        │   Scans all groups for lat/lon/z coordinates to build
        │   tight bounding boxes for spatial domain sliders.
        │
        ▼
data_pack  ←  The core memory object shared across visualization tabs.
        │     Schema:
        │      • data: dict of pandas DataFrames (the observations).
        │      • track: DataFrame containing the storm track.
        │      • meta: Global metadata (storm_center tuple, bounds, info dict).
        │      • var_attrs: Dict mapping variables to their metadata (units, long_name).
        │      • global_domain: Dict of global lat/lon bounds.
        │      • vert_bounds: Dict of pre-computed vertical limits per group.
        │
        ├──▶ ui_viewer_controls.render_viewer_controls()
        │           Returns ViewerIntent (all plot parameters)
        │                   │
        │                   ▼
        │           plotter.StormPlotter methods (e.g., plot(), plot_storm_relative())
        │                   │
        │                   ▼
        │           Plotly figure → st.plotly_chart()
        │
        └──▶ ui_analysis_controls.render_analysis_controls()
                    Returns AnalysisIntent (analysis type, coordinate system, normalizations)
                            │
                            ▼
                    plotter.StormPlotter methods (e.g., plot_histogram_2d(), plot_scatter())
                            │
                            ▼
                    Plotly figure → st.plotly_chart()


---------------------------------------------------------------------
## Dataset Explorer Data Flow

hrdobs_inventory_db.csv
        │
        ▼
data_utils.load_inventory_db()
        │
        ▼
ui_explorer_controls.render_explorer_controls()
        │   Returns ExplorerIntent (filter selections, including SHIPS data)
        │
        ▼
ui_explorer.py  ← Applies filters, sorts, and coordinates outputs
        │
        ├──▶ ui_explorer_plots.render_explorer_summary_plots()
        │         Builds geographic category maps, scatter plots, and histograms
        │
        ├──▶ ui_explorer_table.display_summary_table()
        │         Builds storm-level aggregated summary view
        │
        ├──▶ ui_explorer_table.display_explorer_table()
        │         Builds detailed, styled HTML multi-index file table
        │
        └──▶ session_state['explorer_available_files' / 'explorer_row_lookup']
                  Publishes the filtered, sorted file list for the sidebar
                  loader on the Viewer and Analysis tabs (no widget rendered)


---------------------------------------------------------------------
## CSS & Theming Strategy

This application does not rely on standard Streamlit theming configurations (e.g., `.streamlit/config.toml`) for component styling. Instead, native widgets are heavily customized via injected CSS in **`ui_layout.py`**. 
If you need to change font sizes, button colors, or spacing, adjust the "Design Tokens" defined at the top of `ui_layout.py`.

---------------------------------------------------------------------
## Session State Key Prefixes

| Prefix  | Scope                                        |
|---------|----------------------------------------------|
| `v_`    | File Data Viewer tab (persisted in `viewer_state`) |
| `a_`    | Statistical Analysis tab (persisted in `analysis_state`) |
| `ui_`   | Dataset Explorer tab (persisted in `explorer_state`) |
| `explorer_` | Cross-tab: filtered results published by Tab 1 and read by the sidebar loader on Tabs 2 and 3 |
| `_`     | Internal one-shot signals (auto-cleared with `.pop()`) |


---------------------------------------------------------------------
## Key Dependencies

| Package             | Used for                                      |
|---------------------|-----------------------------------------------|
| `streamlit`         | UI framework                                  |
| `plotly`            | Interactive figures (2D/3D, Maps, Charts)     |
| `pandas`            | DataFrames, CSV I/O                           |
| `numpy`             | Numerical operations                          |
| `h5py`              | HDF5 file reading                             |
| `scipy`             | KDE for mode estimation and density contours  |
| `streamlit_js_eval` | Optional: mobile device/viewport detection    |