# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import h5py
import tempfile
import os
import re
import json
import math
from datetime import datetime, timezone
import streamlit as st
from config import (
    EXPECTED_GROUPS, UNIT_CONVERSIONS, EARTH_R_KM, DEFAULT_SFMR_ALTITUDE,
    GLOBAL_LAT_MIN, GLOBAL_LAT_MAX, GLOBAL_LON_MIN, GLOBAL_LON_MAX
)

def decode_metadata(val):
    """
    Cleans up byte strings, null-padded strings, or arrays from HDF5 metadata.
    """
    # --- V11 FIX: Properly join multi-item lists instead of just taking index 0 ---
    if isinstance(val, (np.ndarray, list)):
        if len(val) == 0:
            return ""
        if len(val) > 1:
            parts = []
            for elem in val:
                if isinstance(elem, (bytes, np.bytes_)):
                    parts.append(elem.decode('utf-8', errors='ignore').rstrip('\x00').strip())
                else:
                    parts.append(str(elem).strip())
            return ", ".join(p for p in parts if p)
        # If it's just a single-element array, extract it and process normally
        val = val[0]
    # ------------------------------------------------------------------------------

    if isinstance(val, (bytes, np.bytes_, bytearray)):
        try:
            val = val.decode('utf-8') if not isinstance(val, bytearray) else val.decode('utf-8')
        except:
            val = str(val)
    result = str(val).strip()
    
    result = result.rstrip('\x00').strip()
    if result.startswith("b'") and result.endswith("'"):
        result = result[2:-1]
    elif result.startswith('b"') and result.endswith('"'):
        result = result[2:-1]
    return result

def get_cf_epoch_offset(time_unit_str):
    """
    Parses a CF-compliant time unit string and returns the offset from Unix 1970 in seconds.
    """
    if not isinstance(time_unit_str, str): return 0.0
    
    match = re.search(r'since\s+(\d{4}-\d{2}-\d{2})', time_unit_str.lower())
    if match:
        try:
            origin_dt = datetime.strptime(match.group(1), '%Y-%m-%d').replace(tzinfo=timezone.utc)
            unix_epoch_dt = datetime(1970, 1, 1, tzinfo=timezone.utc)
            return (unix_epoch_dt - origin_dt).total_seconds()
        except ValueError:
            pass
    return 0.0

def get_basin_from_filename(filename):
    """
    Extracts the basin code dynamically from the filename prefix.
    """
    if not isinstance(filename, str): return "Unknown"
    prefix = filename.split('.')[0]
    if not prefix: return "Unknown"
    last_char = prefix[-1].upper()
    if last_char == 'L': return "North Atlantic"
    elif last_char == 'E': return "Eastern Pacific"
    elif last_char == 'C': return "Central Pacific"
    else: return "Unknown"

