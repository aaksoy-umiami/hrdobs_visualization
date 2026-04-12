# HRDOBS Dataset Explorer & Visualizer — Package Structure

hrdobs_companion.py                  ← App entry point (tab routing, page setup)
│
├── ui_layout.py                     ← Page config, global CSS, design tokens
│
├── [Tab 1] ui_explorer.py           ← Dataset Explorer tab
│   ├── ui_explorer_controls.py      ← Sidebar filters (storm, year, basin, intensity)
│   └── ui_explorer_table.py         ← Styled HTML results table + download
│
├── [Tab 2] ui_viewer.py             ← Single-File Plotter tab
│   ├── ui_viewer_controls.py        ← Sidebar controls (variable, plot type, options)
│   │   ├── ui_viewer_file.py        ← File upload, derived fields, global domain
│   │   └── ui_viewer_domain.py      ← Domain/time limit sliders, auto-fit/reset
│   └── (calls) plotter.py
│
├── [Tab 3] ui_analysis.py           ← Single-File Statistical Analysis tab
│   ├── ui_analysis_controls.py      ← Sidebar controls (analysis type, variables)
│   └── (calls) plotter.py
│
└── [Tab 4] ui_info.py               ← Info tab (About, How To Use)


---------------------------------------------------------------------
## Architecture Philosophy & Design Pattern

The application strictly separates **UI state/collection** from **rendering logic** using a unidirectional data flow. 

1. **Sidebar Modules (`_controls.py`):** These scripts handle all `st.sidebar` widgets and session state management. They collect user inputs and return an `Intent` dataclass (e.g., `ViewerIntent`, `AnalysisIntent`, `ExplorerIntent`).
2. **Main Tab Modules (`ui_*.py`):** These scripts receive the `Intent` dataclass and coordinate the main page layout. 
3. **Rendering (`plotter.py` / `ui_*_table.py`):** These modules contain pure functions/classes that take the clean data and parameters from the `Intent` to generate visual outputs (Plotly figures or HTML tables) without reading Streamlit session state directly.

---------------------------------------------------------------------
## Shared Utilities

plotter.py        ← All Plotly figure generation (StormPlotter class)
                     • plot()                — Horizontal Cartesian scatter / vector / 3D
                     • plot_storm_relative() — Storm-relative Cartesian scatter
                     • plot_radial_height()  — Radial-height profile (range vs. altitude)
                     • plot_histogram()      — 1D histogram (bar or line)
                     • plot_histogram_2d()   — 2D joint density heatmap
                     • plot_scatter()        — Scatter plot with optional trendline
                     • add_flight_tracks()   — Module-level helper for flight track overlays

data_utils.py     ← HDF5 file loading, CSV inventory loading, metadata decoding
                     • load_data_from_h5()   — Reads groups, datasets, and attributes
                     • load_inventory_db()   — Loads the global CSV inventory

basemap.py        ← Coastline/country border traces for Cartesian map underlay
                     • get_basemap_traces()  — Returns go.Scatter line traces from TopoJSON

config.py         ← App-wide Central Registry
                     • This is the single source of truth for variables. If adding a new 
                       dataset variable or changing a color scale, update this file.
                     • Contains EXPECTED_GROUPS, EXPECTED_META, UNIT_CONVERSIONS, 
                       and GLOBAL_VAR_CONFIG (color scales, limits, coordinate flags).

ui_components.py  ← Reusable Streamlit widget helpers
                     • section_divider()
                     • spacer()
                     • sidebar_label()
                     • multiselect_with_controls()


---------------------------------------------------------------------
## Data Flow & Expected Schema

Uploaded .hdf5 file
        │
        ▼
data_utils.load_data_from_h5()
        │   Reads HDF5 groups and variable attributes.
        │   Applies unit conversions (e.g., Pa → hPa).
        │
        ▼
ui_viewer_file._inject_derived_fields()
        │   Adds computed wind speeds, wind speed errors,
        │   and vector placeholder columns.
        │
        ▼
ui_viewer_file._compute_global_domain()
        │   Scans all groups for lat/lon to build
        │   a tight bounding box for domain sliders.
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
        │           plotter.StormPlotter.plot() / plot_storm_relative()
        │                   / plot_radial_height()
        │                   │
        │                   ▼
        │           Plotly figure → st.plotly_chart()
        │
        └──▶ ui_analysis_controls.render_analysis_controls()
                    Returns AnalysisIntent (analysis type, variables, options)
                            │
                            ▼
                    plotter.StormPlotter.plot_histogram()
                            / plot_histogram_2d() / plot_scatter()
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
        │   Returns ExplorerIntent (filter selections)
        │
        ▼
ui_explorer.py  ← Applies filters, sorts, renders results
        │
        ▼
ui_explorer_table.display_explorer_table()
        │   Builds styled HTML multi-index table
        │
        ▼
st.markdown() + st.download_button()


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
| `_`     | Internal one-shot signals (auto-cleared with `.pop()`) |


---------------------------------------------------------------------
## Key Dependencies

| Package         | Used for                                      |
|-----------------|-----------------------------------------------|
| `streamlit`     | UI framework                                  |
| `plotly`        | Interactive figures                           |
| `pandas`        | DataFrames, CSV I/O                           |
| `numpy`         | Numerical operations                          |
| `h5py`          | HDF5 file reading                             |
| `scipy`         | KDE for mode estimation in stats table        |
| `streamlit_js_eval` | Optional: viewport width detection        |
