import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from pyproj import Geod
import h5py

# ==========================================
# 1. CLASS DEFINITION
# ==========================================
class StormPlotter:
    def __init__(self, data_dict, track_data, metadata, var_attrs):
        self.data = data_dict
        self.track = track_data
        self.metadata = metadata
        self.var_attrs = var_attrs  
        self.geod = Geod(ellps='WGS84')

        self.config_map = {
            'TDR': {
                'coord_system': 'polar',
                'exclude': ['radius', 'range', 'dist', 'azimuth', 'az', 'azim', 'elevation', 'elev', 'el', 'lat', 'lon', 'latitude', 'longitude', 'time', 'date', 'group_name']
            },
            'DROPSONDE': {
                'coord_system': 'geo',
                'exclude': ['lat', 'lon', 'latitude', 'longitude', 'time', 'date', 'mission_id', 'storm_id', 'group_name']
            },
            'FLIGHT_LEVEL': {
                'coord_system': 'geo',
                'exclude': ['lat', 'lon', 'latitude', 'longitude', 'time', 'group_name']
            },
            'SFMR': {
                'coord_system': 'geo',
                'exclude': ['lat', 'lon', 'latitude', 'longitude', 'time', 'group_name']
            },
            'TRACK': {
                'coord_system': 'geo',
                'exclude': ['lat', 'lon', 'latitude', 'longitude', 'time']
            }
        }
        
    def _get_config(self, group_name):
        g_upper = group_name.upper()
        if 'TDR' in g_upper: return self.config_map['TDR']
        if 'DROP' in g_upper: return self.config_map['DROPSONDE']
        if 'FLIGHT' in g_upper: return self.config_map['FLIGHT_LEVEL']
        if 'SFMR' in g_upper: return self.config_map['SFMR']
        if 'TRACK' in g_upper: return self.config_map['TRACK']
        return self.config_map['DROPSONDE']

    def get_plottable_variables(self, group_name, active_z_col=None):
        if group_name not in self.data: return []
        df = self.data[group_name]
        cfg = self._get_config(group_name)
        
        exclude_lower = set([x.lower() for x in cfg['exclude']])
        if active_z_col: exclude_lower.add(active_z_col.lower())
        
        valid_vars = [col for col in df.columns if col.lower() not in exclude_lower]
        return sorted(valid_vars)

    def _get_var_display_name(self, group_name, variable):
        meta = self.var_attrs.get(group_name, {}).get(variable, {})
        long_name = meta.get('long_name')
        if not long_name: long_name = variable.replace('_', ' ').title()
        else: long_name = long_name.title()
        units = meta.get('units')
        if units: return f"{long_name} ({units})"
        return long_name

    def _format_title(self, group_name, variable, constraint_lbl):
        parts = group_name.split('_')
        inst = next((p.capitalize() for p in parts if p.lower() in ['dropsonde', 'tdr', 'sfmr', 'flight']), parts[0].capitalize())
        platform = next((p.upper() for p in parts if 'noaa' in p.lower() or 'af' in p.lower() or 'usaf' in p.lower()), '')
        if not platform and len(parts) > 1: platform = parts[-1].upper()

        var_display = self._get_var_display_name(group_name, variable)

        title = f"{inst} {var_display}"
        if platform: title += f" from {platform}"
        title += f"<br><sup>{constraint_lbl}</sup>"
        return title

    def _polar_to_geo_transform(self, df):
        if self.metadata.get('storm_center') is None: return [], []
        center_lat, center_lon = self.metadata['storm_center']
        
        cols_lower = {c.lower(): c for c in df.columns}
        r_col = next((cols_lower[c] for c in ['range', 'radius', 'dist'] if c in cols_lower), None)
        az_col = next((cols_lower[c] for c in ['az', 'azimuth', 'azim'] if c in cols_lower), None)
        if not r_col or not az_col: return [], []

        radii_km = df[r_col].values
        azimuths = df[az_col].values
        
        lons = np.full_like(radii_km, center_lon)
        lats = np.full_like(radii_km, center_lat)
        new_lons, new_lats, _ = self.geod.fwd(lons, lats, azimuths, radii_km * 1000.0)
        return new_lons, new_lats

    def plot(self, group_name, variable, z_constraint=None, xy_bounds=None, show_center=False):
        if group_name not in self.data: return None
        df = self.data[group_name]
        cfg = self._get_config(group_name)
        is_track = 'TRACK' in group_name.upper()

        # 1. Z-Constraint
        plot_df = df.copy()
        constraint_lbl = "All Levels"
        if not is_track and z_constraint:
            col, val, tol = z_constraint['col'], z_constraint['val'], z_constraint['tol']
            unit_label = z_constraint.get('unit_label', '') # Get units passed from sidebar
            
            # Note: The dataframe 'df' passed here still has original units (Pa).
            # If the sidebar sent converted hPa values, we must convert plot_df column to match for filtering
            # OR convert the filter values back to Pa.
            # Strategy: Convert DF column to hPa if sidebar says so.
            if z_constraint.get('convert_pa_to_hpa'):
                plot_df[col] = plot_df[col] / 100.0
            
            if col in plot_df.columns:
                plot_df = plot_df[(plot_df[col] >= val - tol) & (plot_df[col] <= val + tol)]
                
                # Title Format with Units
                unit_suffix = f" ({unit_label})" if unit_label else ""
                constraint_lbl = f"{col}={val:,.2f} ± {tol:,.2f}{unit_suffix}"

        if plot_df.empty:
            st.warning(f"No data for {variable} at {constraint_lbl}")
            return None

        # 2. Coordinates
        if cfg['coord_system'] == 'polar':
            lons, lats = self._polar_to_geo_transform(plot_df)
            if len(lons) == 0: return None
        else:
            cols_lower = {c.lower(): c for c in plot_df.columns}
            lat_col = next((cols_lower[c] for c in ['lat', 'latitude'] if c in cols_lower), None)
            lon_col = next((cols_lower[c] for c in ['lon', 'longitude'] if c in cols_lower), None)
            if lat_col and lon_col:
                lons, lats = plot_df[lon_col].values, plot_df[lat_col].values
            else:
                st.error("Missing lat/lon columns.")
                return None

        # 3. XY Bounds Filter
        if xy_bounds:
            mask = ((lats >= xy_bounds['lat_min']) & (lats <= xy_bounds['lat_max']) &
                    (lons >= xy_bounds['lon_min']) & (lons <= xy_bounds['lon_max']))
            lats = lats[mask]
            lons = lons[mask]
            if not is_track: plot_df = plot_df.iloc[mask]
            if len(lats) == 0:
                st.warning("No data in selected domain.")
                return None

        # 4. Generate Plot
        fig = go.Figure()

        if show_center and self.metadata.get('storm_center'):
            clat, clon = self.metadata['storm_center']
            fig.add_trace(go.Scatter(
                x=[clon], y=[clat], mode='markers', 
                marker=dict(symbol='x', size=14, color='red', line=dict(width=3)),
                name='NHC Best Track Center', showlegend=True 
            ))

        if is_track:
            fig.add_trace(go.Scatter(
                x=lons, y=lats, mode='lines', 
                line=dict(width=4, color='blue'), name=group_name, showlegend=False
            ))
        else:
            cmin, cmax = plot_df[variable].min(), plot_df[variable].max()
            fig.add_trace(go.Scatter(
                x=lons, y=lats, mode='markers',
                marker=dict(
                    size=9, color=plot_df[variable], colorscale='Jet',
                    colorbar=dict(len=0.8, thickness=20, tickfont=dict(size=18)),
                    cmin=cmin, cmax=cmax
                ),
                text=[f"{v:,.2f}" for v in plot_df[variable]],
                name=group_name, showlegend=False
            ))

        # 5. Layout
        nice_title = self._format_title(group_name, variable, constraint_lbl)
        
        x_range, y_range = None, None
        if xy_bounds:
            x_range = [xy_bounds['lon_min'], xy_bounds['lon_max']]
            y_range = [xy_bounds['lat_min'], xy_bounds['lat_max']]
        elif 'bounds' in self.metadata and self.metadata['bounds']:
            x_range = [self.metadata['bounds'][0], self.metadata['bounds'][1]]
            y_range = [self.metadata['bounds'][2], self.metadata['bounds'][3]]

        fig.update_layout(
            title={'text': nice_title, 'y':0.95, 'x':0.5, 'xanchor': 'center', 'yanchor': 'top', 'font': dict(size=24, color="black")},
            height=700, font=dict(size=16, color="black"),
            xaxis=dict(title="Longitude", title_font=dict(size=20, weight="bold"), tickfont=dict(size=18), range=x_range, showgrid=True, gridwidth=1, gridcolor='lightgray', zeroline=False, showline=True, linewidth=2, linecolor='black', mirror=True),
            yaxis=dict(title="Latitude", title_font=dict(size=20, weight="bold"), tickfont=dict(size=18), range=y_range, showgrid=True, gridwidth=1, gridcolor='lightgray', scaleanchor="x", scaleratio=1, zeroline=False, showline=True, linewidth=2, linecolor='black', mirror=True),
            plot_bgcolor="rgb(250, 250, 250)",
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255, 255, 255, 0.8)", bordercolor="Black", borderwidth=1, font=dict(size=14))
        )
        return fig

