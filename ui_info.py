# -*- coding: utf-8 -*-
"""
ui_info.py
----------
Info tab for the HRDOBS Dataset Explorer & Visualizer.
Provides two sub-sections rendered from sidebar navigation buttons:
  • About      — authorship, citation placeholder, contact, disclaimer
  • How To Use — detailed per-tab usage guide
"""

import streamlit as st
from ui_layout import CLR_PRIMARY, CLR_SUBTLE, CLR_ACCENT, FS_BODY


# ---------------------------------------------------------------------------
# Sidebar button style for Info tab (black nav, not red run-button style)
# ---------------------------------------------------------------------------

def _apply_info_sidebar_css():
    st.markdown(f"""
    <style>
        /* PRIMARY (selected): white background, black text/border */
        [data-testid="stSidebar"] button[kind="primary"] {{
            background-color: #ffffff !important;
            color: {CLR_PRIMARY} !important;
            border: 3px solid {CLR_PRIMARY} !important;
            font-weight: 600;
        }}
        /* SECONDARY (unselected): black background, white text */
        [data-testid="stSidebar"] button[kind="secondary"] {{
            background-color: {CLR_PRIMARY} !important;
            color: #ffffff !important;
            border: 3px solid {CLR_PRIMARY} !important;
            font-weight: 600;
            padding: 6px 10px !important;
            min-height: 36px !important;
            height: auto !important;
            border-radius: 8px !important;
        }}
        [data-testid="stSidebar"] button[kind="secondary"] * {{
            font-size: {FS_BODY}px !important;
            color: #ffffff !important;
        }}
    </style>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_info_tab():
    _apply_info_sidebar_css()

    # Initialise sub-tab state
    if 'info_sub_tab' not in st.session_state:
        st.session_state.info_sub_tab = 'usage'

    is_about = (st.session_state.info_sub_tab == 'about')
    is_usage = (st.session_state.info_sub_tab == 'usage')

    # --- Sidebar navigation ---
    with st.sidebar:
        st.markdown("<br>" * 4, unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### Information Guide")

            label_usage = "How To Use This App" + (" →" if is_usage else "")
            if st.button(label_usage,
                         type='primary' if is_usage else 'secondary',
                         width="stretch",
                         key="btn_info_usage"):
                st.session_state.info_sub_tab = 'usage'
                st.rerun()

            label_about = "About" + (" →" if is_about else "")
            if st.button(label_about,
                         type='primary' if is_about else 'secondary',
                         width="stretch",
                         key="btn_info_about"):
                st.session_state.info_sub_tab = 'about'
                st.rerun()

    # --- Main content ---
    if st.session_state.info_sub_tab == 'about':
        _render_about()
    elif st.session_state.info_sub_tab == 'usage':
        _render_usage()


# ---------------------------------------------------------------------------
# About section
# ---------------------------------------------------------------------------

def _render_about():
    st.markdown("### About")

    st.markdown("""
    **HRDOBS Dataset Explorer & Visualizer** is an interactive tool for exploring, filtering,
    and visualizing observations from the **HRDOBS AI-Ready HDF5 dataset** — a curated collection
    of tropical cyclone reconnaissance data from NOAA and U.S. Air Force aircraft.

    The dataset includes flight-level observations, dropsonde profiles, SFMR surface wind
    measurements, and tail Doppler radar data, all co-located with best-track storm position
    and interpolated storm-relative coordinates.
    """)

    st.markdown("---")

    # Citation placeholder
    col_cit1, col_cit2 = st.columns([0.6, 0.4])

    with col_cit1:
        st.markdown("#### 📄 Citation")
        st.markdown("""
        *Citation information will be added once the companion paper is published.*

        In the meantime, if you use this dataset or tool in your research, please contact the
        author for the appropriate reference.
        """)
        # Placeholder link button — update URL when paper is live
        # st.link_button("Read the Paper (DOI)", "https://doi.org/TBD")

    with col_cit2:
        st.markdown("#### 📝 BibTeX *(placeholder)*")
        st.code("""\
@article{Aksoy_HRDOBS_TBD,
  title   = {TBD},
  author  = {Aksoy, Altug},
  journal = {TBD},
  year    = {TBD},
  doi     = {TBD}
}""", language="latex")

    st.markdown("---")

    col_auth1, col_auth2 = st.columns(2)

    with col_auth1:
        st.markdown("#### 👤 Author")
        st.markdown("""
**Altug Aksoy**
Scientist, *CIMAS/Rosenstiel School, University of Miami*  
& *Hurricane Research Division / AOML, NOAA*

📧 [aaksoy@miami.edu](mailto:aaksoy@miami.edu)  
🌐 [NOAA/HRD Profile](https://www.aoml.noaa.gov/hrd/people/altugaksoy/)  
🆔 [ORCID: 0000-0002-2335-7710](https://orcid.org/0000-0002-2335-7710)
        """)

    with col_auth2:
        st.markdown("#### 💻 Dataset & Source Code")
        st.markdown("""
        The HRDOBS dataset and the source code for this application will be made
        publicly available upon publication of the companion paper.

        For early access or collaboration inquiries, please reach out directly via
        the contact information above.
        """)

    st.markdown("---")

    st.markdown("#### ⚠️ Disclaimer & Usage")
    st.markdown("""
    **All rights reserved.** This application is intended for research and educational purposes.
    Please adhere to the citation guidelines provided above when using the dataset or this tool
    in any published work.

    **Feedback welcome!** If you encounter bugs or have feature suggestions, please contact the
    author at the email address above.

    *This application is optimized for desktop environments. Users on smaller screens may
    experience layout or performance limitations.*
    """)


# ---------------------------------------------------------------------------
# How To Use section
# ---------------------------------------------------------------------------

def _render_usage():
    st.markdown("### How To Use This App")

    st.markdown("""
    #### General
    *Follow these steps to interact with the user interface.*

    1. Choose functionality from the **tabs** at the top of the page.
    2. Adjust the relevant configuration options in the **left sidebar**.
    3. Results update automatically as you change settings — no "Run" button is needed
       unless explicitly indicated.

    ---

    #### 🌍 Tab 1 — Dataset Explorer

    *Browse the full HRDOBS inventory across all storms, years, and platforms. -- No additional file required, the inventory is included with this app.*

    **Sidebar controls:**
    - **Storm Information filters:** Narrow down the inventory using the multiselect dropdowns
      for storm name, season year, basin, and observation platform (NOAA / Air Force).
    - **Variable Group filters:** Choose which main variable groups to include in the filtered list.
    - **Variable filters:** Choose which specific variables to include in the filtered list.

    **Main panel:**
    - **The inventory table** shows all matching HDF5 files with metadata.
    - **The sort area** above the inventory table allows for sorting within the shown table.
    - **The download button** is to download the filtered list as a CSV file to your local computer.

    ---

    #### 📊 Tab 2 — Single-File Plotter

    *Load an AI-Ready HDF5 file and generate interactive spatial or vertical plots to visualize the contents of the dataset.*

    **Getting started:**
    1. **Upload a file** using the File Upload section in the sidebar (`.h5` or `.hdf5`).
       Once loaded, the file remains in memory until you clear it.
    2. **File inventory:** Expand to view exactly which platform/variable group sare included in the file uploaded.
    3. **Metadata inventory:** Expand to view the contents of the metadata associated with the file uploaded.
                
    **Plot Variable (📈 Plot Variable section):**
    - Choose the **variable group** and the **variable** from within to visualize it.
    - When available, you can also plot the **variable error** instead.
    - Also control whether you want to plot the variable in **log scale** for color scaling.

    **Plot Type (🧭 Plot Type section):**
    - **Horizontal Cartesian** — Standard lat/lon map view with optional basemap underlay.
    - **Horizontal Storm-Relative** — Positions all observations relative to the storm center.
      *(Requires a spline or best-track group with ≥ 2 points.)*
      - **Upward Direction Represents:** Choose whether "up" in the plot means geographic North
        or the direction of storm motion.
    - **Radial-Height Profile** — Collapses all azimuths and plots storm-relative range (km)
      on the X axis vs. height or pressure on the Y axis.
      - **Plot on Y axis:** Choose between geopotential height and pressure as the vertical coordinate.
      *(Requires a spline or best-track group with ≥ 2 points.)*

    **Plot Options (⚙️ Plotting Options section):**
    - **Storm Center:** Toggle display of the storm center marker (Cartesian mode only).
    - **Map Underlay:** Add a coastline/country basemap (Cartesian and Storm-relative modes only).
    - **Apply Thinning:** Randomly thin observations by a percentage for faster rendering.
      *(For some platforms like TDR superobs, automatic thinning may be applied.)*
    - **Filter by Level:** Restrict observations to a height or pressure range. Use the
      **Vertical Coord.** dropdown to switch between height (m) and pressure (hPa).
    - **Plot flight track from:** Overlay the flight track of a selected aircraft on the plot.
    - **3D View:** Render the horizontal plot in 3D with height on the Z axis (Cartesian/Storm-Relative only).
    - **Marker Size:** Adjust the size of observation markers.

    **Plot Domain Limits:**
    - **Lat/Lon sliders** (Cartesian): Set the geographic bounding box.
    - **Max Range slider** (Storm-Relative / Radial-Height): Set the maximum storm-relative
      radius to display.
    - **Vertical range slider:** Restrict the displayed vertical range (height in m or
      pressure in hPa depending on the selected Vertical Coord.). The colorbar auto-scales
      to whatever is currently visible.
    - **Time range slider:** Filter observations by time relative to the file's temporal coverage.
    - **Auto-Fit Domain** and **Reset Domain** buttons quickly set or clear the spatial limits.

    ***Note:** Zooming options on the plot itself are Streamlit-native controls and will not re-render new gridlines.
      To see denser gridlines in a zoomed-in region, use the zoom controls in the sidebar first.*

    ---

    #### 📈 Tab 3 — Single-File Statistical Analysis

    *Compute and visualize distributions and correlations from a loaded file.*

    **Getting started:**
    - This tab shares the file loaded in Tab 2. If no file is loaded, upload one via the
      file upload section in the sidebar.

    **Analysis Types:**
    - **Histogram Analysis (1D)** — Distribution of a single variable as a bar or line histogram.
      A summary statistics table is rendered below the figure showing **Count, Mean, Median,
      Mode, and Std Dev**.
    - **Histogram Analysis (2D)** — Joint density heatmap of a primary variable vs. a secondary
      variable.
    - **Scatter Analysis** — Point cloud of two variables. Optionally color points by a third
      variable or by local point density. A linear trendline can be overlaid.

    **Variable selectors (📈 Plot Variable section):**
    - **First Variable / Primary Variable / Variable:** The main quantity to analyze, plotted on the y axis by default (but can be swapped, see below)
    - **Second Variable / Secondary Variable / Coordinate Variable:** Used as the x axis
      in 2D Histogram and Scatter modes (disabled in 1D Histogram mode).
    - **Show on log scale** checkbox under each variable: Applies a log₁₀ transform to that
      variable before plotting. The plot title and axis labels reflect the transformation with
      a *(Log Scale)* note in the units.

    **Histogram Controls:**
    - **Num. of Intervals (X/Y):** Set bin counts manually or leave on Default.
    - **Normalization:** Optionally normalize bins to percentages — fully, or within each
      primary/secondary bin slice (2D only).
    - **Reverse X and Y axes:** Swap which variable appears on which axis.
    - **Render as line plot:** Draw the 1D histogram as a continuous line rather than bars
      (1D mode only).

    **Scatter Controls:**
    - **Show Trendline:** Overlay a least-squares linear fit.
    - **Color By:** Color markers uniformly, or by a selected variable.
    - **Marker Size:** Scale the size of scatter points.

    **Main panel:**
    - Plots update automatically when controls change.
    - In **1D Histogram mode**, a compact statistics table appears below the figure with
      five columns: **Count, Mean, Median, Mode, Std Dev**. Units and log scale context
      are visible in the figure title rather than the table headers.
    - Figures can be downloaded using the camera icon on the Plotly toolbar.
    """)
