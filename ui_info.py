# -*- coding: utf-8 -*-
"""
ui_info.py
----------
Info tab for the HRDOBS Dataset Explorer & Visualizer.
Provides sub-sections rendered from sidebar navigation buttons:
  • Help: How To Use This App
  • Additional Sources
  • About: Author & Citation
"""

import streamlit as st
from ui_layout import CLR_PRIMARY, CLR_SUBTLE, CLR_ACCENT, FS_BODY


# ---------------------------------------------------------------------------
# Sidebar button style for Info tab
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
            width: 100% !important; /* Keep active button full width */
        }}
        /* SECONDARY (unselected): black background, white text */
        [data-testid="stSidebar"] button[kind="secondary"] {{
            background-color: {CLR_PRIMARY} !important;
            color: #ffffff !important;
            border: 3px solid {CLR_PRIMARY} !important;
            font-weight: 600;
            
            /* Make it slightly smaller vertically */
            padding: 4px 10px !important; 
            min-height: 32px !important;
            height: auto !important;
            border-radius: 8px !important;
            
            /* Make it slightly smaller horizontally and center it */
            width: 90% !important; 
            margin-left: 5% !important;
            margin-right: 5% !important;
            display: block !important;
        }}
        
        /* Drop the font size of the inactive button by 1px */
        [data-testid="stSidebar"] button[kind="secondary"] * {{
            font-size: calc({FS_BODY}px - 1px) !important;
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

    is_usage = (st.session_state.info_sub_tab == 'usage')
    is_sources = (st.session_state.info_sub_tab == 'sources')
    is_about = (st.session_state.info_sub_tab == 'about')

    with st.sidebar:
        st.markdown("<br>" * 4, unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### Information Guide")

            label_usage = "Help: How To Use This App" + (" →" if is_usage else "")
            if st.button(label_usage,
                         type='primary' if is_usage else 'secondary',
                         width="stretch",
                         key="btn_info_usage"):
                st.session_state.info_sub_tab = 'usage'
                st.rerun()

            label_sources = "Additional Sources" + (" →" if is_sources else "")
            if st.button(label_sources,
                         type='primary' if is_sources else 'secondary',
                         width="stretch",
                         key="btn_info_sources"):
                st.session_state.info_sub_tab = 'sources'
                st.rerun()

            label_about = "About: Author & Citation" + (" →" if is_about else "")
            if st.button(label_about,
                         type='primary' if is_about else 'secondary',
                         width="stretch",
                         key="btn_info_about"):
                st.session_state.info_sub_tab = 'about'
                st.rerun()

    if st.session_state.info_sub_tab == 'usage':
        _render_usage()
    elif st.session_state.info_sub_tab == 'sources':
        _render_sources()
    elif st.session_state.info_sub_tab == 'about':
        _render_about()


# ---------------------------------------------------------------------------
# About section
# ---------------------------------------------------------------------------

def _render_about():
    st.markdown("### About")

    st.markdown("""
    **HRDOBS Dataset Explorer & Visualizer v1.0** is an interactive tool for exploring, filtering,
    and visualizing observations from the **HRDOBS v1.0 AI-Ready HDF5 dataset** — a curated collection
    of tropical cyclone (TC) reconnaissance data from NOAA and U.S. Air Force aircraft.

    **Each HDF5 file is further accompanied by an Icechunk "sidecar" JSON file** that provides the digital address of
    each data vector contained in the HDF5 files. Using these digital maps, it is possible to bypass
    heavyweight h5py dependencies and directly utilize cloud-based storage and parallel-access capabilities
    for highly efficient machine-learning applications.
                
    The dataset includes dropsonde profiles, flight-level observations, SFMR surface wind
    measurements, and Tail Doppler Radar superobservations. These aircraft-based measurements are further accompanied
    by various TC track datasets and Statistical Hurricane Intensity Prediction Scheme (SHIPS) TC environment parameters.
    
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
Scientist, *CIMAS/Rosenstiel School, University of Miami*

📧 [aaksoy@miami.edu](mailto:aaksoy@miami.edu)  
🌐 [LinkedIn Profile](https://www.linkedin.com/in/altugaksoy)  
🆔 [ORCID: 0000-0002-2335-7710](https://orcid.org/0000-0002-2335-7710)
        """)

    with col_auth2:
        st.markdown("#### 💻 Dataset & Source Code")
        st.markdown("""
        The HRDOBS v1.0 dataset DOI will be made publicly available along with the publication of the companion paper. The source code can be accessed at:
        
        [https://github.com/aaksoy-umiami/hrdobs_visualization](https://github.com/aaksoy-umiami/hrdobs_visualization)

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
# Additional Sources section
# ---------------------------------------------------------------------------

def _render_sources():
    st.markdown("### Upstream Data Sources")

    st.markdown("""
    The AI-Ready HRDOBS Dataset is not created in a vacuum. It is meticulously constructed by 
    aggregating, homogenizing, and interpolating a multitude of raw observations, tracking data, 
    and environmental parameters gathered from several authoritative online sources.
    
    Below is a breakdown of the primary data sources utilized to build this dataset, outlining 
    what they provide and where they originate.
    """)

    st.markdown("---")

    # Source 1: Aircraft Data
    st.markdown("#### ✈️ 1. Main Aircraft Reconnaissance Data")
    st.markdown("""
    **Description:** This represents the core scientific payload of the dataset. It includes high-resolution,
    quality-controlled flight-level data, dropsonde thermodynamic profiles, Stepped Frequency Microwave Radiometer 
    (SFMR) surface wind estimates, and Tail Doppler Radar (TDR) wind fields collected by NOAA P-3, NOAA G-IV, 
    and U.S. Air Force Reserve Hurricane Hunter aircraft.
    
    **Origin:** Collected and hosted by the **[NOAA/AOML Hurricane Research Division (HRD)](https://www.aoml.noaa.gov/data-products/#hurricanedata)** via their official webpage and data servers.
    """)

    # Source 2: HURDAT2
    st.markdown("#### 🌪️ 2. NHC HURDAT2 (Best Track)")
    st.markdown("""
    **Description:** The official historical "Best Track" database for the North Atlantic basin tropical cyclones. HURDAT2 provides 
    definitive, post-storm reanalyzed data at 6-hourly intervals, including the storm's center location, maximum sustained surface 
    wind speed, and minimum sea-level pressure. It acts as the foundational baseline for storm identification and overall intensity.
    
    **Origin:** Maintained and published by the **[National Hurricane Center (NHC) Data Archive](https://www.nhc.noaa.gov/data/#hurdat)**.
    """)

    # Source 3: Vortex Messages
    st.markdown("#### 📡 3. Vortex Data Messages (VDM)")
    st.markdown("""
    **Description:** Standardized, operational messages transmitted in real-time by reconnaissance aircraft when they 
    penetrate a tropical cyclone's center. VDMs provide vital "fixes" on the exact coordinates of the eye, 
    the minimum central pressure, the maximum flight-level and surface winds, and temperature gradients. These 
    fixes provide crucial anchor points for storm tracking.
    
    **Origin:** Extracted from the **[NHC's Aircraft Reconnaissance Archive](https://verif.rap.ucar.edu/jntweb/hurricanes-beta/structure/vortex/vdm_data/)**.
    """)

    # Source 4: Spline Tracks
    st.markdown("#### 🗺️ 4. High-Resolution Spline Tracks")
    st.markdown("""
    **Description:** Because HURDAT2 is limited to 6-hour intervals, it is often insufficient for highly granular 
    storm-relative coordinates. The HRD derives objectively smoothed "spline tracks" from high-frequency aircraft 
    fixes. These tracks provide a continuous, high-temporal-resolution estimation of the storm center at flight level.
    
    **Origin:** Hosted and provided by the **[NOAA/AOMLHRD](https://www.aoml.noaa.gov/data-products/#hurricanedata)** via their official webpage and data servers.
    """)

    # Source 5: SHIPS
    st.markdown("#### 📊 5. Statistical Hurricane Intensity Prediction Scheme (SHIPS)")
    st.markdown("""
    **Description:** The SHIPS dataset evaluates synoptic and environmental diagnostics along the track of a tropical 
    cyclone. It provides the crucial environmental context for the storm, including parameters like vertical wind shear 
    magnitude and direction (e.g., the 850-200 hPa shear vector), ocean heat content, maximum potential intensity (MPI), 
    and relative humidity values.
    
    **Origin and documentation:** Accessed via the official **[SHIPS website at CIRA (Cooperative Institute for Research in the Atmosphere)](https://rammb2.cira.colostate.edu/research/tropical-cyclones/ships/development_data/)**.
    """)


# ---------------------------------------------------------------------------
# How To Use section
# ---------------------------------------------------------------------------

def _render_usage():
    st.markdown("### How To Use This App")

    st.markdown("""
    #### 💡 General Workflow & Usage Tips
    1. **Navigate** between different tools using the tabs at the top of the page.
    2. **Configure** your view using the options in the left sidebar. Results update automatically—no "Run" button is needed!
    3. **File Upload Requirements:**
       - No file upload is needed for Tab 1 as it uses its own built-in database.
       - Tabs 2 and 3 require uploading one hdf5 file from the dataset to memory.
    4. **Shared Memory:** Data uploaded in the *Individual File Plotter* tab (Tab 2) is automatically shared with the *Individual File Statistical Analysis* tab (Tab 3). You only need to load your file once.
    
    #### 💡 Chart Controls and Saving Figures
    1. **Interactive Charts:** All generated charts are fully interactive. You can hover over data points for exact values, click and drag to zoom or rotate 3D plots, and use the camera icon in the top right of any chart to download it as an image.
    2. **Interactive vs. Manual Zooming:**
       - For quick zooming and panning, use the hover controls on the top right of the plots.
       - Manual zooming controls in the sidebar will redefine the color scales/full plot area and redraw vectors/scatter points for more precise plotting.
    3. **Saving figures as PNG:** Then controls that appear on the top-right of figures when hovering over them also provide the option to save them as png graphic files.  

    ---

    #### 🌍 Tab 1 — Dataset Explorer
    **Purpose:** Browse the full HRDOBS inventory across all storms, years, and platforms without needing to download massive files first. *(The global inventory database is built into this app).*

    **Quick Start:**
    1. **Filter** the inventory using the sidebar (select specific storm names, years, basins, geographical region, observation platforms/variables, or SHIPS parameters).
    2. **Refine** the table by toggling specific variable groups on or off.
       - **View Summary Table of Filtered Results:** Shows a storm-based summary table for the filters applied.
       - **View Summary Graphics of Filtered Results:** Displays summary graphics based on the filters applied.
    3. **Download** the customized list as a CSV file to your local computer for external reference.

    ---

    #### 📊 Tab 2 — Single-File Plotter
    **Purpose:** Visualize spatial and vertical data from a single HRDOBS HDF5 file.

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
    2. **Select Analysis Mode:**
       - **Histogram Analysis (1D):** View the distribution of a single variable.
       - **Histogram Analysis (2D):** Create a density heatmap between two variables, along with the option to plot marginal probability densities.
       - **Scatter Analysis:** Plot two variables against each other as a point cloud, with the option of coloring for a third variable.
    3. **Choose** your primary (and secondary) variables to analyze.

    **Key Controls:**
    - **Log Scale:** Toggle variables into log₁₀ scale directly from the variable selection area.
    - **Normalization (Histograms):** Display bin counts as raw numbers or normalize them to percentages (e.g., fully normalized, or normalized within specific X/Y slices).
    - **Scatter Enhancements:** Overlay a linear trendline, or color your scatter points by a third variable or by local point density.
    """)