# ==========================================
# 2. STREAMLIT APP LOGIC
# ==========================================

st.title("HRD Obs Visualization")
uploaded_file = st.sidebar.file_uploader("Upload HDF5 File", type=['h5', 'hdf5'])

if not uploaded_file:
    st.info("Waiting for file upload...")
    st.stop()

@st.cache_data
def load_data_from_h5(file_obj):
    def _safe_val(val):
        try:
            if hasattr(val, '__len__') and not isinstance(val, (str, bytes)):
                if len(val) == 1: val = val[0]
            if isinstance(val, bytes): val = val.decode('utf-8')
            return val
        except: return str(val)

    def _safe_float(val):
        try: return float(_safe_val(val))
        except: return None
        
    def _find_center_in_attrs(attrs):
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
        return (lat, lon) if (lat and lon) else None

    try:
        f = h5py.File(file_obj, 'r')
    except Exception as e:
        st.error(f"Error opening HDF5: {e}")
        return None

    data_dict, track_df = {}, pd.DataFrame()
    var_attrs = {} 
    metadata = {'storm_center': None, 'bounds': [], 'info': {}}

    for k, v in f.attrs.items():
        metadata['info'][f"GLOBAL_{k}"] = _safe_val(v)
    metadata['storm_center'] = _find_center_in_attrs(f.attrs)

    for key in f.keys():
        group = f[key]
        g_upper = key.upper()
        if any(x in g_upper for x in ['HEADER', 'CONFIG', 'METADATA', 'INFO']):
            if not metadata['storm_center']: metadata['storm_center'] = _find_center_in_attrs(group.attrs)
            continue

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
                if c.lower() in ['lat', 'latitude', 'ilat']: rename_map[c] = 'lat'
                if c.lower() in ['lon', 'longitude', 'ilon']: rename_map[c] = 'lon'
            if rename_map: df.rename(columns=rename_map, inplace=True)
            
            if 'TRACK' in g_upper:
                track_df = df
                data_dict[key] = df
                var_attrs[key] = group_var_attrs
                if not metadata['storm_center'] and 'lat' in df.columns:
                     mid = len(df) // 2
                     metadata['storm_center'] = (df.iloc[mid]['lat'], df.iloc[mid]['lon'])
            else:
                data_dict[key] = df
                var_attrs[key] = group_var_attrs

    if metadata['storm_center']:
        clat, clon = metadata['storm_center']
        metadata['bounds'] = [clon-3.0, clon+3.0, clat-3.0, clat+3.0]
    return {'data': data_dict, 'track': track_df, 'meta': metadata, 'var_attrs': var_attrs}

