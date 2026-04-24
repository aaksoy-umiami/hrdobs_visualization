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
    "ships_params",
    "track_best_track", "track_spline_track", "track_vortex_message"
]

EXPECTED_META = [
    "center_from_tc_vitals", 
    "creator_email", 
    "creator_name",
    "existing_groups", 
    "expected_groups",
    "geospatial_lat_max", 
    "geospatial_lat_min", 
    "geospatial_lat_units",
    "geospatial_lon_max", 
    "geospatial_lon_min", 
    "geospatial_lon_units",
    "radius_of_maximum_wind_km", 
    "storm_datetime", 
    "storm_epoch", 
    "storm_id",
    "storm_intensity_ms", 
    "storm_motion_heading_deg", 
    "storm_motion_speed_kt",
    "storm_mslp_hpa", 
    "storm_name", 
    "tc_category",
    "time_coverage_end", 
    "time_coverage_start", 
    "title", 
    "version_number",
    "Virtual_Manifest"
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
    'u': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Zonal Wind Component (m/s)', 'sort_order': 1},
    'v': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Meridional Wind Component (m/s)', 'sort_order': 2},
    'w': {'colorscale': 'PuOr_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Vertical Wind Component (m/s)', 'sort_order': 3},
    't': {'colorscale': 'Plasma', 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Temperature (deg C)', 'sort_order': 4},
    'q': {'colorscale': 'YlGnBu', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Specific Humidity (g/kg)', 'sort_order': 5},
    'spd': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Wind Speed (m/s)', 'sort_order': 6},
    'sfcspd': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Surface Wind Speed (m/s)', 'sort_order': 7},
    'sfcdir': {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Surface Wind Direction (deg)', 'sort_order': 8},
    'rr': {'colorscale': 'Blues', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Rain Rate (mm/h)', 'sort_order': 9},
    'rvel': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Radial Velocity (m/s)', 'sort_order': 10},
    'pmin': {'colorscale': 'Viridis_r', 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Min Pressure (hPa)', 'sort_order': 11},
    'vmax': {'colorscale': 'Turbo', 'hide': False, 'cmin': 0, 'is_coord': False, 'is_derived': False, 'display_name': 'Max Wind (m/s)', 'sort_order': 12},
    'uerr': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Zonal Wind Observation Error (m/s)', 'sort_order': 13},
    'verr': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Meridional Wind Observation Error (m/s)', 'sort_order': 14},
    'werr': {'colorscale': 'PuOr_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Vertical Wind Observation Error (m/s)', 'sort_order': 15},
    'terr': {'colorscale': 'Plasma', 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Temperature Error (deg C)', 'sort_order': 16},
    'qerr': {'colorscale': 'YlGnBu', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Specific Humidity Observation Error (g/kg)', 'sort_order': 17},
    'perr': {'colorscale': 'Viridis_r', 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Pressure Observation Error (hPa)', 'sort_order': 18},
    'spderr': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Wind Speed Observation Error (m/s)', 'sort_order': 19},
    'rvelerr': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False, 'is_coord': False, 'is_derived': False, 'display_name': 'Radial Velocity Observation Error (m/s)', 'sort_order': 20},

    # --- TIER 1: DERIVED VARIABLES (is_derived=True, is_coord=False) ---
    'wspd_hz_comp': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': True, 'display_name': 'Horizontal Wind Speed (Computed) (m/s)', 'sort_order': 1},
    'wspd_3d_comp': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_coord': False, 'is_derived': True, 'display_name': '3D Wind Speed (Computed) (m/s)', 'sort_order': 2},
    'wind_vec_hz': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_vector': True, 'is_coord': False, 'is_derived': True, 'display_name': 'Horizontal Wind Vector (m/s)', 'sort_order': 3},
    'wind_vec_3d': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'is_vector': True, 'is_coord': False, 'is_derived': True, 'display_name': '3D Wind Vector (m/s)', 'sort_order': 4},

    # --- TIER 2: STANDARD COORDINATES & METADATA (is_derived=False, is_coord=True) ---
    'lat': {'hide': True, 'is_coord': True, 'is_derived': False, 'display_name': 'Latitude (deg)', 'sort_order': 1},
    'latitude': {'hide': True, 'is_coord': True, 'is_derived': False, 'display_name': 'Latitude (deg)', 'sort_order': 2},
    'clat': {'hide': True, 'is_track_pos': True, 'is_coord': True, 'is_derived': False, 'display_name': 'Center Latitude (deg)', 'sort_order': 3},
    'lon': {'hide': True, 'is_coord': True, 'is_derived': False, 'display_name': 'Longitude (deg)', 'sort_order': 4},
    'longitude': {'hide': True, 'is_coord': True, 'is_derived': False, 'display_name': 'Longitude (deg)', 'sort_order': 5},
    'clon': {'hide': True, 'is_track_pos': True, 'is_coord': True, 'is_derived': False, 'display_name': 'Center Longitude (deg)', 'sort_order': 6},
    'az': {'hide': True, 'is_coord': True, 'is_derived': False, 'display_name': 'Radar Beam Azimuth Angle from North (deg)', 'sort_order': 7},
    'p': {'colorscale': 'Viridis_r', 'hide': False, 'is_coord': True, 'is_derived': False, 'display_name': 'Pressure (hPa)', 'sort_order': 8},
    'sfcp': {'colorscale': 'Viridis_r', 'hide': False, 'is_coord': True, 'is_derived': False, 'display_name': 'Surface Pressure (hPa)', 'sort_order': 9},
    'pres': {'colorscale': 'Viridis_r', 'hide': False, 'is_coord': True, 'is_derived': False, 'display_name': 'Flight-Level Pressure, Spline Track (hPa)', 'sort_order': 10},
    'ght': {'colorscale': 'Viridis', 'hide': False, 'is_coord': True, 'is_derived': False, 'display_name': 'Geopotential Height (m)', 'sort_order': 11},
    'height': {'colorscale': 'Viridis', 'hide': False, 'is_coord': True, 'is_derived': False, 'display_name': 'Height (m)', 'sort_order': 12},
    'altitude': {'colorscale': 'Viridis', 'hide': False, 'is_coord': True, 'is_derived': False, 'display_name': 'Altitude (m)', 'sort_order': 13},
    'elev': {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False, 'is_coord': True, 'is_derived': False, 'display_name': 'Radar Beam Elevation Angle from Nadir (deg)', 'sort_order': 13},
    'rmw': {'hide': True, 'is_coord': True, 'is_derived': False, 'display_name': 'Radius of Max Winds (km)', 'sort_order': 15},
    'time': {'colorscale': 'Plasma', 'hide': False, 'is_coord': True, 'is_derived': False, 'display_name': 'Time (UTC)', 'sort_order': 16},

    # --- TIER 3: DERIVED SPATIAL COORDINATES (is_derived=True, is_coord=True) ---
    'dist_from_center': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False, 'sort_weight': 100, 'is_coord': True, 'is_derived': True, 'display_name': 'Distance from Storm Center (km)', 'sort_order': 1},
    'azimuth_north': {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False, 'sort_weight': 101, 'is_coord': True, 'is_derived': True, 'display_name': 'Azimuth from North (Computed) (deg)', 'sort_order': 2},
    'azimuth_motion': {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False, 'sort_weight': 102, 'is_coord': True, 'is_derived': True, 'display_name': 'Azimuth from Storm Motion (Computed) (deg)', 'sort_order': 3},
    'azimuth_shear_deep': {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False, 'sort_weight': 103, 'is_coord': True, 'is_derived': True, 'display_name': 'Azimuth from 850-200 hPa Shear (Computed) (deg)', 'sort_order': 4},
    'azimuth_shear_vortex': {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False, 'sort_weight': 104, 'is_coord': True, 'is_derived': True, 'display_name': 'Azimuth from Vortex-Removed 850-200 hPa Shear (Computed) (deg)', 'sort_order': 5}
}

SHIPS_PREDICTOR_META = {
    'type':           ('intensity category', 'Storm type'),
    'incv_kt':        ('knot',               'Intensity change -6 to 0 hr'),
    'csst_degc':      ('deg C',              'Climatological SST along track'),
    'cd20_m':         ('m',                  'Climatological depth of 20 deg C isotherm'),
    'cd26_m':         ('m',                  'Climatological depth of 26 deg C isotherm'),
    'cohc_kjcm2':     ('kJ/cm^2',            'Climatological ocean heat content'),
    'dtl_km':         ('km',                 'Distance to nearest major land mass'),
    'oage_hr':        ('hr',                 'Ocean age'),
    'nage_hr':        ('hr',                 'Intensity-weighted ocean age'),
    'shrd_kt':        ('kt',                 '850-200 hPa shear magnitude'),
    'shtd_deg':       ('deg',                'Heading of 850-200 hPa shear vector'),
    'shdc_kt':        ('knot',               '850-200 hPa vortex-removed shear magnitude'),
    'sddc_deg':       ('deg',                'Heading of vortex-removed shear vector'),
    'rhlo_pct':       ('%',                  '850-700 hPa relative humidity'),
    'rhmd_pct':       ('%',                  '700-500 hPa relative humidity'),
    'rhhi_pct':       ('%',                  '500-300 hPa relative humidity'),
    'vmpi_kt':        ('kt',                 'Maximum potential intensity'),
    'penv_hpa':       ('hPa',                'Average environmental surface pressure'),
    'penc_hpa':       ('hPa',                'Outer vortex edge surface pressure'),
    'z850_1e7_per_s': ('1e-7 s^-1',          '850 hPa vorticity'),
    'd200_1e7_per_s': ('1e-7 s^-1',          '200 hPa divergence'),
    'u200_kt':        ('kt',                 '200 hPa zonal wind'),
    'dsst_degc':      ('deg C',              'Daily Reynolds SST along track'),
    'nsst_degc':      ('deg C',              'NCODA analysis SST'),
    'nohc_kjcm2':     ('kJ/cm^2',            'NCODA ocean heat content'),
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
