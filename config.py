# -*- coding: utf-8 -*-

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
    'lat': {'hide': True, 'is_coord': True}, 'lon': {'hide': True, 'is_coord': True}, 'time': {'hide': True, 'is_coord': True},
    'clat': {'hide': True, 'is_coord': True}, 'clon': {'hide': True, 'is_coord': True}, 
    'az': {'hide': True, 'is_coord': True}, 'rmw': {'hide': True, 'is_coord': True},
    'pmin': {'hide': True}, 'vmax': {'hide': True}, 
    'qerr': {'hide': True}, 'spderr': {'hide': True},

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
# The data loader will intercept these units, multiply the data by the factor,
# and overwrite the unit string so the rest of the app displays it correctly.
UNIT_CONVERSIONS = {
    'Pa': {'multiplier': 0.01, 'new_unit': 'hPa'},
    'Pascals': {'multiplier': 0.01, 'new_unit': 'hPa'},
    'kg/kg': {'multiplier': 1000.0, 'new_unit': 'g/kg'},
    'kg kg-1': {'multiplier': 1000.0, 'new_unit': 'g/kg'},
    'kg kg**-1': {'multiplier': 1000.0, 'new_unit': 'g/kg'}
}

# --- USER INTERFACE DEFAULTS ---
DEFAULT_HIST_BINS = 50
