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
    """Utility to clean up b'byte strings' or arrays from HDF5 metadata."""
    if isinstance(val, (np.ndarray, list)) and len(val) > 0:
        val = val[0]
    if isinstance(val, bytes):
        try:
            val = val.decode('utf-8')
        except:
            val = str(val)
    return str(val).strip("[]b'\"")

def get_basin_from_filename(filename):
    """Extracts basin code dynamically from filename prefixes."""
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
    """Loads and standardizes the global dataset CSV inventory."""
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
    
    extracted = df['Filename'].str.extract(r'\.(?P<Year>\d{4})(?P<Cycle>\d{6})')
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
    def _safe_val(val):
        try:
            if hasattr(val, '__len__') and not isinstance(val, (str, bytes)):
                val = val.flat[0] if hasattr(val, 'flat') else val[0]
            if isinstance(val, (bytes, bytearray)):
                val = val.decode('utf-8', errors='replace')
            return str(val)
        except:
            return str(val)

    def _safe_float(val):
        try: return float(_safe_val(val))
        except: return None
        
    def _find_center_in_attrs(attrs):
        if 'center_from_tc_vitals' in attrs:
            val_str = _safe_val(attrs['center_from_tc_vitals']).upper()
            matches = re.findall(r"([-+]?\d+(?:\.\d+)?)\s*([NSEW]?)", val_str)
            if len(matches) >= 2:
                lat_val = float(matches[0][0])
                if matches[0][1] == 'S': lat_val = -lat_val

                lon_val = float(matches[1][0])
                if matches[1][1] == 'W': lon_val = -lon_val
                if lon_val > 180: lon_val -= 360

                return lat_val, lon_val
                
        lat, lon = None, None
        attr_map = {k.lower(): k for k in attrs.keys()}
        for c in ['metadata_best_track_lat', 'best_track_lat', 'stormcenterlat', 'center_lat', 'lat']:
            for k in attr_map:
                if c in k:
                    v = _safe_float(attrs[k])
                    if v: lat=v; break
            if lat: break
        for c in ['metadata_best_track_lon', 'best_track_lon', 'stormcenterlon', 'center_lon', 'lon']:
            for k in attr_map:
                if c in k:
                    v = _safe_float(attrs[k])
                    if v: lon=v; break
            if lon: break
            
        if lon is not None and lon > 180: lon -= 360
        return (lat, lon) if (lat and lon) else None

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
