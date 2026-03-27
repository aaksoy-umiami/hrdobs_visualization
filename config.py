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

AVAILABLE_COLORSCALES = [
    'Blues', 'Earth', 'hsv', 'Jet', 'Plasma', 
    'PuOr_r', 'RdBu_r', 'Turbo', 'Viridis', 'Viridis_r', 'YlGnBu'
]

# --- USER-FRIENDLY COLORSCALE NAMES ---
COLORSCALE_NAMES = {
    'Blues': 'Blues (Sequential)',
    'Earth': 'Earth (Terrain/Elevation)',
    'hsv': 'HSV (Directional/Circular)',
    'Jet': 'Jet (Classic Rainbow)',
    'Plasma': 'Plasma (Perceptually Uniform)',
    'PuOr_r': 'Purple-Orange (Diverging)',
    'RdBu_r': 'Red-Blue (Diverging)',
    'Turbo': 'Turbo (Smooth Rainbow)',
    'Viridis': 'Viridis (Default Uniform)',
    'Viridis_r': 'Viridis Reversed',
    'YlGnBu': 'Yellow-Green-Blue (Sequential)'
}

GLOBAL_VAR_CONFIG = {
    # --- NON-PLOTTABLE COORDINATES & METADATA (Hidden) ---
    'lat': {'hide': True, 'is_coord': True}, 
    'lon': {'hide': True, 'is_coord': True}, 
    'latitude': {'hide': True, 'is_coord': True}, 
    'longitude': {'hide': True, 'is_coord': True}, 
    'time': {'hide': False, 'is_coord': True},
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
    
    # --- DERIVED SPATIAL COORDINATES ---
    'dist_from_center': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False,
                         'is_derived': True, 'is_coord': True, 'sort_weight': 100,
                         'display_name': 'Distance from Storm Center (km)'},
    'azimuth_north':    {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False,
                         'is_derived': True, 'is_coord': True, 'sort_weight': 101,
                         'display_name': 'Azimuth from North (Computed) (deg)'},
    'azimuth_motion':   {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False,
                         'is_derived': True, 'is_coord': True, 'sort_weight': 102,
                         'display_name': 'Azimuth from Storm Motion (Computed) (deg)'},
    
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

# --- MATH & PHYSICS CONSTANTS ---
MS_TO_KTS = 1.94384
EARTH_R_KM = 6371.0
SURFACE_PRESSURE_HPA = 1013.25
DEFAULT_SFMR_ALTITUDE = 10.0

# --- GEOGRAPHIC DEFAULTS ---
GLOBAL_LAT_MIN = -90.0
GLOBAL_LAT_MAX = 90.0
GLOBAL_LON_MIN = -180.0
GLOBAL_LON_MAX = 180.0
FALLBACK_STORM_CENTER_LAT = 20.0
FALLBACK_STORM_CENTER_LON = -50.0

# --- USER INTERFACE & PLOT DEFAULTS ---
DEFAULT_HIST_BINS = 10
DEFAULT_HIST_BINS_AZIMUTH = 8
DEFAULT_HIST_BINS_RADIAL = 10

DEFAULT_INTENSITY_MIN = 0.0
DEFAULT_INTENSITY_MAX = 100.0
DEFAULT_MSLP_MIN = 900.0
DEFAULT_MSLP_MAX = 1020.0
DEFAULT_SR_MAX_RANGE = 500.0
SR_RING_CANDIDATES = [1, 2, 5, 10, 25, 50, 100, 150, 200, 250, 500]
RH_RING_CANDIDATES = [10, 25, 50, 100, 150, 200, 250, 500]
DEFAULT_MAX_HEIGHT_M = 15000.0
DEFAULT_MAX_PRESSURE_HPA = 1015.0

# --- SUMMARY PLOT BOUNDARIES ---
DOMAIN_LAT_MIN = 10.0
DOMAIN_LAT_MAX = 50.0
DOMAIN_LON_MIN = -120.0
DOMAIN_LON_MAX = -20.0

# ---------------------------------------------------------------------
# GLOBAL CATEGORY & PLATFORM STYLING
# ---------------------------------------------------------------------

CAT_COLORS = {
    'WV': '#e0e0e0',      
    'DB': '#b0b0b0',      
    'TD': '#42c7f4',      
    'TS': '#7be09b',      
    'H1': '#11aa4b',      
    'H2': '#fff599',      
    'H3': '#fee609',      
    'H4': '#fcae91',      
    'H5': '#ef3d25',      
    'EX': '#eec1db',      
    'LO': '#fce4f0',      
    'SS': '#ffffff',      
    'Unknown': '#ffffff'  
}

CAT_ORDER = ['WV', 'DB', 'TD', 'TS', 'H1', 'H2', 'H3', 'H4', 'H5', 'EX', 'LO', 'SS', 'Unknown']

CAT_FULL_NAMES = {
    'WV': 'Tropical Wave',
    'DB': 'Disturbance',
    'TD': 'Tropical Depression',
    'TS': 'Tropical Storm',
    'H1': 'Hurricane Cat 1',
    'H2': 'Hurricane Cat 2',
    'H3': 'Hurricane Cat 3',
    'H4': 'Hurricane Cat 4',
    'H5': 'Hurricane Cat 5',
    'EX': 'Extratropical',
    'LO': 'Remnant Low',
    'SS': 'Subtropical Storm',
    'Unknown': 'Unknown',
}

PLATFORM_COLORS = {
    'NOAA P-3': 'navy',
    'NOAA G-IV': '#66FF66',
    'Air Force': '#B0B0B0',
    'NASA Global Hawk': 'darkred',
    'Tracks': '#FFFF99'
}