with st.spinner("Processing HDF5..."):
    data_pack = load_data_from_h5(uploaded_file)

if not data_pack or not data_pack['data']:
    st.warning("No data found."); st.stop()

if data_pack['meta']['storm_center'] is None:
    st.sidebar.warning("Center Missing")
    clat = st.sidebar.number_input("Lat", 20.0)
    clon = st.sidebar.number_input("Lon", -50.0)
    data_pack['meta']['storm_center'] = (clat, clon)
    data_pack['meta']['bounds'] = [clon-3, clon+3, clat-3, clat+3]

# Session State for Domain
d_bounds = data_pack['meta']['bounds'] 
if 'bounds_lat_min' not in st.session_state: st.session_state.bounds_lat_min = d_bounds[2]
if 'bounds_lat_max' not in st.session_state: st.session_state.bounds_lat_max = d_bounds[3]
if 'bounds_lon_min' not in st.session_state: st.session_state.bounds_lon_min = d_bounds[0]
if 'bounds_lon_max' not in st.session_state: st.session_state.bounds_lon_max = d_bounds[1]

plotter = StormPlotter(data_pack['data'], data_pack['track'], data_pack['meta'], data_pack['var_attrs'])

# ==========================================
# 3. SIDEBAR CONTROLS
# ==========================================
st.sidebar.markdown("### Data Selection")

