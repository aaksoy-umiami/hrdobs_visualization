# -*- coding: utf-8 -*-
"""
config.py
----------
Global configuration parameters shared by all other functions.
"""

EXPECTED_GROUPS = [
    "dropsonde_ghawk", "dropsonde_noaa42", "dropsonde_noaa43", "dropsonde_noaa49", "dropsonde_usaf",
    "flight_level_hdobs_noaa42", "flight_level_hdobs_noaa43", "flight_level_hdobs_noaa49", "flight_level_hdobs_usaf",
    "sfmr_noaa42", "sfmr_noaa43", "sfmr_usaf",
    "tdr_noaa42", "tdr_noaa43", "tdr_noaa49",
    "track_best_track", "track_spline_track", "track_vortex_message"
]

EXPECTED_META = [
    "center_from_tc_vitals", "creator_email", "creator_name",
    "geospatial_lat_max", "geospatial_lat_min", "geospatial_lat_units",
    "geospatial_lon_max", "geospatial_lon_min", "geospatial_lon_units",
    "platforms", "radius_of_maximum_wind_km", "storm_datetime", "storm_epoch", "storm_id",
    "storm_intensity_ms", "storm_motion", "storm_mslp_hpa", "storm_name", 
    "tc_category", "time_coverage_end", "time_coverage_start", "title", "version_number"
]

GLOBAL_VAR_CONFIG = {
    # --- NON-PLOTTABLE COORDINATES & METADATA (Hidden) ---
    'lat': {'hide': True, 'is_coord': True}, 'lon': {'hide': True, 'is_coord': True}, 'time': {'hide': False, 'is_coord': True},
    'clat': {'hide': True, 'is_coord': True, 'is_track_pos': True},
    'clon': {'hide': True, 'is_coord': True, 'is_track_pos': True},
    'az': {'hide': True, 'is_coord': True}, 'rmw': {'hide': True, 'is_coord': True},
    'qerr': {'hide': True}, 'spderr': {'hide': True},

    # --- TRACK INTENSITY VARIABLES ---
    'pmin': {'colorscale': 'Viridis_r', 'hide': False, 'display_name': 'Min Pressure (hPa)'},
    'vmax': {'colorscale': 'Turbo',     'hide': False, 'cmin': 0, 'display_name': 'Max Wind (m/s)'},

    # --- DIVERGING VARIABLES (Centered at 0) ---
    'rvel': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False}, 
    'w':    {'colorscale': 'PuOr_r', 'cmid': 0, 'hide': False}, 
    'u':    {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False}, 
    'v':    {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False}, 
    
    # --- SEQUENTIAL VARIABLES ---
    'spd':    {'colorscale': 'Turbo', 'cmin': 0, 'hide': False}, 
    'sfcspd': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False}, 
    'rr':     {'colorscale': 'Blues', 'cmin': 0, 'hide': False}, 
    'q':      {'colorscale': 'YlGnBu', 'cmin': 0, 'hide': False}, 
    't':      {'colorscale': 'Plasma', 'hide': False},           
    'p':      {'colorscale': 'Viridis_r', 'hide': False, 'is_coord': True},        
    'sfcp':   {'colorscale': 'Viridis_r', 'hide': False, 'is_coord': True},        
    'sfcdir': {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False},
    'wspd_hz_comp': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_derived': True},
    'wspd_3d_comp': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_derived': True},
    'wind_vec_hz':  {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_vector': True},
    'wind_vec_3d':  {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_vector': True},
    
    # --- VERTICAL MEASUREMENTS (Now Plottable) ---
    'ght':      {'colorscale': 'Earth', 'hide': False, 'is_coord': True},
    'elev':     {'colorscale': 'Earth', 'hide': False, 'is_coord': True},
    'height':   {'colorscale': 'Earth', 'hide': False, 'is_coord': True},
    'altitude': {'colorscale': 'Earth', 'hide': False, 'is_coord': True}
}

# --- AUTOMATIC UNIT CONVERSIONS ---
UNIT_CONVERSIONS = {
    'Pa': {'multiplier': 0.01, 'new_unit': 'hPa'},
    'Pascals': {'multiplier': 0.01, 'new_unit': 'hPa'},
    'kg/kg': {'multiplier': 1000.0, 'new_unit': 'g/kg'},
    'kg kg-1': {'multiplier': 1000.0, 'new_unit': 'g/kg'},
    'kg kg**-1': {'multiplier': 1000.0, 'new_unit': 'g/kg'}
}

# --- CONSTANTS ---
MS_TO_KTS = 1.94384

# --- USER INTERFACE DEFAULTS ---
DEFAULT_HIST_BINS = 50

# --- SUMMARY PLOT BOUNDARIES ---
# Fixed domain for the summary map matching manuscript bounds
DOMAIN_LAT_MIN = 10.0
DOMAIN_LAT_MAX = 50.0
DOMAIN_LON_MIN = -120.0
DOMAIN_LON_MAX = -20.0

# ---------------------------------------------------------------------
# GLOBAL CATEGORY & PLATFORM STYLING
# ---------------------------------------------------------------------

# Colors matched to manuscript with enhanced contrast for lighter variants
CAT_COLORS = {
    'H5': '#ef3d25',      
    'H4': '#fcae91',      
    'H3': '#fee609',      
    'H2': '#fff599',      
    'H1': '#11aa4b',      
    'TS': '#7be09b',      
    'TD': '#42c7f4',      
    'SS': '#ffffff',      
    'LO': '#d3d3d3',      
    'EX': '#eec1db',      
    'Unknown': '#ffffff'  
}

CAT_ORDER = ['SS', 'LO', 'TD', 'TS', 'H1', 'H2', 'H3', 'H4', 'H5', 'EX', 'Unknown']

PLATFORM_COLORS = {
    'NOAA P-3': 'navy',
    'NOAA G-IV': '#66FF66',
    'Air Force': '#B0B0B0',
    'NASA Global Hawk': 'darkred',
    'Tracks': '#FFFF99'
}
