# -*- coding: utf-8 -*-

import pandas as pd
import numpy as np
import h5py
import tempfile
import os
import re
import json
import streamlit as st
from config import EXPECTED_GROUPS

def decode_metadata(val):
    """
    Cleans up byte strings, null-padded strings, or arrays from HDF5 metadata.
    """
    if isinstance(val, (np.ndarray, list)) and len(val) > 0:
        val = val[0]
    if isinstance(val, (bytes, np.bytes_, bytearray)):
        try:
            val = val.decode('utf-8') if not isinstance(val, bytearray) else val.decode('utf-8')
        except:
            val = str(val)
    result = str(val).strip()
    
    # Remove null padding and strip any remaining b'...' wrapper artifacts
    result = result.rstrip('\x00').strip()
    if result.startswith("b'") and result.endswith("'"):
        result = result[2:-1]
    elif result.startswith('b"') and result.endswith('"'):
        result = result[2:-1]
    return result

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
            if hasattr(val, '__len__') and not isinstance(val, (str, bytes)):
                val = val.flat[0] if hasattr(val, 'flat') else val[0]
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
        if 'center_from_tc_vitals' in attrs:
            raw_val = attrs['center_from_tc_vitals']
            
            # Check if the value is a numeric array or list rather than a string
            if hasattr(raw_val, '__iter__') and not isinstance(raw_val, (str, bytes)):
                try:
                    return float(raw_val[0]), float(raw_val[1])
                except (ValueError, TypeError, IndexError):
                    pass
            
            val_str = _safe_val(raw_val).upper()
            
            # Attempt to parse as a stringified numeric vector or list (e.g., "[20.5, -60.2]")
            import re
            m = re.search(r'\[?\s*([-+]?\d*\.?\d+)[\s,]+([-+]?\d*\.?\d+)\s*\]?', val_str)
            if m:
                lat_val = float(m.group(1))
                lon_val = float(m.group(2))
                if lon_val > 180: lon_val -= 360
                if -90 <= lat_val <= 90 and -180 <= lon_val <= 180:
                    return lat_val, lon_val

            # Fallback for legacy string coordinate formats (e.g., "15.0N 75.5W")
            coords = []
            used = set()
            for m in re.finditer(
                r'([-+]?\d+(?:\.\d+)?)\s*([NSEW])|([NSEW])\s*([-+]?\d+(?:\.\d+)?)',
                val_str
            ):
                if m.start() in used:
                    continue
                used.add(m.start())
                if m.group(1):          
                    coords.append((float(m.group(1)), m.group(2)))
                else:                   
                    coords.append((float(m.group(4)), m.group(3)))
            if len(coords) >= 2:
                lat_val = coords[0][0] * (-1 if coords[0][1] == 'S' else 1)
                lon_val = coords[1][0] * (-1 if coords[1][1] == 'W' else 1)
                if lon_val > 180: lon_val -= 360
                if -90 <= lat_val <= 90 and -180 <= lon_val <= 180:
                    return lat_val, lon_val
                
        # Fallback to computing the average of the geospatial bounding box
        try:
            attr_map = {k.lower(): k for k in attrs.keys()}
            
            def get_bound(key_name):
                if key_name in attr_map:
                    val = _safe_float(attrs[attr_map[key_name]])
                    return val
                return None
                
            lat_min = get_bound('geospatial_lat_min')
            lat_max = get_bound('geospatial_lat_max')
            lon_min = get_bound('geospatial_lon_min')
            lon_max = get_bound('geospatial_lon_max')
            
            if all(v is not None for v in [lat_min, lat_max, lon_min, lon_max]):
                lat_avg = (lat_min + lat_max) / 2.0
                lon_avg = (lon_min + lon_max) / 2.0
                
                if lon_avg > 180: lon_avg -= 360
                
                if -90 <= lat_avg <= 90 and -180 <= lon_avg <= 180:
                    return lat_avg, lon_avg
        except Exception:
            pass

        # Return None if no valid center or bounds were found
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

            # Apply global unit conversions
            from config import UNIT_CONVERSIONS
            for dset in df.columns:
                if dset in group_var_attrs:
                    u_raw = group_var_attrs[dset].get('units', '')
                    u_str = _safe_val(u_raw).strip().lower()
                    
                    # Match against lowercase keys in the configuration
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
        
    return {'data': data_dict, 'track': track_df, 'meta': metadata, 'var_attrs': var_attrs}
    