sel_group = st.sidebar.selectbox("Data Group", sorted(list(data_pack['data'].keys())))

# Detect available Z-columns for this specific group
h_col, p_col = None, None
if 'TRACK' not in sel_group.upper():
    df_sel = data_pack['data'][sel_group]
    cols_lower = {c.lower(): c for c in df_sel.columns}
    h_col = next((cols_lower[c] for c in ['height', 'ght', 'altitude', 'elev'] if c in cols_lower), None)
    p_col = next((cols_lower[c] for c in ['pres', 'pressure', 'p'] if c in cols_lower), None)

# Check State of Vertical Filter
is_filtering = st.session_state.get('use_v_filter', False)
active_vert_coord = st.session_state.get('v_coord_sel', None)

exclude_col = active_vert_coord if is_filtering else None
vars_list = plotter.get_plottable_variables(sel_group, active_z_col=exclude_col)

if 'TRACK' in sel_group.upper(): 
    variable = 'Path'
elif vars_list: 
    variable = st.sidebar.selectbox("Variable", vars_list)
else: 
    st.stop()

st.sidebar.markdown("---")
st.sidebar.markdown("### Vertical Slice")

use_filter = st.sidebar.checkbox("Filter by Level?", False, key='use_v_filter')
z_con = None

if use_filter and (h_col or p_col):
    options = []
    if h_col: options.append(h_col)
    if p_col: options.append(p_col)
    
    if len(options) > 1:
        target_col = st.sidebar.selectbox("Vertical Coordinate", options, key='v_coord_sel')
    else:
        target_col = st.sidebar.selectbox("Vertical Coordinate", options, key='v_coord_sel', disabled=True)

    # Unit Logic & Conversion
    v_meta = data_pack['var_attrs'].get(sel_group, {}).get(target_col, {})
    v_unit = v_meta.get('units', '')
    
    # Check if we need to convert Pa -> hPa
    is_pa = 'Pa' in v_unit and 'hPa' not in v_unit
    convert = False
    
    if is_pa:
        # User sees hPa, logic handles conversion
        v_unit = 'hPa'
        convert = True
        
    unit_str = f"({v_unit})" if v_unit else ""
    
    # Get Data Range (Converting if necessary)
    raw_vals = df_sel[target_col].values
    if convert:
        raw_vals = raw_vals / 100.0
        
    dmin, dmax = float(np.nanmin(raw_vals)), float(np.nanmax(raw_vals))
    
    # Defaults: FULL RANGE
    default_val = (dmax + dmin) / 2.0
    default_tol = (dmax - dmin) / 2.0
    
    c1, c2 = st.sidebar.columns(2)
    val = c1.number_input(f"Center {target_col} {unit_str}", value=default_val, format="%.2f")
    tol = c2.number_input("Tol (+/-)", value=max(default_tol, 0.1), format="%.2f")
    
    z_con = {
        'col': target_col, 
        'val': val, 
        'tol': tol, 
        'convert_pa_to_hpa': convert, # Flag for plotter
        'unit_label': v_unit # Flag for title
    }
    
elif use_filter and not (h_col or p_col):
    st.sidebar.info("No vertical coordinates found for slicing.")

st.sidebar.markdown("#### Layers")
show_cen = st.sidebar.checkbox("Show Storm Center", value=True)

st.sidebar.markdown("#### Plot Domain (Determines Color Scale)")

def reset_domain():
    st.session_state.bounds_lat_min = d_bounds[2]
    st.session_state.bounds_lat_max = d_bounds[3]
    st.session_state.bounds_lon_min = d_bounds[0]
    st.session_state.bounds_lon_max = d_bounds[1]

c1, c2 = st.sidebar.columns(2)
lat_min = c1.number_input("Lat Min", key='bounds_lat_min')
lat_max = c2.number_input("Lat Max", key='bounds_lat_max')
lon_min = c1.number_input("Lon Min", key='bounds_lon_min')
lon_max = c2.number_input("Lon Max", key='bounds_lon_max')
st.sidebar.button("Reset to Original Domain", on_click=reset_domain)

xy_bounds = {'lat_min': lat_min, 'lat_max': lat_max, 'lon_min': lon_min, 'lon_max': lon_max}

if variable:
    fig = plotter.plot(sel_group, variable, z_con, xy_bounds, show_cen)
    if fig: st.plotly_chart(fig, use_container_width=True)