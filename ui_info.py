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

    if 'info_sub_tab' not in st.session_state:
        st.session_state.info_sub_tab = 'usage'

    is_about = (st.session_state.info_sub_tab == 'about')
    is_usage = (st.session_state.info_sub_tab == 'usage')

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

    col_cit1, col_cit2 = st.columns([0.6, 0.4])

    with col_cit1:
        st.markdown("#### 📄 Citation")
        st.markdown("""
        *Citation information will be added once the companion paper is published.*

        In the meantime, if you use this dataset or tool in your research, please contact the
        author for the appropriate reference.
        """)

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
Scientist, *CIMAS/Rosenstiel School, University of Miami* & *Hurricane Research Division / AOML, NOAA*

📧 [aaksoy@miami.edu](mailto:aaksoy@miami.edu)  
🌐 [NOAA/HRD Profile](https://www.aoml.noaa.gov/hrd/people/altugaksoy/)  
🆔 [ORCID: 0000-0002-2335-7710](https://orcid.org/0000-0002-2335-7710)
        """)

    with col_auth2:
        st.markdown("#### 💻 Dataset & Source Code")
        st.markdown("""
        The HRDOBS dataset and the source code for this application will be made
        publicly available along with the publication of the companion paper.

        For early access or collaboration inquiries, please reach out directly via
        the contact information provided.
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
    #### 💡 General Workflow & Pro-Tips
    1. **Navigate** between different tools using the tabs at the top of the page.
    2. **Configure** your view using the options in the left sidebar. Results update automatically—no "Run" button is needed!
    3. **Shared Memory:** Data uploaded in the *Single-File Plotter* (Tab 2) is automatically shared with the *Statistical Analysis* tool (Tab 3). You only need to load your file once.
    4. **Interactive Charts:** All generated charts are fully interactive. You can hover over data points for exact values, click and drag to zoom or rotate 3D plots, and use the camera icon in the top right of any chart to download it as an image.

    ---

    #### 🌍 Tab 1 — Dataset Explorer
    **Purpose:** Browse the full HRDOBS inventory across all storms, years, and platforms without needing to download massive files first. *(The global inventory database is built into this app).*

    **Quick Start:**
    1. **Filter** the inventory using the sidebar (select specific storm names, years, basins, or observation platforms).
    2. **Refine** the table by toggling specific variable groups on or off.
    3. **Download** the customized list as a CSV file to your local computer for external reference.

    ---

    #### 📊 Tab 2 — Single-File Plotter
    **Purpose:** Visualize spatial and vertical data from a single AI-Ready HDF5 file.

    **Quick Start:**
    1. **Upload** an `.h5` or `.hdf5` file using the sidebar.
    2. **Select** the observation group (e.g., dropsonde, radar) and the variable you want to see.
    3. **Choose** your plot type: 
       - **Horizontal Cartesian:** A standard geographic map view.
       - **Horizontal Storm-Relative:** Centers the map on the storm to show where observations fall relative to the eye. *(Requires storm track data to be present in the uploaded file).*
       - **Radial-Height Profile:** Creates a vertical cross-section showing altitude or pressure against the distance from the storm center.

    **Key Controls:**
    - **Plotting Options:** Toggle the storm center marker, add a geographic map underlay, view the data in 3D, or thin the data to speed up rendering. You can also filter observations to a specific altitude or pressure level.
    - **Domain & Time Limits:** Use the sliders to zoom into specific latitudes, longitudes, or time windows. Clicking "Auto-fit" will automatically snap the view to the data currently available.

    ---

    #### 📈 Tab 3 — Single-File Statistical Analysis
    **Purpose:** Compute and visualize data distributions and correlations from your loaded file.

    **Quick Start:**
    1. Ensure a file is loaded (via the sidebar or inherited from Tab 2).
    2. **Select Analysis Mode:** - **Histogram Analysis (1D):** View the distribution of a single variable. Generates a bar/line chart and a summary statistics table (Count, Mean, Median, Mode, Std Dev).
       - **Histogram Analysis (2D):** Create a density heatmap comparing two variables.
       - **Scatter Analysis:** Plot two variables against each other as a point cloud.
    3. **Choose** your primary (and secondary) variables to analyze.

    **Key Controls:**
    - **Log Scale:** Toggle variables into log₁₀ scale directly from the variable selection area.
    - **Normalization (Histograms):** Display bin counts as raw numbers or normalize them to percentages (e.g., fully normalized, or normalized within specific X/Y slices).
    - **Scatter Enhancements:** Overlay a linear trendline, or color your scatter points by a third variable or by local point density.
    """)
  
