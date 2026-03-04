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
    'lat': {'hide': True}, 'lon': {'hide': True}, 'time': {'hide': True},
    'clat': {'hide': True}, 'clon': {'hide': True}, 'ght': {'hide': True},
    'elev': {'hide': True}, 'az': {'hide': True}, 'rmw': {'hide': True},
    'pmin': {'hide': True}, 'vmax': {'hide': True}, 
    'qerr': {'hide': True}, 'spderr': {'hide': True},
    'rvel': {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False}, 
    'w':    {'colorscale': 'PuOr_r', 'cmid': 0, 'hide': False}, 
    'u':    {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False}, 
    'v':    {'colorscale': 'RdBu_r', 'cmid': 0, 'hide': False}, 
    'spd':    {'colorscale': 'Turbo', 'cmin': 0, 'hide': False}, 
    'sfcspd': {'colorscale': 'Turbo', 'cmin': 0, 'hide': False}, 
    'rr':     {'colorscale': 'Blues', 'cmin': 0, 'hide': False}, 
    'q':      {'colorscale': 'YlGnBu', 'cmin': 0, 'hide': False}, 
    't':      {'colorscale': 'Plasma', 'hide': False},           
    'p':      {'colorscale': 'Viridis_r', 'hide': False},        
    'sfcp':   {'colorscale': 'Viridis_r', 'hide': False},        
    'sfcdir': {'colorscale': 'hsv', 'cmin': 0, 'cmax': 360, 'hide': False} 
}