@st.cache_data
def load_inventory_db(db_path):
    """
    Loads and standardizes the global dataset CSV inventory.
    """
    if not os.path.exists(db_path):
        return None
        
    df = pd.read_csv(db_path)
    
    for col in ['Lat', 'Lon', 'Intensity_ms', 'MSLP_hPa']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(r'[\[\]]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'MSLP_hPa' in df.columns:
        df.loc[df['MSLP_hPa'] > 2000, 'MSLP_hPa'] /= 100.0
            
    df['TC_Category'] = df['TC_Category'].fillna("Unknown").astype(str).str.replace(r'[\[\]\'"]', '', regex=True)
    df['TC_Category'] = df['TC_Category'].replace('NaN', 'Unknown')
    
    df['Basin'] = df['Filename'].apply(get_basin_from_filename)
    df['Constructed_File_Name'] = df['Filename']
    
    extracted = df['Filename'].str.extract(r'[_\.](?P<Year>\d{4})(?P<Cycle>\d{6})')
    df['Year'] = extracted['Year']
    df['Cycle_Raw'] = extracted['Cycle']
    df['Cycle_Display'] = df['Cycle_Raw'].str[-6:-4] + '/' + df['Cycle_Raw'].str[-4:-2] + '\xa0' + df['Cycle_Raw'].str[-2:] + 'Z'
    
    def parse_counts(x):
        try: return json.loads(x)
        except: return {}
    
    counts_df = pd.json_normalize(df['Group_Counts_JSON'].apply(parse_counts))
    df = pd.concat([df.drop(columns=['Group_Counts_JSON']), counts_df], axis=1)
    
    for g in EXPECTED_GROUPS:
        if g not in df.columns: df[g] = np.nan
    
    return df

@st.cache_data
def load_data_from_h5(file_bytes):
    """
    Loads HDF5 file contents from memory, parses datasets, attributes, 
    and metadata, and returns a standardized data package.
    """
    def _safe_val(val):
        try:
            # --- V11 FIX: Handle multi-item arrays in HDF5 extraction ---
            if hasattr(val, '__len__') and not isinstance(val, (str, bytes)):
                if len(val) == 0:
                    return ""
                if len(val) > 1:
                    parts = []
                    for elem in val:
                        if isinstance(elem, (bytes, bytearray, np.bytes_)):
                            parts.append(elem.decode('utf-8', errors='replace').rstrip('\x00').strip())
                        else:
                            parts.append(str(elem).strip())
                    return ", ".join(parts)
                # If length is exactly 1, extract it safely
                val = val.flat[0] if hasattr(val, 'flat') else val[0]
            # ------------------------------------------------------------
            
            if isinstance(val, (bytes, bytearray)):
                val = val.decode('utf-8', errors='replace').rstrip('\x00').strip()
            elif isinstance(val, np.bytes_):
                val = val.tobytes().decode('utf-8', errors='replace').rstrip('\x00').strip()
            return str(val)
        except:
            return str(val)

    def _safe_float(val):
        try: return float(_safe_val(val))
        except: return None
        
    def _find_center_in_attrs(attrs):
        """Calculates the storm center purely from the geospatial bounding box midpoint."""
        try:
            attr_map = {k.lower(): k for k in attrs.keys()}
            def get_bound(key_name):
                if key_name in attr_map: return _safe_float(attrs[attr_map[key_name]])
                return None
                
            lat_min = get_bound('geospatial_lat_min')
            lat_max = get_bound('geospatial_lat_max')
            lon_min = get_bound('geospatial_lon_min')
            lon_max = get_bound('geospatial_lon_max')
            
            if all(v is not None for v in [lat_min, lat_max, lon_min, lon_max]):
                lat_avg = (lat_min + lat_max) / 2.0
                lon_avg = (lon_min + lon_max) / 2.0
                if lon_avg > 180: lon_avg -= 360
                
                if GLOBAL_LAT_MIN <= lat_avg <= GLOBAL_LAT_MAX and GLOBAL_LON_MIN <= lon_avg <= GLOBAL_LON_MAX:
                    return lat_avg, lon_avg
        except Exception:
            pass
        return None

    with tempfile.NamedTemporaryFile(delete=False, suffix='.hdf5') as tmp_file:
        tmp_file.write(file_bytes)
        temp_file_path = tmp_file.name

    try:
        f = h5py.File(temp_file_path, 'r')
    except Exception as e:
        os.remove(temp_file_path)
        raise e

    data_dict, track_df = {}, pd.DataFrame()
    var_attrs = {} 
    
    metadata = {'storm_center': None, 'bounds': [], 'info': {}}

    for k, v in f.attrs.items():
        metadata['info'][k] = _safe_val(v)
        
    metadata['storm_center'] = _find_center_in_attrs(f.attrs)

    for key in f.keys():
        group = f[key]
        if not isinstance(group, h5py.Group): continue
        
        group_data = {}
        group_var_attrs = {}
        
        for dset in group.keys():
            if isinstance(group[dset], h5py.Dataset):
                arr = group[dset][:]
                if arr.ndim == 1: group_data[dset] = arr
                elif arr.ndim == 2 and arr.shape[1] == 1: group_data[dset] = arr.flatten()
                
                d_attrs = {}
                for attr_name, attr_val in group[dset].attrs.items():
                    d_attrs[attr_name] = _safe_val(attr_val)
                group_var_attrs[dset] = d_attrs
        
        if group_data:
            df = pd.DataFrame(group_data)
            rename_map = {}
            for c in df.columns:
                if c.lower() in ['lat', 'latitude', 'ilat', 'clat']: rename_map[c] = 'lat'
                if c.lower() in ['lon', 'longitude', 'ilon', 'clon']: rename_map[c] = 'lon'
            if rename_map: df.rename(columns=rename_map, inplace=True)

            for dset in df.columns:
                if dset in group_var_attrs:
                    u_raw = group_var_attrs[dset].get('units', '')
                    u_str = _safe_val(u_raw).strip().lower()
                    for target_unit, rule in UNIT_CONVERSIONS.items():
                        if u_str == target_unit.lower():
                            df[dset] = df[dset] * rule['multiplier']
                            group_var_attrs[dset]['units'] = rule['new_unit']
                            break
            
            if 'track' in key.lower():
                track_df = df
                data_dict[key] = df
                var_attrs[key] = group_var_attrs
                if not metadata['storm_center'] and 'lat' in df.columns:
                     mid = len(df) // 2
                     metadata['storm_center'] = (df.iloc[mid]['lat'], df.iloc[mid]['lon'])
            else:
                data_dict[key] = df
                var_attrs[key] = group_var_attrs

    f.close()
    os.remove(temp_file_path)

    if metadata['storm_center']:
        clat, clon = metadata['storm_center']
        metadata['bounds'] = [clon-3.0, clon+3.0, clat-3.0, clat+3.0]

    # Dynamically determine the time offset for this file
    metadata['time_offset_seconds'] = 0.0
    for grp_attrs in var_attrs.values():
        for var_name, attrs in grp_attrs.items():
            if var_name.lower() == 'time' and 'units' in attrs:
                metadata['time_offset_seconds'] = get_cf_epoch_offset(attrs['units'])
                break
        if metadata['time_offset_seconds'] != 0.0:
            break
        
    return {'data': data_dict, 'track': track_df, 'meta': metadata, 'var_attrs': var_attrs}

def inject_derived_fields(raw_data_pack):
    """
    Post-load enrichment: adds SFMR altitude, derived wind speeds,
    propagated error estimates, vector dummy variables, and distance
    from storm center in-place.
    """
    def _find_track_grp(data):
        for pref in ('track_spline_track', 'track_best_track'):
            if pref in data: return pref
        for k in data:
            if k.startswith('track_'): return k
        return None

    offset = raw_data_pack['meta'].get('time_offset_seconds', 0.0)
    def _ts(v):
        try:
            if pd.isna(v): return np.nan
            if v > 1.9e13:
                dt = datetime.strptime(f"{v:.0f}", '%Y%m%d%H%M%S')
                return dt.replace(tzinfo=timezone.utc).timestamp()
            # Dynamic CF subtraction!
            return float(v) - offset
        except Exception:
            return np.nan

    track_grp_name = _find_track_grp(raw_data_pack['data'])
    track_epochs = track_lats = track_lons = None

    if track_grp_name is not None:
        tr = raw_data_pack['data'][track_grp_name]
        tcols = {c.lower(): c for c in tr.columns}
        t_col   = tcols.get('time')
        lat_col = next((tcols[c] for c in ['lat', 'latitude', 'clat'] if c in tcols), None)
        lon_col = next((tcols[c] for c in ['lon', 'longitude', 'clon'] if c in tcols), None)
        if all([t_col, lat_col, lon_col]):
            te = np.array([_ts(v) for v in tr[t_col].values])
            valid_te = np.isfinite(te)
            if valid_te.sum() >= 2:   
                order = np.argsort(te[valid_te])
                track_epochs = te[valid_te][order]
                track_lats   = tr[lat_col].values.astype(float)[valid_te][order]
                track_lons   = tr[lon_col].values.astype(float)[valid_te][order]

    for grp in raw_data_pack['data'].keys():
        df_grp = raw_data_pack['data'][grp]
        if grp not in raw_data_pack['var_attrs']:
            raw_data_pack['var_attrs'][grp] = {}

        if (track_epochs is not None and not grp.startswith('track_')):
            gcols = {c.lower(): c for c in df_grp.columns}
            lat_c  = next((gcols[c] for c in ['lat', 'latitude']  if c in gcols), None)
            lon_c  = next((gcols[c] for c in ['lon', 'longitude'] if c in gcols), None)
            time_c = gcols.get('time')
            if lat_c and lon_c and time_c:
                obs_epochs = np.array([_ts(v) for v in df_grp[time_c].values])
                cen_lats = np.interp(obs_epochs, track_epochs, track_lats)
                cen_lons = np.interp(obs_epochs, track_epochs, track_lons)
                dlat     = np.radians(df_grp[lat_c].values.astype(float) - cen_lats)
                dlon     = np.radians(df_grp[lon_c].values.astype(float) - cen_lons)
                mean_lat = np.radians((df_grp[lat_c].values.astype(float) + cen_lats) / 2.0)
                x_km = EARTH_R_KM * dlon * np.cos(mean_lat)
                y_km = EARTH_R_KM * dlat
                dist = np.sqrt(x_km**2 + y_km**2)
                nan_mask = (~np.isfinite(obs_epochs) | df_grp[lat_c].isna().values | df_grp[lon_c].isna().values)
                dist[nan_mask] = np.nan
                df_grp['dist_from_center'] = dist
                raw_data_pack['var_attrs'][grp]['dist_from_center'] = {
                    'units': 'km', 'long_name': 'Distance from Storm Center (Computed)',
                }

        if 'sfmr' in grp.lower():
            df_grp['altitude'] = DEFAULT_SFMR_ALTITUDE
            raw_data_pack['var_attrs'][grp]['altitude'] = {
                'units': 'm', 'long_name': 'Assumed Observation Height'
            }

        cols_lower = {c.lower(): c for c in df_grp.columns}
        has_u = 'u' in cols_lower
        has_v = 'v' in cols_lower
        has_w = 'w' in cols_lower

        def get_err_col(var_name):
            cands = [f"{var_name}err", f"{var_name}_err", f"{var_name}_error", f"{var_name}error"]
            return next((cols_lower[c] for c in cands if c in cols_lower), None)

        if not (has_u and has_v):
            continue

        u_c, v_c     = cols_lower['u'], cols_lower['v']
        u_vals       = df_grp[u_c]
        v_vals       = df_grp[v_c]
        u_units      = raw_data_pack['var_attrs'][grp].get(u_c, {}).get('units', 'm/s')
        u_err_c      = get_err_col('u')
        v_err_c      = get_err_col('v')

        wspd_hz = np.sqrt(u_vals**2 + v_vals**2)
        df_grp['wspd_hz_comp'] = wspd_hz
        raw_data_pack['var_attrs'][grp]['wspd_hz_comp'] = {
            'units': u_units, 'long_name': 'Horizontal Wind Speed (Computed)'
        }

        if u_err_c and v_err_c:
            u_err_vals = df_grp[u_err_c]
            v_err_vals = df_grp[v_err_c]
            u_err_const = np.isclose(np.nanmin(u_err_vals), np.nanmax(u_err_vals))
            v_err_const = np.isclose(np.nanmin(v_err_vals), np.nanmax(v_err_vals))
            if u_err_const and v_err_const:
                hz_err      = np.sqrt(u_err_vals**2 + v_err_vals**2)
                hz_err_name = 'Horizontal Wind Speed Error (Static Computed)'
            else:
                hz_err = np.where(wspd_hz > 0, np.sqrt((u_vals * u_err_vals)**2 + (v_vals * v_err_vals)**2) / wspd_hz, 0.0)
                hz_err_name = 'Horizontal Wind Speed Error (Dynamic Computed)'
            df_grp['wspd_hz_comp_err'] = hz_err
            raw_data_pack['var_attrs'][grp]['wspd_hz_comp_err'] = {
                'units': u_units, 'long_name': hz_err_name
            }

        df_grp['wind_vec_hz'] = wspd_hz
        raw_data_pack['var_attrs'][grp]['wind_vec_hz'] = {
            'units': u_units, 'long_name': 'Horizontal Wind Vectors'
        }

        if not has_w: continue

        w_c    = cols_lower['w']
        w_vals = df_grp[w_c]

        wspd_3d = np.sqrt(u_vals**2 + v_vals**2 + w_vals**2)
        df_grp['wspd_3d_comp'] = wspd_3d
        raw_data_pack['var_attrs'][grp]['wspd_3d_comp'] = {
            'units': u_units, 'long_name': '3D Wind Speed (Computed)'
        }

        w_err_c = get_err_col('w')
        if u_err_c and v_err_c and w_err_c:
            u_err_vals = df_grp[u_err_c]
            v_err_vals = df_grp[v_err_c]
            w_err_vals = df_grp[w_err_c]
            u_err_const = np.isclose(np.nanmin(u_err_vals), np.nanmax(u_err_vals))
            v_err_const = np.isclose(np.nanmin(v_err_vals), np.nanmax(v_err_vals))
            w_err_const = np.isclose(np.nanmin(w_err_vals), np.nanmax(w_err_vals))
            if u_err_const and v_err_const and w_err_const:
                err_3d      = np.sqrt(u_err_vals**2 + v_err_vals**2 + w_err_vals**2)
                err_3d_name = '3D Wind Speed Error (Static Computed)'
            else:
                err_3d = np.where(wspd_3d > 0, np.sqrt((u_vals * u_err_vals)**2 + (v_vals * v_err_vals)**2 + (w_vals * w_err_vals)**2) / wspd_3d, 0.0)
                err_3d_name = '3D Wind Speed Error (Dynamic Computed)'
            df_grp['wspd_3d_comp_err'] = err_3d
            raw_data_pack['var_attrs'][grp]['wspd_3d_comp_err'] = {
                'units': u_units, 'long_name': err_3d_name
            }

        df_grp['wind_vec_3d'] = wspd_3d
        raw_data_pack['var_attrs'][grp]['wind_vec_3d'] = {
            'units': u_units, 'long_name': '3D Wind Vectors'
        }

def compute_global_domain(data_pack):
    """
    Scans all groups for lat/lon and stores a tight square bounding box
    in data_pack['global_domain']. Called at file load; also safe to call
    lazily if missing.
    """
    all_lats, all_lons = [], []
    for grp, df in data_pack['data'].items():
        if df is None or df.empty:
            continue
        cl = {c.lower(): c for c in df.columns}
        x_c = next((cl[c] for c in ['lon', 'longitude', 'clon'] if c in cl), None)
        y_c = next((cl[c] for c in ['lat', 'latitude',  'clat'] if c in cl), None)
        if x_c and y_c:
            lons = df[x_c].dropna().values
            lats = df[y_c].dropna().values
            if len(lons): all_lons.extend(lons.tolist())
            if len(lats): all_lats.extend(lats.tolist())

    if not all_lats or not all_lons:
        data_pack['global_domain'] = None
        return

    span_lat = max(float(np.max(all_lats)) - float(np.min(all_lats)), 0.05)
    span_lon = max(float(np.max(all_lons)) - float(np.min(all_lons)), 0.05)
    buf_lat  = span_lat * 0.05
    buf_lon  = span_lon * 0.05
    lat_min  = float(np.min(all_lats)) - buf_lat
    lat_max  = float(np.max(all_lats)) + buf_lat
    lon_min  = float(np.min(all_lons)) - buf_lon
    lon_max  = float(np.max(all_lons)) + buf_lon
    lat_span = lat_max - lat_min
    lon_span = lon_max - lon_min
    if lat_span > lon_span:
        extra = (lat_span - lon_span) / 2
        lon_min -= extra; lon_max += extra
    else:
        extra = (lon_span - lat_span) / 2
        lat_min -= extra; lat_max += extra

    data_pack['global_domain'] = {
        'lat_min': round(lat_min, 2), 'lat_max': round(lat_max, 2),
        'lon_min': round(lon_min, 2), 'lon_max': round(lon_max, 2),
    }

def compute_vert_bounds(data_pack):
    """
    Pre-computes vertical (height/pressure) slider bounds for every group and column.
    Stores the results in data_pack['vert_bounds'].
    """
    bounds = {}
    for grp, df in data_pack['data'].items():
        if df is None or df.empty:
            continue
        cl = {c.lower(): c for c in df.columns}
        grp_bounds = {}
        vert_keys = ['height', 'ght', 'altitude', 'elev', 'pres', 'pressure', 'p']
        for key in vert_keys:
            if key not in cl:
                continue
            col = cl[key]
            is_pres = key in ['pres', 'pressure', 'p']
            raw = df[col].dropna().values
            if len(raw) == 0:
                continue
            unit = decode_metadata(
                data_pack['var_attrs'].get(grp, {}).get(col, {}).get('units', '')
            )
            convert = 'Pa' in unit and 'hPa' not in unit
            vals = raw / 100.0 if convert else raw.copy()
            display_unit = 'hPa' if convert else unit

            if is_pres or convert:
                zmin = float(max(0.0, math.floor(np.nanmin(vals) / 50.0) * 50.0))
                raw_max = float(np.nanmax(vals))
                zmax = float(math.ceil(raw_max / 5.0) * 5.0 + 5.0)
                zmax = max(zmax, zmin + 50.0)
                step = 5.0
            else:
                zmin = 0.0
                zmax = float(math.ceil(np.nanmax(vals) / 1000.0) * 1000.0)
                if zmax == 0.0:
                    zmax = 1000.0
                step = 10.0

            if zmin >= zmax:
                zmax = zmin + step

            grp_bounds[col] = (zmin, zmax, is_pres or convert, display_unit, step)
        if grp_bounds:
            bounds[grp] = grp_bounds
    data_pack['vert_bounds'] = bounds
    