# HRDOBS Visualizer: Interactive Exploration of Hurricane Observations

![Streamlit Version](https://img.shields.io/badge/Streamlit-v1.57.0-FF4B4B?logo=streamlit)

This repository contains the source code for the **HRDOBS Visualizer**, an interactive web application designed to explore, view, and analyze the HRDOBS dataset from the Hurricane Research Division (HRD). 

### 🌐 <a href="https://hrdobs-visualization.streamlit.app" target="_blank">Launch the Live App on Streamlit</a>

## Overview
Built to streamline the visualization of complex atmospheric data, this companion app provides an intuitive interface for querying inventory databases and rendering meteorological observations on interactive maps. It is structured modularly to support data exploration and detailed file viewing for the contents of HRDOBS dataset hdf5 files.

### Key Features
* **Inventory Explorer:** Search and filter the built-in HRDOBS inventory database to locate specific storms and datasets.
* **Direct Archive Access:** Load any file from the filtered inventory results straight from the official HRDOBS online repository, with no manual download required. Files can also be uploaded manually from your own computer.
* **Interactive Data Viewer:** Visualize spatial observation data using customizable basemaps and interactive plotting tools. 
* **Modular Analysis Suite:** Access dedicated analysis and domain-viewing controls for deep-dives into specific hurricane events.
* **Extensible Architecture:** Built with Streamlit, the app separates UI layout, data utilities (`data_utils.py`), and rendering (`plotter.py`, `plotter_basemap.py`) for easy academic extension.

## Requirements
* **Streamlit 1.57.0** is strictly required to ensure full functionality. 
* This application is optimized for desktop environments.

## Research & Authorship
This tool was developed by **Dr. Altug Aksoy** (University of Miami / CIMAS) to assist researchers, meteorologists, and students in interacting with hurricane observation data.

*Note: The HRDOBS v1.0 dataset has been submitted to NCEI. Additionally, a companion manuscript titled "HRDOBS: A Comprehensive, AI-Ready Dataset for Standardized Observations Collected in and Around North Atlantic Tropical Cyclones" by Altug Aksoy, Kathryn Sellwood, Sim Aberson, and Brittany Dahl has been submitted to the Bulletin of the American Meteorological Society (BAMS) and is currently under review. The official DOIs for both the publication and the dataset will be added here once they are minted and available.*

---

## ✉️ Contact & Support
If you have questions regarding the data, the visualization tool, or encounter technical issues, please feel free to reach out:

* **Direct Code Inquiry**: <a href="mailto:aaksoy@miami.edu?subject=Question%20about%20HRDOBS%20Visualizer" target="_blank">Click here to send an email inquiry</a>
* **Direct Dataset Inquiry**: <a href="mailto:ksellwood@earth.miami.edu?subject=Question%20about%20HRDOBS%20Dataset" target="_blank">Click here to send an email inquiry</a>
* **Community**: <a href="https://github.com/aaksoy-umiami/hrdobs_visualization/discussions" target="_blank">Join the conversation in the Discussions tab!</a>
