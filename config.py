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
    'Blues', 'Cividis', 'Earth', 'Greys', 'hsv', 'Inferno', 'Jet', 'Plasma', 
    'PuOr_r', 'RdBu_r', 'Turbo', 'Viridis', 'Viridis_r', 'YlGnBu'
]

# --- USER-FRIENDLY COLORSCALE NAMES ---
COLORSCALE_NAMES = {
    'Blues': 'Blues (Sequential)',
    'Cividis': 'Cividis (Colorblind Safe)',
    'Earth': 'Earth (Terrain/Elevation)',
    'Greys': 'Greys (Grayscale)',
    'hsv': 'HSV (Directional/Circular)',
    'Inferno': 'Inferno (Dark to Bright)',
    'Jet': 'Jet (Legacy Rainbow)',
    'Plasma': 'Plasma (Perceptually Uniform)',
    'PuOr_r': 'Purple-Orange (Diverging)',
    'RdBu_r': 'Red-Blue (Diverging)',
    'Turbo': 'Turbo (Modern Smooth Rainbow)',
    'Viridis': 'Viridis (Default Uniform)',
    'Viridis_r': 'Viridis Reversed',
    'YlGnBu': 'Yellow-Green-Blue (Sequential)'
}

GLOBAL_VAR_CONFIG = {
    # --- TIER 0: STANDARD VARIABLES (is_derived=False, is_coord=False) ---
    'u': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 1},
    'v': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 2},
    'w': {'colorscale': 'PuOr_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 3},
    't': {'colorscale': 'Plasma', 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order':4},
    'q': {'colorscale': 'YlGnBu', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 5},
    'spd': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 6},
    'sfcspd': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 7},
    'sfcdir': {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 8},
    'rr': {'colorscale': 'Blues', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 9},
    'rvel': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 10},
    'pmin': {'colorscale': 'Viridis_r', 'hide': False, 'display_name': 'Min Pressure (hPa)', 'is_coord': False, 'is_derived': False, 'sort_order': 11},
    'vmax': {'colorscale': 'Turbo', 'hide': False, 'cmin': 0, 'display_name': 'Max Wind (m/s)', 'is_coord': False, 'is_derived': False, 'sort_order': 12},
    'uerr': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 13},
    'verr': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 14},
    'werr': {'colorscale': 'PuOr_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 15},
    'terr': {'colorscale': 'Plasma', 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order':16},
    'qerr': {'colorscale': 'YlGnBu', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 17},
    'spderr': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 18},
    'rvelerr': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'sort_order': 19},

    # --- TIER 1: DERIVED VARIABLES (is_derived=True, is_coord=False) ---
    'wspd_hz_comp': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': True, 'sort_order': 1},
    'wspd_3d_comp': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': True, 'sort_order': 2},
    'wind_vec_hz': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_vector': True, 'is_coord': False, 'is_derived': True, 'sort_order': 3},
    'wind_vec_3d': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_vector': True, 'is_coord': False, 'is_derived': True, 'sort_order': 4},

    # --- TIER 2: STANDARD COORDINATES & METADATA (is_derived=False, is_coord=True) ---
    'lat': {'hide': True, 'is_coord': True, 'is_derived': False, 'sort_order': 1},
    'latitude': {'hide': True, 'is_coord': True, 'is_derived': False, 'sort_order': 2},
    'clat': {'hide': True, 'is_track_pos': True, 'is_coord': True, 'is_derived': False, 'sort_order': 3},
    'lon': {'hide': True, 'is_coord': True, 'is_derived': False, 'sort_order': 4},
    'longitude': {'hide': True, 'is_coord': True, 'is_derived': False, 'sort_order': 5},
    'clon': {'hide': True, 'is_track_pos': True, 'is_coord': True, 'is_derived': False, 'sort_order': 6},
    'az': {'hide': True, 'is_coord': True, 'is_derived': False, 'sort_order': 7},
    'p': {'colorscale': 'Viridis_r', 'hide': False, 'is_coord': True, 'is_derived': False, 'sort_order': 8},
    'sfcp': {'colorscale': 'Viridis_r', 'hide': False, 'is_coord': True, 'is_derived': False, 'sort_order': 9},
    'ght': {'colorscale': 'Earth', 'hide': False, 'is_coord': True, 'is_derived': False, 'sort_order': 10},
    'height': {'colorscale': 'Earth', 'hide': False, 'is_coord': True, 'is_derived': False, 'sort_order': 11},
    'altitude': {'colorscale': 'Earth', 'hide': False, 'is_coord': True, 'is_derived': False, 'sort_order': 12},
    'elev': {'colorscale': 'Earth', 'hide': False, 'is_coord': True, 'is_derived': False, 'sort_order': 13},
    'rmw': {'hide': True, 'is_coord': True, 'is_derived': False, 'sort_order': 14},
    'time': {'hide': False, 'is_coord': True, 'is_derived': False, 'sort_order': 15},

    # --- TIER 3: DERIVED SPATIAL COORDINATES (is_derived=True, is_coord=True) ---
    'dist_from_center': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'sort_weight': 100, 'display_name': 'Distance from Storm Center (km)', 'is_coord': True, 'is_derived': True, 'sort_order': 1},
    'azimuth_north': {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False, 'sort_weight': 101, 'display_name': 'Azimuth from North (Computed) (deg)', 'is_coord': True, 'is_derived': True, 'sort_order': 2},
    'azimuth_motion': {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False, 'sort_weight': 102, 'display_name': 'Azimuth from Storm Motion (Computed) (deg)', 'is_coord': True, 'is_derived': True, 'sort_order': 3}
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

# --- VECTOR RENDERING DEFAULTS ---
VEC_COLOR_BINS = 30
VEC_WING_ANGLE_DEG = 150
VEC_WING_LEN_FRAC = 0.3
VEC_WING_SPREAD_FRAC = 0.15

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
DOMAIN_LON_MIN = -100.0
DOMAIN_LON_MAX = -10.0

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
