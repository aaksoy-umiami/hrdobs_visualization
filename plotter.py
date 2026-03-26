# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import math
import re
from config import GLOBAL_VAR_CONFIG
from data_utils import decode_metadata
from ui_layout import CLR_PRIMARY, CLR_PLOT_BG, CLR_PLOT_GRID, CLR_MUTED, FS_PLOT_TITLE, FS_PLOT_AXIS, FS_PLOT_TICK, TARGET_PLOT_TICKS, CLR_EXTRA, PLOT_TITLE_Y

# ---------------------------------------------------------------------------
# Tunable display constants
# ---------------------------------------------------------------------------
_CONE_DOMAIN_FRACTION   = 0.03
_SURFACE_PRESSURE_HPA   = 1013.25
_FIG_HEIGHT_BASE        = 800
_FIG_HEIGHT_Z_THRESHOLD = 0.6
_FIG_HEIGHT_Z_STRETCH   = 400
EARTH_R_KM              = 6371.0


class StormPlotter:
    """
    Main plotting class for rendering 2D and 3D visualizations of storm data 
    using Plotly. Handles Cartesian, Storm-Relative, Radial-Height, and 
    statistical histogram/scatter plots.
    """

    def __init__(self, data_dict, track_data, metadata, var_attrs):
        """
        Initializes the StormPlotter with data, track paths, metadata, 
        and variable attributes.
        """
        self.data = data_dict
        self.track = track_data
        self.metadata = metadata
        self.var_attrs = var_attrs  

    def _get_color_setup(self, group_name, variable, color_scale):
        """
        Computes the colormap, cmin, cmax, cmid, colorbar title, and custom tick 
        values/text from the unfiltered group data. Both plot() and 
        plot_storm_relative() use this to ensure identical color scaling.
        """
        var_conf  = GLOBAL_VAR_CONFIG.get(variable.lower(), {})
        cmap      = var_conf.get('colorscale', 'Jet')
        cmid_conf = var_conf.get('cmid')
        cmid      = float(cmid_conf) if cmid_conf is not None else None
        cb_title  = self._get_var_display_name(group_name, variable)
        cb_tickvals, cb_ticktext = None, None

        df_full = self.data.get(group_name)
        if df_full is not None and variable in df_full.columns:
            full_vals = df_full[variable].dropna().values.astype(float)
        else:
            full_vals = np.array([0.0, 1.0])

        if variable.lower() == 'time' and len(full_vals) > 0:
            _tr = self._convert_time_to_relative(full_vals)
            if _tr is not None:
                full_vals = _tr[0][np.isfinite(_tr[0])]
            cb_title = "Time rel. to cycle center"

        cmin_conf = var_conf.get('cmin')
        cmax_conf = var_conf.get('cmax')
        cmin = float(cmin_conf) if cmin_conf is not None else (
            float(np.nanmin(full_vals)) if len(full_vals) > 0 else 0.0)
        cmax = float(cmax_conf) if cmax_conf is not None else (
            float(np.nanmax(full_vals)) if len(full_vals) > 0 else 1.0)

        if color_scale == "Log scale":
            pos = full_vals[full_vals > 0]
            real_cmin = cmin if cmin > 0 else (float(np.nanmin(pos)) if len(pos) > 0 else 1e-3)
            real_cmax = cmax if cmax > 0 else (float(np.nanmax(pos)) if len(pos) > 0 else 1.0)
            cmin = np.log10(real_cmin)
            cmax = np.log10(real_cmax)
            cmid = None
            mn, mx = int(np.floor(cmin)), int(np.ceil(cmax))
            if mx > mn:
                cb_tickvals = np.arange(mn, mx + 1, dtype=float)
            else:
                cb_tickvals = np.array([cmin, cmax])
            cb_ticktext = [f"1e{int(p)}" if p < -3 or p > 3 else f"{10**p:g}"
                           for p in cb_tickvals]

        return cmap, cmin, cmax, cmid, cb_title, cb_tickvals, cb_ticktext

    def get_plottable_variables(self, sel_group, active_z_col=None, exclude_vectors=False):
        """
        Retrieves a sorted list of variables valid for plotting within a selected group, 
        optionally excluding the active Z-axis coordinate or vector variables.
        """
        if sel_group not in self.data: return []
        
        df = self.data[sel_group]
        valid_cols = []
        
        for col in df.columns:
            if active_z_col and col == active_z_col: continue
            col_lower = col.lower()
            cfg = GLOBAL_VAR_CONFIG.get(col_lower, {})
            if cfg.get('hide', False): continue
            if exclude_vectors and cfg.get('is_vector', False): continue
            if col_lower.endswith('err'): continue
            if df[col].dtype == 'object': continue
            valid_cols.append(col)
            
        def custom_sort(c):
            c_lower = c.lower()
            cfg = GLOBAL_VAR_CONFIG.get(c_lower, {})
            if cfg.get('is_coord', False):
                tier = '2'
            elif cfg.get('is_derived', False):
                tier = '1'
            else:
                tier = '0'
            return f'{tier}_{c_lower}'
            
        return sorted(valid_cols, key=custom_sort)
    
    def get_coordinate_variables(self, group_name):
        """
        Identifies columns that act as coordinates using GLOBAL_VAR_CONFIG rules.
        """
        if group_name not in self.data: return []
        df = self.data[group_name]
        valid_coords = []
        
        for col in df.columns:
            c_lower = col.lower()
            if GLOBAL_VAR_CONFIG.get(c_lower, {}).get('is_coord', False):
                valid_coords.append(col)
                
        if not valid_coords:
            valid_coords = [c for c in df.columns if df[c].dtype != 'object']
            
        return sorted(valid_coords)

    def _get_var_display_name(self, group_name, variable):
        """
        Retrieves the formatted display name and units for a variable based on 
        metadata and custom definitions.
        """
        if variable.lower() == 'time':
            return "Time (relative to cycle center)"
        meta = self.var_attrs.get(group_name, {}).get(variable, {})
        long_name = decode_metadata(meta.get('long_name', ''))

        if not long_name:
            if variable.lower().endswith('err'):
                base_var = variable[:-3] if not variable.lower().endswith('_err') else variable[:-4]
                long_name = base_var.replace('_', ' ').title() + " Error"
            else:
                long_name = variable.replace('_', ' ').title()
        else:
            long_name = long_name.title()

        units = decode_metadata(meta.get('units', ''))
        if units: return f"{long_name} ({units})"
        return long_name

    def _format_storm_subtitle(self):
        """
        Returns a compact storm identification string from file metadata.
        Example: BERYL02L (02-Jul-2024 12:00 UTC)
        Returns an empty string if the required metadata is absent.
        """
        info = self.metadata.get('info', {})
        storm_id = info.get('storm_id', '').strip()
        dt_raw   = info.get('storm_datetime', '').strip()

        if not storm_id:
            return ''

        dt_str = ''
        if dt_raw:
            try:
                from datetime import datetime
                dt = datetime.strptime(dt_raw.rstrip('Z'), '%Y-%m-%dT%H:%M:%S')
                dt_str = dt.strftime('%d-%b-%Y %H:%M UTC')
            except ValueError:
                dt_str = dt_raw

        if dt_str:
            return f"{storm_id} ({dt_str})"
        return storm_id

    def _format_title(self, group_name, variable, constraint_lbl):
        """
        Constructs an HTML formatted multi-line title for the plot, including 
        instrument, platform, variable name, and active constraints.
        """
        parts = group_name.split('_')

        if parts[0].lower() == 'track':
            inst = ' '.join(p.capitalize() for p in parts[1:])
            platform = ''
        else:
            inst_lower = next((p.lower() for p in parts if p.lower() in ['dropsonde', 'tdr', 'sfmr', 'flight']), parts[0].lower())
            if inst_lower in ['sfmr', 'tdr']:
                inst = inst_lower.upper()
            elif inst_lower == 'flight':
                inst = "Flight-Level"
            else:
                inst = inst_lower.capitalize()
            platform = next((p.upper() for p in parts if 'noaa' in p.lower() or 'af' in p.lower() or 'usaf' in p.lower()), '')
            if not platform and len(parts) > 1: platform = parts[-1].upper()

        var_display = self._get_var_display_name(group_name, variable)
        line1 = f"{inst} {var_display}"
        if platform: line1 += f" from {platform}"

        lines = [f"<span style='font-size:{FS_PLOT_TITLE}px'>{line1}</span>"]
        if constraint_lbl:
            lines.append(f"<span style='font-size:{FS_PLOT_AXIS}px'>{constraint_lbl}</span>")

        storm_sub = self._format_storm_subtitle()
        if storm_sub:
            lines.append(f"<span style='font-size:{FS_PLOT_AXIS}px'>{storm_sub}</span>")

        return "<br>".join(lines)

    def _title_top_margin(self, title: str, gap: int = 20) -> int:
        """
        Computes the top margin in pixels, consisting of the title block height 
        plus a gap to the plot area.
        """
        n_lines = title.count('<br>') + 1
        height = FS_PLOT_TITLE 
        height += max(0, n_lines - 1) * FS_PLOT_AXIS 
        return height + gap

    def _convert_time_to_relative(self, vals):
        """
        Converts a float array of YYYYMMDDHHmmss to seconds relative to storm_epoch.
        Returns a tuple of (converted_vals, tick_vals, tick_labels) for clean 
        intervals formatted as ±HH:MM:SS. Returns None on failure.
        """
        from datetime import datetime, timezone
        info = self.metadata.get('info', {})
        epoch_raw = info.get('storm_epoch', '')
        try:
            cycle_epoch = float(epoch_raw)
        except (ValueError, TypeError):
            dt_raw = info.get('storm_datetime', '').strip()
            try:
                dt = datetime.strptime(dt_raw.rstrip('Z'), '%Y-%m-%dT%H:%M:%S')
                cycle_epoch = dt.replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                return None

        def yyyymmddhhmmss_to_epoch(v):
            s = f"{v:.0f}"
            try:
                dt = datetime.strptime(s, '%Y%m%d%H%M%S')
                return dt.replace(tzinfo=timezone.utc).timestamp() - cycle_epoch
            except ValueError:
                return np.nan

        rel_vals = np.array([yyyymmddhhmmss_to_epoch(v) for v in vals])

        finite = rel_vals[np.isfinite(rel_vals)]
        if len(finite) == 0:
            return None
        t_min, t_max = finite.min(), finite.max()
        interval = 1800 
        tick_start = np.ceil(t_min / interval) * interval
        tick_end   = np.floor(t_max / interval) * interval
        tick_vals  = np.arange(tick_start, tick_end + 1, interval)

        def fmt_seconds(s):
            sign = '-' if s < 0 else '+'
            s = abs(int(s))
            h, rem = divmod(s, 3600)
            m, sec = divmod(rem, 60)
            return f"{sign}{h:02d}:{m:02d}:{sec:02d}"

        tick_labels = [fmt_seconds(t) for t in tick_vals]
        return rel_vals, tick_vals, tick_labels

    def _apply_time_axis(self, var_col, vals, axis_dict, is_x=True):
        """
        If var_col is a time variable, converts vals to relative seconds and
        updates axis_dict in-place with custom ticks and a relative time label.
        Slants tick labels when on the x-axis. Returns the (possibly converted) values.
        """
        if var_col.lower() != 'time':
            return vals
        result = self._convert_time_to_relative(vals)
        if result is None:
            return vals
        rel_vals, tick_vals, tick_labels = result
        axis_dict['tickvals']  = tick_vals
        axis_dict['ticktext']  = tick_labels
        axis_dict['title']     = 'Time relative to cycle center (HH:MM:SS)'
        if is_x:
            axis_dict['tickangle'] = -45
        return rel_vals

    def plot(self, group_name, variable, z_con, domain_bounds, show_center,
             is_3d=False, z_col=None, thinning_pct=None, marker_size_pct=100,
             time_bounds=None, z_ratio=0.3, vec_scale=1.0, show_basemap=False,
             cen_mode="Display Location Only", color_scale="Linear scale"):
        """
        Renders the primary Horizontal Cartesian plot (2D or 3D). Returns a tuple 
        (fig, plot_df) representing the resulting Plotly figure and the active 
        filtered DataFrame used for the plot.
        """
        
        if group_name not in self.data: return None, None
            
        df = self.data[group_name].copy()
        is_track = 'TRACK' in group_name.upper()
        
        cols_lower = {c.lower(): c for c in df.columns}
        x_col = next((cols_lower[c] for c in ['lon', 'longitude', 'clon'] if c in cols_lower), None)
        y_col = next((cols_lower[c] for c in ['lat', 'latitude',  'clat'] if c in cols_lower), None)
        
        if not x_col or not y_col: return None, None
            
        cols_to_check = [x_col, y_col]
        if not is_track and variable in df.columns: cols_to_check.append(variable)
        if z_col and z_col in df.columns: cols_to_check.append(z_col)
            
        df = df.dropna(subset=cols_to_check)
        if df.empty: return None, None

        _var_conf_pre = GLOBAL_VAR_CONFIG.get(variable.lower(), {})
        if thinning_pct is not None and thinning_pct < 100:
            df = df.sample(frac=thinning_pct/100.0, random_state=42)
        if df.empty: return None, None

        constraint_lbl = ""
        plot_df = df.copy()
        
        if z_con and z_con.get('col') in plot_df.columns:
            t_col = z_con['col']
            val = z_con['val']
            tol = z_con['tol']
            mask = (plot_df[t_col] >= val - tol) & (plot_df[t_col] <= val + tol)
            plot_df = plot_df[mask]
            unit_str = "hPa" if z_con.get('convert_pa_to_hpa') else ""
            constraint_lbl = f"Level: {val} ± {tol} {unit_str}"
            
        if plot_df.empty:
            st.warning("No valid data found at this specific level filter.")
            return None, None

        lats, lons = plot_df[y_col].values, plot_df[x_col].values

        if domain_bounds and not is_track:
            mask = ((lats >= domain_bounds['lat_min']) & (lats <= domain_bounds['lat_max']) &
                    (lons >= domain_bounds['lon_min']) & (lons <= domain_bounds['lon_max']))

            if 'z_min' in domain_bounds and domain_bounds['z_col'] in plot_df.columns:
                z_b_col = domain_bounds['z_col']
                z_b_vals = plot_df[z_b_col].values
                if domain_bounds.get('z_convert'): z_b_vals = z_b_vals / 100.0
                mask &= ((z_b_vals >= domain_bounds['z_min']) & (z_b_vals <= domain_bounds['z_max']))

            plot_df = plot_df[mask]
            lats, lons = plot_df[y_col].values, plot_df[x_col].values
            if len(lats) == 0:
                st.warning("No data in selected domain.")
                return None, None
        
        if time_bounds and time_bounds['col'] in plot_df.columns and not is_track:
            t_col = time_bounds['col']
            t_min, t_max = time_bounds['min'], time_bounds['max']
            plot_df = plot_df[(plot_df[t_col] >= t_min) & (plot_df[t_col] <= t_max)]
            lats, lons = plot_df[y_col].values, plot_df[x_col].values
            
            if plot_df.empty:
                st.warning("No data found within the selected time window.")
                return None, None

        _filtered_color_vals = plot_df[variable].values if variable in plot_df.columns else None
        if _filtered_color_vals is not None and variable.lower() == 'time':
            _tr = self._convert_time_to_relative(_filtered_color_vals)
            _filtered_color_vals = _tr[0] if _tr is not None else _filtered_color_vals
        _full_cmin = float(_var_conf_pre['cmin']) if _var_conf_pre.get('cmin') is not None else (
            float(np.nanmin(_filtered_color_vals)) if _filtered_color_vals is not None else None)
        _full_cmax = float(_var_conf_pre['cmax']) if _var_conf_pre.get('cmax') is not None else (
            float(np.nanmax(_filtered_color_vals)) if _filtered_color_vals is not None else None)
        if variable.lower() == 'time' and _full_cmin is not None:
            _full_cmin = max(_full_cmin, -10800.0)
            _full_cmax = min(_full_cmax,  10800.0)

        fig = go.Figure()

        z_vals = None
        if is_3d and z_col and z_col in plot_df.columns:
            z_vals = plot_df[z_col].values.copy()

        var_conf = GLOBAL_VAR_CONFIG.get(variable.lower(), {})
        cmap = var_conf.get('colorscale', 'Jet') 

        cmid = var_conf.get('cmid', None)
        sz_mult = marker_size_pct / 100.0

        display_name = self._get_var_display_name(group_name, variable)
        cols_lower = {c.lower(): c for c in plot_df.columns}
        is_vector = variable.lower() in ['wind_vec_hz', 'wind_vec_3d']
        cb_title = display_name.split('(')[-1].replace(')', '') if '(' in display_name else ""

        cb_tickvals = None
        cb_ticktext = None
        
        magnitude_vals = None
        if is_vector:
            u_col, v_col = cols_lower.get('u'), cols_lower.get('v')
            u_vals = plot_df[u_col].values
            v_vals = plot_df[v_col].values
            magnitude_vals = plot_df[variable].values
            base_color_array = magnitude_vals
        elif is_track:
            raw_track_vals = plot_df[variable].values if variable in plot_df.columns else None
            if raw_track_vals is None or np.all(np.isnan(raw_track_vals)):
                base_color_array = np.zeros(len(plot_df))
            else:
                base_color_array = raw_track_vals.copy().astype(float)
                nan_mask = np.isnan(base_color_array)
                if nan_mask.any():
                    base_color_array[nan_mask] = np.nanmean(base_color_array)
        else:
            base_color_array = plot_df[variable].values

        if variable.lower() == 'time':
            _dummy_axis = {}
            base_color_array = self._apply_time_axis(variable, base_color_array, _dummy_axis, is_x=False)
            if 'tickvals' in _dummy_axis:
                cb_tickvals = _dummy_axis['tickvals']
                cb_ticktext = _dummy_axis['ticktext']
            cb_title = "Time rel. to cycle center"

        if is_track and variable not in plot_df.columns:
            cmin, cmax = 0, 1
            color_array = base_color_array
        else:
            cmin_conf = var_conf.get('cmin')
            cmax_conf = var_conf.get('cmax')
            cmin = float(cmin_conf) if cmin_conf is not None else (
                _full_cmin if _full_cmin is not None else float(np.nanmin(base_color_array)))
            cmax = float(cmax_conf) if cmax_conf is not None else (
                _full_cmax if _full_cmax is not None else float(np.nanmax(base_color_array)))
            
            if color_scale == "Log scale":
                if is_vector and is_3d:
                    st.toast("⚠️ Log scale not supported for 3D vector cones. Using Linear.", icon="⚠️")
                    color_array = base_color_array
                else:
                    pos_mask = base_color_array > 0
                    log_color = np.full_like(base_color_array, np.nan, dtype=float)
                    log_color[pos_mask] = np.log10(base_color_array[pos_mask])
                    color_array = log_color
                    
                    real_cmin = cmin if cmin > 0 else np.nanmin(base_color_array[pos_mask])
                    real_cmax = cmax if cmax > 0 else np.nanmax(base_color_array[pos_mask])
                    
                    cmin = np.log10(real_cmin) if not np.isnan(real_cmin) else 0
                    cmax = np.log10(real_cmax) if not np.isnan(real_cmax) else 1
                    cmid = None 
                    
                    min_pow = int(np.floor(cmin))
                    max_pow = int(np.ceil(cmax))
                    if max_pow - min_pow < 1:
                        cb_tickvals = [cmin, cmax]
                        cb_ticktext = [f"{10**cmin:.2g}", f"{10**cmax:.2g}"]
                    else:
                        cb_tickvals = np.arange(min_pow, max_pow + 1, dtype=float)
                        cb_ticktext = [f"1e{int(p)}" if p < -3 or p > 3 else f"{10**p:g}" for p in cb_tickvals]
            else:
                color_array = base_color_array

        if is_vector:
            if is_3d and z_vals is not None:
                w_col = cols_lower.get('w')
                w_vals = plot_df[w_col].values if variable.lower() == 'wind_vec_3d' and w_col else np.zeros_like(u_vals)
                max_span = max(np.nanmax(lons) - np.nanmin(lons), np.nanmax(lats) - np.nanmin(lats))
                if pd.isna(max_span) or max_span == 0: max_span = 1.0
                
                target_length = max_span * _CONE_DOMAIN_FRACTION * vec_scale
                max_mag = np.nanmax(magnitude_vals)
                cone_sizeref = (target_length / max_mag) if max_mag > 0 else 1.0
                
                fig.add_trace(go.Cone(
                    x=lons, y=lats, z=z_vals, u=u_vals, v=v_vals, w=w_vals,
                    colorscale=cmap, cmin=cmin, cmax=cmax,
                    sizemode="raw", sizeref=cone_sizeref, anchor="tail",
                    name=display_name, showscale=True,
                    colorbar=dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK))
                ))
            else:
                angles = np.degrees(np.arctan2(u_vals, v_vals))
                marker_dict = dict(
                    symbol='arrow-up', angle=angles, angleref='up',
                    size=12 * sz_mult * vec_scale, color=color_array,
                    colorscale=cmap, cmin=cmin, cmax=cmax, cmid=cmid,
                    showscale=True, colorbar=dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK), tickvals=cb_tickvals, ticktext=cb_ticktext)
                )
                text_arr = [f"Magnitude: {m:.1f}" if not pd.isna(m) else "NaN" for m in base_color_array]
                
                fig.add_trace(go.Scatter(
                    x=lons, y=lats, mode='markers', marker=marker_dict,
                    name=display_name, text=text_arr, hoverinfo='text+x+y', showlegend=False
                ))

        elif is_3d and z_vals is not None:
            fig.add_trace(go.Scatter3d(
                x=lons, y=lats, z=z_vals, mode='markers',
                marker=dict(
                    size=4 * sz_mult, color=color_array, colorscale=cmap,
                    colorbar=dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK), tickvals=cb_tickvals, ticktext=cb_ticktext),
                    cmin=cmin, cmax=cmax, cmid=cmid, opacity=0.8
                ),
                text=[f"{v:,.2f}" if not pd.isna(v) else "NaN" for v in base_color_array],
                name=group_name, showlegend=False
            ))
        else:
            marker_dict = dict(
                size=9 * sz_mult, color=color_array, colorscale=cmap,
                colorbar=dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK), tickvals=cb_tickvals, ticktext=cb_ticktext),
                cmin=cmin, cmax=cmax, cmid=cmid
            )
            text_arr = [f"{v:,.2f}" if not pd.isna(v) else "NaN" for v in base_color_array]
            
            fig.add_trace(go.Scatter(
                x=lons, y=lats, mode='markers', marker=marker_dict,
                text=text_arr, name=group_name, showlegend=False
            ))

        if show_center and self.metadata.get('storm_center'):
            clat, clon = self.metadata['storm_center']
            use_3d = is_3d and (z_vals is not None)
            
            motion_dir = None
            if cen_mode == "Display As Motion Vector":
                motion_str = str(self.metadata.get('info', {}).get('storm_motion', ''))
                nums = re.findall(r'[-+]?\d*\.?\d+', motion_str)
                if len(nums) >= 2:
                    motion_dir = float(nums[1])
                else:
                    st.toast("⚠️ Could not parse storm direction for vector. Falling back to X.", icon="⚠️")
                    
            if motion_dir is not None:
                theta = math.radians(90 - motion_dir)
                
                if domain_bounds:
                    span = max(domain_bounds['lat_max'] - domain_bounds['lat_min'], 
                               domain_bounds['lon_max'] - domain_bounds['lon_min'])
                    arrow_len = max(span * 0.04, 0.06) 
                else:
                    arrow_len = 0.33
                    
                tip_lon = clon + arrow_len * math.cos(theta)
                tip_lat = clat + arrow_len * math.sin(theta)
                
                wing_len = arrow_len * 0.3
                w1_lon = tip_lon + wing_len * math.cos(theta + math.radians(150))
                w1_lat = tip_lat + wing_len * math.sin(theta + math.radians(150))
                w2_lon = tip_lon + wing_len * math.cos(theta - math.radians(150))
                w2_lat = tip_lat + wing_len * math.sin(theta - math.radians(150))
                
                a_lon = [clon, tip_lon, w1_lon, tip_lon, w2_lon]
                a_lat = [clat, tip_lat, w1_lat, tip_lat, w2_lat]
                
                if use_3d:
                    is_pres = z_col and any(p in z_col.lower() for p in ['pres', 'pressure', 'p'])
                    z_bottom = np.nanmax(z_vals) if is_pres else np.nanmin(z_vals)
                    fig.add_trace(go.Scatter3d(
                        x=[clon], y=[clat], z=[z_bottom], mode='markers',
                        marker=dict(symbol='circle', size=6, color='black'),
                        name='Center Location', showlegend=False, hoverinfo='skip'
                    ))
                    fig.add_trace(go.Scatter3d(
                        x=a_lon, y=a_lat, z=[z_bottom]*5, mode='lines',
                        line=dict(color='black', width=3),
                        name='Storm Motion', showlegend=False, hoverinfo='skip'
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=[clon], y=[clat], mode='markers',
                        marker=dict(symbol='circle', size=10, color='black'),
                        name='Center Location', showlegend=False, hoverinfo='skip'
                    ))
                    fig.add_trace(go.Scatter(
                        x=a_lon, y=a_lat, mode='lines',
                        line=dict(color='black', width=2.5),
                        name='Storm Motion', showlegend=False, hoverinfo='skip'
                    ))
            else:
                if use_3d:
                    is_pres = z_col and any(p in z_col.lower() for p in ['pres', 'pressure', 'p'])
                    z_bottom = np.nanmax(z_vals) if is_pres else np.nanmin(z_vals)
                    fig.add_trace(go.Scatter3d(
                        x=[clon], y=[clat], z=[z_bottom], mode='markers', 
                        marker=dict(symbol='x', size=5, color='black', line=dict(color='black', width=1.5)), 
                        name='Center', showlegend=False, hoverinfo='skip'
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=[clon], y=[clat], mode='markers',
                        marker=dict(symbol='x', size=12, color='black', line=dict(color='black', width=1.5)),
                        name='Center', showlegend=False, hoverinfo='skip'
                    ))

        nice_title = self._format_title(group_name, variable, constraint_lbl)
        
        x_range, y_range, z_range = None, None, None
        if domain_bounds:
            x_range = [domain_bounds['lon_min'], domain_bounds['lon_max']]
            y_range = [domain_bounds['lat_min'], domain_bounds['lat_max']]
            if 'z_min' in domain_bounds:
                z_range = [domain_bounds['z_min'], domain_bounds['z_max']]
                if domain_bounds.get('z_col') and any(p in domain_bounds['z_col'].lower() for p in ['pres', 'pressure', 'p']):
                    z_range = [domain_bounds['z_max'], domain_bounds['z_min']]

        if is_3d and z_vals is not None:
            scene_dict = dict(
                aspectmode='manual',
                aspectratio=dict(x=1, y=1, z=z_ratio),
                xaxis_title="Longitude", yaxis_title="Latitude", zaxis_title=z_col,
                xaxis=dict(range=x_range, nticks=20), yaxis=dict(range=y_range, nticks=20),
                zaxis=dict(range=z_range, nticks=10)
            )

            if z_col and any(p in z_col.lower() for p in ['pres', 'pressure', 'p']):
                scene_dict['zaxis']['autorange'] = 'reversed'

            scene_dict['camera'] = dict(eye=dict(x=1.5, y=-1.5, z=1.0 + (z_ratio * 0.8)))

            dynamic_height = _FIG_HEIGHT_BASE if z_ratio <= _FIG_HEIGHT_Z_THRESHOLD else int(_FIG_HEIGHT_BASE + (z_ratio - _FIG_HEIGHT_Z_THRESHOLD) * _FIG_HEIGHT_Z_STRETCH)

            fig.update_layout(
                title={'text': nice_title, 'x': 0.5, 'xanchor': 'center', 'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
                width=800, height=dynamic_height,
                showlegend=False,
                scene=scene_dict,
                margin=dict(l=60, r=40, b=40, t=self._title_top_margin(nice_title))
            )
        else:
            _FIG_W = 700
            _ML, _MR, _MB = 60, 120, 60
            _MT = self._title_top_margin(nice_title)
            if domain_bounds and domain_bounds.get('lat_max') is not None:
                lat_range = domain_bounds['lat_max'] - domain_bounds['lat_min']
                lon_range = domain_bounds['lon_max'] - domain_bounds['lon_min']
                aspect = lat_range / lon_range if lon_range > 0 else 1.0
            else:
                aspect = 1.0
            _PA_W = _FIG_W - _ML - _MR
            _PA_H = int(max(280, min(700, _PA_W * aspect)))
            _FIG_H = _PA_H + _MT + _MB

            if show_basemap and domain_bounds:
                from basemap import get_basemap_traces
                for bm_trace in get_basemap_traces(domain_bounds):
                    fig.add_trace(bm_trace)
                    fig.data = (fig.data[-1],) + fig.data[:-1] 

            fig.update_layout(
                title={'text': nice_title, 'x': 0.5, 'xanchor': 'center', 'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
                width=_FIG_W, height=_FIG_H,
                autosize=False,
                showlegend=False,
                xaxis=dict(
                    title='Longitude',
                    tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                    range=x_range,
                    showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
                    showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                    constrain='domain',
                ),
                yaxis=dict(
                    title='Latitude',
                    tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                    range=y_range,
                    showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
                    showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                    scaleanchor='x', scaleratio=1,
                    constrain='domain',
                ),
                plot_bgcolor=CLR_PLOT_BG,
                paper_bgcolor=CLR_PLOT_BG,
                margin=dict(autoexpand=False, l=_ML, r=_MR, t=_MT, b=_MB),
            )
            
        return fig, plot_df

    def _to_storm_relative(self, obs_lons, obs_lats, obs_times, track_grp, up_convention):
        """
        Converts observation (lon, lat) positions to storm-relative
        Cartesian coordinates (x_km east, y_km north of storm center),
        then to polar (range_km, azimuth_deg).

        Storm center is linearly interpolated to each observation time
        using the track_grp DataFrame.

        up_convention : "Relative to North"        → azimuth measured clockwise from N
                        "Relative to Storm Motion" → azimuth measured clockwise from
                                                     storm motion heading, so
                                                     0° = right of track,
                                                     90° = ahead

        Returns (x_km, y_km, range_km, azimuth_deg, storm_heading_deg_per_obs).
        storm_heading_deg_per_obs is None when up_convention == "Relative to North".
        """
        from datetime import datetime, timezone

        track_df = self.data[track_grp]
        tcols = {c.lower(): c for c in track_df.columns}
        t_col   = tcols.get('time')
        lat_col = next((tcols[c] for c in ['lat', 'latitude', 'clat'] if c in tcols), None)
        lon_col = next((tcols[c] for c in ['lon', 'longitude', 'clon'] if c in tcols), None)
        if not all([t_col, lat_col, lon_col]):
            return None

        def _ts(v):
            try:
                s = f"{v:.0f}"
                dt = datetime.strptime(s, '%Y%m%d%H%M%S')
                return dt.replace(tzinfo=timezone.utc).timestamp()
            except Exception:
                return np.nan

        track_epochs = np.array([_ts(v) for v in track_df[t_col].values])
        track_lats   = track_df[lat_col].values.astype(float)
        track_lons   = track_df[lon_col].values.astype(float)

        order       = np.argsort(track_epochs)
        track_epochs = track_epochs[order]
        track_lats   = track_lats[order]
        track_lons   = track_lons[order]

        obs_epochs = np.array([_ts(v) for v in obs_times])

        cen_lats = np.interp(obs_epochs, track_epochs, track_lats)
        cen_lons = np.interp(obs_epochs, track_epochs, track_lons)

        dlat = np.radians(obs_lats - cen_lats)
        dlon = np.radians(obs_lons - cen_lons)
        mean_lat = np.radians((obs_lats + cen_lats) / 2.0)
        x_km = EARTH_R_KM * dlon * np.cos(mean_lat)   
        y_km = EARTH_R_KM * dlat                       

        range_km    = np.sqrt(x_km**2 + y_km**2)
        azimuth_deg = np.degrees(np.arctan2(x_km, y_km)) % 360

        mean_heading = None
        if up_convention == "Relative to Storm Motion":
            dlat_tr = np.diff(track_lats)
            dlon_tr = np.diff(track_lons)
            mean_lat_tr = np.radians((track_lats[:-1] + track_lats[1:]) / 2.0)
            dy_tr = EARTH_R_KM * np.radians(dlat_tr)
            dx_tr = EARTH_R_KM * np.radians(dlon_tr) * np.cos(mean_lat_tr)
            headings = np.degrees(np.arctan2(dx_tr, dy_tr)) % 360
            mean_heading = float(np.nanmedian(headings))

            theta_rad = np.radians(mean_heading)
            x_rot =  x_km * np.cos(theta_rad) + y_km * np.sin(theta_rad)
            y_rot = -x_km * np.sin(theta_rad) + y_km * np.cos(theta_rad)
            x_km, y_km = x_rot, y_rot

            azimuth_deg = (azimuth_deg - mean_heading) % 360

        return x_km, y_km, range_km, azimuth_deg, mean_heading

    def get_sr_max_range(self, group_name, sr_track_grp, df_override=None):
        """
        Returns the maximum storm-relative range (km) across observations,
        snapped up to the next clean ring-spacing multiple.
        df_override: pre-filtered DataFrame to use instead of the full group.
        """
        if group_name not in self.data or sr_track_grp not in self.data:
            return 500.0
        df = df_override if df_override is not None else self.data[group_name]
        cols_lower = {c.lower(): c for c in df.columns}
        lat_col  = next((cols_lower[c] for c in ['lat', 'latitude', 'clat']  if c in cols_lower), None)
        lon_col  = next((cols_lower[c] for c in ['lon', 'longitude', 'clon'] if c in cols_lower), None)
        time_col = cols_lower.get('time')
        if not all([lat_col, lon_col, time_col]):
            return 500.0
        df = df.dropna(subset=[lat_col, lon_col, time_col])
        if df.empty:
            return 500.0
        result = self._to_storm_relative(
            df[lon_col].values, df[lat_col].values,
            df[time_col].values, sr_track_grp, "Relative to North"
        )
        if result is None:
            return 500.0
        _, _, range_km, _, _ = result
        raw_max = float(np.nanmax(range_km))
        ring_spacing = 25.0 if raw_max <= 150 else 50.0 if raw_max <= 500 else 100.0
        return float(np.ceil(raw_max / ring_spacing) * ring_spacing)

    def plot_storm_relative(self, group_name, variable, z_con,
                            domain_bounds, sr_track_grp,
                            up_convention="Relative to North",
                            thinning_pct=None, marker_size_pct=100,
                            time_bounds=None, color_scale="Linear scale",
                            show_center=True, cen_mode="Display Location Only"):
        """
        Plots observations in storm-relative Cartesian coordinates (km from
        storm center). The plot area is square with equal axes; a circular
        border at the maximum range, range rings at regular intervals, and
        cardinal/motion spokes are overlaid.

        Returns (fig, plot_df) matching the signature of plot().
        """
        if group_name not in self.data:
            return None, None

        df = self.data[group_name].copy()
        cols_lower = {c.lower(): c for c in df.columns}

        lat_col  = next((cols_lower[c] for c in ['lat', 'latitude', 'clat']  if c in cols_lower), None)
        lon_col  = next((cols_lower[c] for c in ['lon', 'longitude', 'clon'] if c in cols_lower), None)
        time_col = cols_lower.get('time')
        if not all([lat_col, lon_col, time_col, variable in df.columns]):
            return None, None

        _var_conf_sr = GLOBAL_VAR_CONFIG.get(variable.lower(), {})
        if z_con:
            zcol = z_con['col']
            if zcol in df.columns:
                zv = df[zcol] / 100.0 if z_con.get('convert_pa_to_hpa') else df[zcol]
                df = df[np.abs(zv - z_con['val']) <= z_con['tol']]

        if time_bounds and time_col in df.columns:
            df = df[(df[time_col] >= time_bounds['min']) &
                    (df[time_col] <= time_bounds['max'])]

        df = df.dropna(subset=[lat_col, lon_col, time_col, variable])
        if df.empty:
            return None, None

        if thinning_pct and thinning_pct < 100:
            df = df.sample(frac=thinning_pct / 100.0, random_state=42)

        result = self._to_storm_relative(
            df[lon_col].values, df[lat_col].values,
            df[time_col].values, sr_track_grp, up_convention
        )
        if result is None:
            return None, None

        x_km, y_km, range_km, azimuth_deg, _ = result

        sr_max_range = None
        if domain_bounds and '_sr_max_range_km' in domain_bounds:
            sr_max_range = float(domain_bounds['_sr_max_range_km'])
        if sr_max_range is not None:
            mask = range_km <= sr_max_range
            x_km        = x_km[mask]
            y_km        = y_km[mask]
            range_km    = range_km[mask]
            azimuth_deg = azimuth_deg[mask]
            df          = df[mask]

        if domain_bounds and 'z_min' in domain_bounds and 'z_col' in domain_bounds:
            z_col_sr = domain_bounds['z_col']
            if z_col_sr in df.columns:
                z_v = df[z_col_sr] / 100.0 if domain_bounds.get('z_convert') else df[z_col_sr]
                vmask = (z_v >= domain_bounds['z_min']) & (z_v <= domain_bounds['z_max'])
                x_km        = x_km[vmask.values]
                y_km        = y_km[vmask.values]
                range_km    = range_km[vmask.values]
                azimuth_deg = azimuth_deg[vmask.values]
                df          = df[vmask]

        plot_df = df.copy()
        plot_df['_sr_x_km']   = x_km
        plot_df['_sr_y_km']   = y_km
        plot_df['_sr_range']  = range_km
        plot_df['_sr_az']     = azimuth_deg

        _filtered_sr_vals = plot_df[variable].dropna().values
        if variable.lower() == 'time':
            _tr = self._convert_time_to_relative(_filtered_sr_vals)
            if _tr is not None:
                _filtered_sr_vals = _tr[0]
        _full_cmin = float(_var_conf_sr['cmin']) if _var_conf_sr.get('cmin') is not None else (
            float(np.nanmin(_filtered_sr_vals)) if len(_filtered_sr_vals) > 0 else 0.0)
        _full_cmax = float(_var_conf_sr['cmax']) if _var_conf_sr.get('cmax') is not None else (
            float(np.nanmax(_filtered_sr_vals)) if len(_filtered_sr_vals) > 0 else 1.0)
        if variable.lower() == 'time':
            _full_cmin = max(_full_cmin, -10800.0)
            _full_cmax = min(_full_cmax,  10800.0)

        var_conf   = GLOBAL_VAR_CONFIG.get(variable.lower(), {})
        cmap       = var_conf.get('colorscale', 'Jet')
        cmid_conf  = var_conf.get('cmid')
        color_vals = plot_df[variable].values
        cb_title   = self._get_var_display_name(group_name, variable)

        cb_tickvals, cb_ticktext = None, None
        if variable.lower() == 'time':
            _ax = {}
            color_vals = self._apply_time_axis(variable, color_vals, _ax, is_x=False)
            cb_tickvals = _ax.get('tickvals')
            cb_ticktext = _ax.get('ticktext')
            cb_title = "Time rel. to cycle center"

        cmin = _full_cmin
        cmax = _full_cmax
        cmid = float(cmid_conf) if cmid_conf is not None else None

        if color_scale == "Log scale":
            pos_mask = color_vals > 0
            log_c    = np.full_like(color_vals, np.nan, dtype=float)
            log_c[pos_mask] = np.log10(color_vals[pos_mask])
            color_vals = log_c
            real_cmin = _full_cmin if _full_cmin > 0 else (float(np.nanmin(plot_df[variable].values[plot_df[variable].values > 0])) if pos_mask.any() else 1e-3)
            real_cmax = _full_cmax if _full_cmax > 0 else (float(np.nanmax(plot_df[variable].values[plot_df[variable].values > 0])) if pos_mask.any() else 1.0)
            cmin = np.log10(real_cmin)
            cmax = np.log10(real_cmax)
            cmid = None
            mn, mx = int(np.floor(cmin)), int(np.ceil(cmax))
            cb_tickvals = np.arange(mn, mx + 1, dtype=float) if mx > mn else [cmin, cmax]
            cb_ticktext = [f"1e{int(p)}" if p < -3 or p > 3 else f"{10**p:g}"
                           for p in cb_tickvals]

        sz_mult = marker_size_pct / 100.0

        raw_max = float(np.nanmax(range_km)) if len(range_km) > 0 else 200.0
        padded  = sr_max_range if sr_max_range is not None else raw_max

        _candidates = [1, 2, 5, 10, 25, 50, 100, 150, 200, 250, 500]
        ring_spacing = next(
            (c for c in _candidates if 3 <= padded / c <= 8),
            _candidates[-1] if padded > 250 else _candidates[0]
        )
        max_range  = np.ceil(padded / ring_spacing) * ring_spacing
        ring_radii = np.arange(ring_spacing, max_range + ring_spacing * 0.01, ring_spacing)

        theta_ring = np.linspace(0, 2 * np.pi, 360)
        spoke_len  = max_range  

        fig = go.Figure()

        for r in ring_radii:
            fig.add_trace(go.Scatter(
                x=r * np.sin(theta_ring),
                y=r * np.cos(theta_ring),
                mode='lines',
                line=dict(color=CLR_PLOT_GRID, width=1, dash='dot'),
                showlegend=False, hoverinfo='skip',
                name=f'{r:.0f} km ring'
            ))

        for angle_deg in [0, 90, 180, 270]:
            sx = spoke_len * np.sin(np.radians(angle_deg))
            sy = spoke_len * np.cos(np.radians(angle_deg))
            fig.add_trace(go.Scatter(
                x=[0, sx], y=[0, sy],
                mode='lines',
                line=dict(color=CLR_PLOT_GRID, width=1),
                showlegend=False, hoverinfo='skip'
            ))

        hover_text = [
            f"Range: {r:.1f} km<br>Az: {a:.1f}°<br>{variable}: {v:.2f}"
            if not (np.isnan(r) or np.isnan(v)) else "NaN"
            for r, a, v in zip(range_km, azimuth_deg, plot_df[variable].values)
        ]
        fig.add_trace(go.Scatter(
            x=x_km, y=y_km,
            mode='markers',
            marker=dict(
                size=9 * sz_mult,
                color=color_vals,
                colorscale=cmap,
                cmin=cmin, cmax=cmax, cmid=cmid,
                showscale=True,
                colorbar=dict(
                    len=0.8, thickness=15,
                    tickfont=dict(size=FS_PLOT_TICK),
                    tickvals=cb_tickvals,
                    ticktext=cb_ticktext
                )
            ),
            text=hover_text,
            hoverinfo='text',
            showlegend=False
        ))

        if show_center:
            motion_dir = None
            if cen_mode == "Display As Motion Vector":
                motion_str = str(self.metadata.get('info', {}).get('storm_motion', ''))
                nums = re.findall(r'[-+]?\d*\.?\d+', motion_str)
                if len(nums) >= 2:
                    motion_dir = float(nums[1])   

            if motion_dir is not None:
                dir_rad = math.radians(motion_dir)
                dx = math.sin(dir_rad)
                dy = math.cos(dir_rad)

                if up_convention == "Relative to Storm Motion":
                    track_df = self.data[sr_track_grp]
                    tc = {c.lower(): c for c in track_df.columns}
                    t_col_tr = tc.get('time')
                    la_col   = next((tc[c] for c in ['lat', 'latitude']  if c in tc), None)
                    lo_col   = next((tc[c] for c in ['lon', 'longitude'] if c in tc), None)
                    if all([t_col_tr, la_col, lo_col]):
                        tr = track_df[[t_col_tr, la_col, lo_col]].dropna().sort_values(t_col_tr)
                        if len(tr) >= 2:
                            dlat_tr = np.diff(tr[la_col].values)
                            dlon_tr = np.diff(tr[lo_col].values)
                            mean_lat_tr = np.radians(tr[la_col].values[:-1])
                            dx_tr = EARTH_R_KM * np.radians(dlon_tr) * np.cos(mean_lat_tr)
                            dy_tr = EARTH_R_KM * np.radians(dlat_tr)
                            headings = (np.degrees(np.arctan2(dx_tr, dy_tr))) % 360
                            mean_heading = float(np.nanmedian(headings))
                            rotated_dir = motion_dir - mean_heading
                            rot_rad = math.radians(rotated_dir)
                            dx = math.sin(rot_rad)
                            dy = math.cos(rot_rad)

                arrow_len = max_range * 0.12
                tip_x = dx * arrow_len
                tip_y = dy * arrow_len

                wing_len = arrow_len * 0.3
                wing_angle = math.radians(150)
                base_angle = math.atan2(dx, dy)
                w1_x = tip_x + wing_len * math.sin(base_angle + wing_angle)
                w1_y = tip_y + wing_len * math.cos(base_angle + wing_angle)
                w2_x = tip_x + wing_len * math.sin(base_angle - wing_angle)
                w2_y = tip_y + wing_len * math.cos(base_angle - wing_angle)

                fig.add_trace(go.Scatter(
                    x=[0, tip_x, w1_x, tip_x, w2_x],
                    y=[0, tip_y, w1_y, tip_y, w2_y],
                    mode='lines',
                    line=dict(color=CLR_PRIMARY, width=2),
                    showlegend=False, hoverinfo='skip'
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=[0], y=[0], mode='markers+text',
                    marker=dict(symbol='x', size=14, color=CLR_PRIMARY, line=dict(width=2)),
                    text=['TC'], textposition='top center',
                    textfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                    showlegend=False, hoverinfo='text',
                    hovertext=['Storm center']
                ))

        display_name = self._get_var_display_name(group_name, variable)
        up_label     = "North" if up_convention == "Relative to North" else "Storm Motion"
        nice_title   = self._format_title(group_name, variable, f"Storm-Relative | Up: {up_label}")
        _MT          = self._title_top_margin(nice_title)
        _FIG_W       = 700
        _ML, _MR, _MB = 80, 120, 80
        _FIG_H       = _FIG_W  

        axis_lim = max_range

        fig.update_layout(
            title={'text': nice_title, 'x': 0.5, 'xanchor': 'center',
                   'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
            width=_FIG_W, height=_FIG_H,
            autosize=False,
            showlegend=False,
            xaxis=dict(
                title=(
                    "Cross-Track Distance from Center (km)"
                    if up_convention == "Relative to Storm Motion"
                    else "East–West Distance from Center (km)"
                ),
                tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                range=[-axis_lim, axis_lim],
                dtick=ring_spacing,
                tick0=0,
                showgrid=True, gridcolor=CLR_PLOT_GRID, zeroline=False,
                showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                constrain='domain', scaleanchor='y', scaleratio=1,
            ),
            yaxis=dict(
                title=(
                    "Along-Track Distance from Center (km)"
                    if up_convention == "Relative to Storm Motion"
                    else "North–South Distance from Center (km)"
                ),
                tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                range=[-axis_lim, axis_lim],
                dtick=ring_spacing,
                tick0=0,
                showgrid=True, gridcolor=CLR_PLOT_GRID, zeroline=False,
                showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
                constrain='domain',
            ),
            plot_bgcolor=CLR_PLOT_BG,
            paper_bgcolor=CLR_PLOT_BG,
            margin=dict(autoexpand=False, l=_ML, r=_MR, t=_MT, b=_MB),
        )

        return fig, plot_df

    def plot_radial_height(self, group_name, variable, sr_track_grp,
                           domain_bounds=None, thinning_pct=None,
                           marker_size_pct=100, time_bounds=None,
                           color_scale="Linear scale", rh_z_col=None):
        """
        Radial-Height Profile (storm-relative).

        Converts observations to storm-relative polar coordinates using
        _to_storm_relative(), then plots range_km (X) vs the selected Z column
        (height or pressure) on Y, coloring markers by `variable`.
        All azimuths are collapsed — every observation is shown regardless of
        its bearing from the storm center.

        Returns (fig, plot_df) matching the signature of plot().
        """
        if group_name not in self.data:
            return None, None

        df = self.data[group_name].copy()
        cols_lower = {c.lower(): c for c in df.columns}

        lat_col  = next((cols_lower[c] for c in ['lat', 'latitude', 'clat']  if c in cols_lower), None)
        lon_col  = next((cols_lower[c] for c in ['lon', 'longitude', 'clon'] if c in cols_lower), None)
        time_col = cols_lower.get('time')

        if rh_z_col and rh_z_col in df.columns:
            z_col = rh_z_col
        else:
            z_col = next((cols_lower[c] for c in
                          ['height', 'ght', 'altitude', 'elev', 'pres', 'pressure', 'p']
                          if c in cols_lower), None)

        if not all([lat_col, lon_col, time_col, z_col, variable in df.columns]):
            return None, None

        if time_bounds and time_col in df.columns:
            df = df[(df[time_col] >= time_bounds['min']) &
                    (df[time_col] <= time_bounds['max'])]

        df = df.dropna(subset=[lat_col, lon_col, time_col, z_col, variable])
        if df.empty:
            return None, None

        if thinning_pct and thinning_pct < 100:
            df = df.sample(frac=thinning_pct / 100.0, random_state=42)

        result = self._to_storm_relative(
            df[lon_col].values, df[lat_col].values,
            df[time_col].values, sr_track_grp, "Relative to North"
        )
        if result is None:
            return None, None

        _, _, range_km, _, _ = result

        sr_max_range = None
        if domain_bounds and '_sr_max_range_km' in domain_bounds:
            sr_max_range = float(domain_bounds['_sr_max_range_km'])
        if sr_max_range is not None:
            mask     = range_km <= sr_max_range
            range_km = range_km[mask]
            df       = df[mask]

        if len(df) == 0:
            return None, None

        plot_df = df.copy()
        plot_df['_rh_range_km'] = range_km

        if domain_bounds and 'z_min' in domain_bounds and 'z_col' in domain_bounds:
            z_b_col = domain_bounds['z_col']
            if z_b_col in plot_df.columns:
                z_b_vals = plot_df[z_b_col].copy()
                if domain_bounds.get('z_convert'):
                    z_b_vals = z_b_vals / 100.0
                plot_df = plot_df[(z_b_vals >= domain_bounds['z_min']) & (z_b_vals <= domain_bounds['z_max'])]
                if len(plot_df) == 0:
                    return None, None

        z_vals     = plot_df[z_col].values
        color_vals = plot_df[variable].values

        is_pres  = any(p in z_col.lower() for p in ['pres', 'pressure', 'p'])
        z_meta   = self.var_attrs.get(group_name, {}).get(z_col, {})
        z_units  = decode_metadata(z_meta.get('units', 'hPa' if is_pres else 'm'))
        if is_pres and 'Pa' in z_units and 'hPa' not in z_units:
            z_vals  = z_vals / 100.0
            z_units = 'hPa'
        z_label  = f"{'Pressure' if is_pres else 'Height'} ({z_units})"

        var_conf   = GLOBAL_VAR_CONFIG.get(variable.lower(), {})
        cmap       = var_conf.get('colorscale', 'Jet')
        cmid_conf  = var_conf.get('cmid')
        cmid       = float(cmid_conf) if cmid_conf is not None else None
        cb_tickvals, cb_ticktext = None, None

        _color_work = color_vals.copy().astype(float)
        if variable.lower() == 'time':
            _ax = {}
            _color_work = self._apply_time_axis(variable, _color_work, _ax, is_x=False)
            cb_tickvals = _ax.get('tickvals')
            cb_ticktext = _ax.get('ticktext')

        cmin_conf = var_conf.get('cmin')
        cmax_conf = var_conf.get('cmax')
        cmin = float(cmin_conf) if cmin_conf is not None else float(np.nanmin(_color_work))
        cmax = float(cmax_conf) if cmax_conf is not None else float(np.nanmax(_color_work))

        if color_scale == "Log scale":
            pos_mask = _color_work > 0
            log_c    = np.full_like(_color_work, np.nan, dtype=float)
            log_c[pos_mask] = np.log10(_color_work[pos_mask])
            _color_work = log_c
            real_cmin = cmin if cmin > 0 else (float(np.nanmin(color_vals[pos_mask])) if pos_mask.any() else 1e-3)
            real_cmax = cmax if cmax > 0 else (float(np.nanmax(color_vals[pos_mask])) if pos_mask.any() else 1.0)
            cmin = np.log10(real_cmin)
            cmax = np.log10(real_cmax)
            cmid = None
            mn, mx = int(np.floor(cmin)), int(np.ceil(cmax))
            cb_tickvals = np.arange(mn, mx + 1, dtype=float) if mx > mn else [cmin, cmax]
            cb_ticktext = [f"1e{int(p)}" if p < -3 or p > 3 else f"{10**p:g}" for p in cb_tickvals]

        x_max_raw = float(np.nanmax(range_km)) if len(range_km) > 0 else 200.0
        x_max     = sr_max_range if sr_max_range is not None else x_max_raw
        _candidates = [10, 25, 50, 100, 150, 200, 250, 500]
        ring_spacing = next((c for c in _candidates if 3 <= x_max / c <= 8), _candidates[-1])
        x_axis_max = np.ceil(x_max / ring_spacing) * ring_spacing

        has_z_bounds = (domain_bounds and 'z_min' in domain_bounds and
                        domain_bounds.get('z_col') == z_col)
        if is_pres:
            if has_z_bounds:
                y_axis_min = domain_bounds['z_min']
                y_axis_max = domain_bounds['z_max']
            else:
                y_min_raw = float(np.nanmin(z_vals)) if len(z_vals) > 0 else 100.0
                y_max_raw = float(np.nanmax(z_vals)) if len(z_vals) > 0 else 1013.0
                for step in [10, 25, 50, 100]:
                    y_axis_min = np.floor(y_min_raw / step) * step
                    y_axis_max = np.ceil(y_max_raw  / step) * step
                    if (y_axis_max - y_axis_min) / step <= 20:
                        break
            y_range   = [y_axis_max, y_axis_min]   
            y_autorev = False
        else:
            if has_z_bounds:
                y_axis_min = domain_bounds['z_min']
                y_axis_max = domain_bounds['z_max']
            else:
                y_max_raw = float(np.nanmax(z_vals)) if len(z_vals) > 0 else 15000.0
                for step in [500, 1000, 2000, 2500, 5000, 10000]:
                    y_axis_max = np.ceil(y_max_raw / step) * step
                    if y_axis_max / step <= 20:
                        break
                y_axis_min = 0
            y_range   = [y_axis_min, y_axis_max]
            y_autorev = False

        sz_mult      = marker_size_pct / 100.0
        display_name = self._get_var_display_name(group_name, variable)

        z_disp_label = 'Pressure' if is_pres else 'Height'
        z_unit_str   = z_units
        hover_text = [
            f"Range: {r:.1f} km<br>{z_disp_label}: {z:.1f} {z_unit_str}<br>{variable}: {v:.2f}"
            if not (np.isnan(r) or np.isnan(z) or np.isnan(v)) else "NaN"
            for r, z, v in zip(range_km, z_vals, color_vals)
        ]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=range_km,
            y=z_vals,
            mode='markers',
            marker=dict(
                size=9 * sz_mult,
                color=_color_work,
                colorscale=cmap,
                cmin=cmin, cmax=cmax, cmid=cmid,
                showscale=True,
                colorbar=dict(
                    len=0.8, thickness=15,
                    tickfont=dict(size=FS_PLOT_TICK),
                    tickvals=cb_tickvals,
                    ticktext=cb_ticktext,
                )
            ),
            text=hover_text,
            hoverinfo='text',
            showlegend=False,
        ))

        nice_title = self._format_title(group_name, variable, "Radial-Height Profile | Storm-Relative")
        _MT = self._title_top_margin(nice_title)

        fig.update_layout(
            title={'text': nice_title, 'x': 0.5, 'xanchor': 'center',
                   'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
            width=800, height=600,
            autosize=False,
            showlegend=False,
            xaxis=dict(
                title='Radius from Storm Center (km)',
                range=[0, x_axis_max],
                dtick=ring_spacing,
                tick0=0,
                tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                showgrid=True, gridcolor=CLR_PLOT_GRID, zeroline=False,
                showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
            ),
            yaxis=dict(
                title=z_label,
                range=y_range,
                tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
                showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True,
            ),
            plot_bgcolor=CLR_PLOT_BG,
            paper_bgcolor=CLR_PLOT_BG,
            margin=dict(l=80, r=120, t=_MT, b=60),
        )

        return fig, plot_df

    def plot_histogram(self, group_name, variable, nbins=None, normalization="None", reverse_axes=False, render_as_line=False):
        """
        Renders a 1D histogram or line plot representing the distribution of a variable.
        """
        if group_name not in self.data: return None
        
        df = self.data[group_name].copy()
        if variable not in df.columns: return None

        plot_df = df.dropna(subset=[variable])
        if plot_df.empty: return None

        vals = plot_df[variable].values

        display_name = self._get_var_display_name(group_name, variable)
        nice_title = self._format_title(group_name, variable, "")

        histnorm = 'percent' if normalization == "Full Normalization (all bins sum to 100%)" else None
        count_label = 'Percentage (%)' if normalization == "Full Normalization (all bins sum to 100%)" else 'Count'

        def _make_var_axis(is_x):
            d = dict(
                title=display_name,
                tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
                showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True
            )
            if variable.lower() == 'p' or 'pres' in variable.lower() or variable.lower().endswith('_p'):
                d['autorange'] = 'reversed'
            return d

        def _make_count_axis():
            return dict(
                title=count_label,
                tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
                showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
                showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True
            )

        fig = go.Figure()

        if reverse_axes:
            var_axis   = _make_var_axis(is_x=False)
            plot_vals  = self._apply_time_axis(variable, vals, var_axis, is_x=False)
            count_axis = _make_count_axis()
            x_axis, y_axis = count_axis, var_axis
        else:
            var_axis   = _make_var_axis(is_x=True)
            plot_vals  = self._apply_time_axis(variable, vals, var_axis, is_x=True)
            count_axis = _make_count_axis()
            x_axis, y_axis = var_axis, count_axis

        n_bins  = nbins if nbins else 50
        finite  = plot_vals[np.isfinite(plot_vals)]
        counts, edges = np.histogram(finite, bins=n_bins)
        centers = (edges[:-1] + edges[1:]) / 2
        widths  = edges[1:] - edges[:-1]
        display_counts = counts / counts.sum() * 100 if normalization == "Full Normalization (all bins sum to 100%)" else counts.astype(float)

        if render_as_line:
            if reverse_axes:
                fig.add_trace(go.Scatter(
                    x=display_counts, y=centers, mode='lines',
                    line=dict(color=CLR_EXTRA, width=2), name=display_name, showlegend=False
                ))
            else:
                fig.add_trace(go.Scatter(
                    x=centers, y=display_counts, mode='lines',
                    line=dict(color=CLR_EXTRA, width=2), name=display_name, showlegend=False
                ))
        else:
            if reverse_axes:
                fig.add_trace(go.Bar(
                    x=display_counts, y=centers, orientation='h',
                    width=widths, marker_color=CLR_EXTRA, opacity=0.85,
                    name=display_name, showlegend=False
                ))
            else:
                fig.add_trace(go.Bar(
                    x=centers, y=display_counts, orientation='v',
                    width=widths, marker_color=CLR_EXTRA, opacity=0.85,
                    name=display_name, showlegend=False
                ))

        fig.update_layout(xaxis=x_axis, yaxis=y_axis, bargap=0)

        fig.update_layout(
            title={'text': nice_title, 'x': 0.5, 'xanchor': 'center', 'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
            width=800, height=600,
            showlegend=False,
            plot_bgcolor=CLR_PLOT_BG,
            paper_bgcolor=CLR_PLOT_BG,
            margin=dict(l=60, r=40, t=self._title_top_margin(nice_title), b=60),
        )
        return fig
    
    def _compute_2d_normalization(self, x_vals, y_vals, nbinsx, nbinsy, normalization):
        """
        Builds a 2D density matrix and applies row, column, or full percentage normalization.
        """
        nx = nbinsx if nbinsx is not None else 50
        ny = nbinsy if nbinsy is not None else 50

        # Drop any rows where either axis is non-finite (NaN or inf),
        # which can arise after time conversion or missing-value replacement.
        x_vals = np.asarray(x_vals, dtype=float)
        y_vals = np.asarray(y_vals, dtype=float)
        finite_mask = np.isfinite(x_vals) & np.isfinite(y_vals)
        x_vals = x_vals[finite_mask]
        y_vals = y_vals[finite_mask]

        if len(x_vals) == 0:
            return np.zeros((ny, nx)), np.zeros(nx), np.zeros(ny)

        H, xedges, yedges = np.histogram2d(x_vals, y_vals, bins=[nx, ny])
        
        H = H.T
        
        if normalization == "Normalize Fully":
            total = H.sum()
            if total > 0:
                H = (H / total) * 100.0
        elif normalization == "Normalize within each Y bin":
            row_sums = H.sum(axis=1, keepdims=True)
            H = np.divide(H, row_sums, out=np.zeros_like(H), where=row_sums != 0) * 100.0
        elif normalization == "Normalize within each X bin":
            col_sums = H.sum(axis=0, keepdims=True)
            H = np.divide(H, col_sums, out=np.zeros_like(H), where=col_sums != 0) * 100.0
            
        x_centers = (xedges[:-1] + xedges[1:]) / 2
        y_centers = (yedges[:-1] + yedges[1:]) / 2
        
        return H, x_centers, y_centers
    
    def plot_histogram_2d(self, group_name, variable, coord_var, nbinsx=None, nbinsy=None, reverse_axes=False, normalization="None"):
        """
        Renders a 2D histogram (heatmap) mapping the density of two variables 
        against each other.
        """
        if group_name not in self.data: return None
        
        df = self.data[group_name].copy()
        if variable not in df.columns or coord_var not in df.columns: return None

        plot_df = df.dropna(subset=[variable, coord_var])
        if plot_df.empty: return None

        primary_name   = self._get_var_display_name(group_name, variable)
        secondary_name = self._get_var_display_name(group_name, coord_var)
        if reverse_axes:
            x_vals, y_vals = plot_df[variable].values, plot_df[coord_var].values
            x_name = f"{primary_name} (Primary)"
            y_name = f"{secondary_name} (Secondary)"
            x_var_col, y_var_col = variable, coord_var
        else:
            x_vals, y_vals = plot_df[coord_var].values, plot_df[variable].values
            x_name = f"{secondary_name} (Secondary)"
            y_name = f"{primary_name} (Primary)"
            x_var_col, y_var_col = coord_var, variable

        nice_title = self._format_title(group_name, variable, f"Binned by {secondary_name}")

        _var_key = variable[len('_log10_'):] if variable.startswith('_log10_') else variable
        var_conf = GLOBAL_VAR_CONFIG.get(_var_key.lower(), {})
        cmap_name = var_conf.get('colorscale', 'Viridis')
        
        try:
            import plotly.colors
            base_cmap = plotly.colors.get_colorscale(cmap_name)
            custom_cmap = []
            for val, clr in base_cmap:
                if float(val) == 0.0:
                    custom_cmap.append([0.0, 'rgba(0,0,0,0)'])
                else:
                    custom_cmap.append([float(val), clr])
        except Exception:
            custom_cmap = cmap_name

        cb_title = 'Percentage (%)' if normalization not in ("None", None) else 'Count'

        xaxis_dict = dict(
            title=x_name, 
            tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
            showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
            showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True
        )
        yaxis_dict = dict(
            title=y_name, 
            tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
            showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
            showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True
        )

        if x_var_col.lower() == 'p' or 'pres' in x_var_col.lower() or x_var_col.lower().endswith('_p'):
            xaxis_dict['autorange'] = 'reversed'
        if y_var_col.lower() == 'p' or 'pres' in y_var_col.lower() or y_var_col.lower().endswith('_p'):
            yaxis_dict['autorange'] = 'reversed'

        x_vals = self._apply_time_axis(x_var_col, x_vals, xaxis_dict)
        y_vals = self._apply_time_axis(y_var_col, y_vals, yaxis_dict, is_x=False)

        _norm = normalization
        if normalization == "Normalize within each Primary bin":
            _norm = "Normalize within each X bin" if reverse_axes else "Normalize within each Y bin"
        elif normalization == "Normalize within each Secondary bin":
            _norm = "Normalize within each Y bin" if reverse_axes else "Normalize within each X bin"
        H, x_centers, y_centers = self._compute_2d_normalization(x_vals, y_vals, nbinsx, nbinsy, _norm)

        fig = go.Figure()
        fig.add_trace(go.Heatmap(
            z=H,
            x=x_centers,
            y=y_centers,
            colorscale=custom_cmap,
            zmin=0,
            colorbar=dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK))
        ))

        fig.update_layout(
            title={'text': nice_title, 'x': 0.5, 'xanchor': 'center', 'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
            width=800, height=600,
            showlegend=False,
            xaxis=xaxis_dict,
            yaxis=yaxis_dict,
            plot_bgcolor=CLR_PLOT_BG,    
            paper_bgcolor=CLR_PLOT_BG,   
            margin=dict(l=60, r=40, t=self._title_top_margin(nice_title), b=60),
        )
        return fig

    def plot_scatter(self, group_name, variable, coord_var, color_var=None, show_trendline=False, reverse_axes=False, marker_size_pct=100):
        """
        Renders a scatter plot of a variable (X-axis) against a coordinate variable (Y-axis).
        Color mapping can represent point density, a Z-Coordinate, or the variable itself.
        """
        if group_name not in self.data: return None

        df = self.data[group_name].copy()
        if variable not in df.columns or coord_var not in df.columns: return None

        plot_df = df.dropna(subset=[variable, coord_var])
        if plot_df.empty: return None

        x_vals = plot_df[variable].values
        y_vals = plot_df[coord_var].values
        x_var_col = variable
        y_var_col = coord_var

        if reverse_axes:
            x_vals, y_vals = y_vals, x_vals
            x_var_col, y_var_col = coord_var, variable

        x_name = self._get_var_display_name(group_name, x_var_col)
        y_name = self._get_var_display_name(group_name, y_var_col)
        _color_suffix = f", Color: {self._get_var_display_name(group_name, color_var)}" if color_var and color_var in plot_df.columns else ""
        nice_title = self._format_title(group_name, y_var_col, f"vs. {x_name}{_color_suffix}")

        if color_var and color_var in plot_df.columns:
            color_vals = plot_df[color_var].values
            var_conf   = GLOBAL_VAR_CONFIG.get(color_var.lower(), {})
            cmap       = var_conf.get('colorscale', 'Viridis')
            cmid       = var_conf.get('cmid', None)
        else:
            H, xedges, yedges = np.histogram2d(x_vals, y_vals, bins=50)
            xi = np.clip(np.searchsorted(xedges, x_vals) - 1, 0, H.shape[0] - 1)
            yi = np.clip(np.searchsorted(yedges, y_vals) - 1, 0, H.shape[1] - 1)
            color_vals = H[xi, yi]
            cmap       = "Viridis"
            cmid       = None

        xaxis_dict = dict(
            title=x_name,
            tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
            showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
            showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True
        )
        yaxis_dict = dict(
            title=y_name,
            tickfont=dict(size=FS_PLOT_TICK, color=CLR_PRIMARY),
            showgrid=True, gridcolor=CLR_PLOT_GRID, nticks=TARGET_PLOT_TICKS,
            showline=True, linewidth=1.5, linecolor=CLR_PRIMARY, mirror=True
        )
        if x_var_col.lower() == 'p' or 'pres' in x_var_col.lower() or x_var_col.lower().endswith('_p'):
            xaxis_dict['autorange'] = 'reversed'
        if y_var_col.lower() == 'p' or 'pres' in y_var_col.lower() or y_var_col.lower().endswith('_p'):
            yaxis_dict['autorange'] = 'reversed'

        x_vals = self._apply_time_axis(x_var_col, x_vals, xaxis_dict)
        y_vals = self._apply_time_axis(y_var_col, y_vals, yaxis_dict, is_x=False)

        fig = go.Figure()

        sz = max(1, int(5 * marker_size_pct / 100))
        if color_var and color_var in plot_df.columns:
            marker_dict = dict(
                size=sz,
                color=color_vals,
                colorscale=cmap,
                cmid=cmid,
                showscale=True,
                colorbar=dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK))
            )
        else:
            marker_dict = dict(size=sz, color=CLR_PRIMARY)

        fig.add_trace(go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers',
            marker=marker_dict,
            name=x_name,
            showlegend=False
        ))

        if show_trendline:
            valid = np.isfinite(x_vals) & np.isfinite(y_vals)
            if valid.sum() >= 2:
                m, b = np.polyfit(x_vals[valid], y_vals[valid], 1)
                x_line = np.array([x_vals[valid].min(), x_vals[valid].max()])
                y_line = m * x_line + b
                fig.add_trace(go.Scatter(
                    x=x_line, y=y_line, mode='lines',
                    line=dict(color=CLR_PRIMARY, width=2, dash='dash'),
                    name='Trendline', showlegend=False
                ))

        fig.update_layout(
            title={'text': nice_title, 'x': 0.5, 'xanchor': 'center', 'y': PLOT_TITLE_Y, 'yanchor': 'top', 'yref': 'container'},
            width=800, height=600,
            showlegend=False,
            xaxis=xaxis_dict,
            yaxis=yaxis_dict,
            plot_bgcolor=CLR_PLOT_BG,
            paper_bgcolor=CLR_PLOT_BG,
            margin=dict(l=60, r=40, t=self._title_top_margin(nice_title), b=60),
        )
        return fig


def add_flight_tracks(fig, data_pack, track_mapping, plot_track, selected_platform, is_3d, is_target_pres, proj_option="Bottom Only", domain_bounds=None):
    """
    Overlays flight track geometry onto a Cartesian Plotly figure (2D or 3D).
    In 3D mode, can project shadows onto the bottom or sidewalls of the domain bounding box.
    """
    for plat, track_group in track_mapping.items():
        track_df = data_pack['data'][track_group]
        
        t_lat_c = next((c for c in track_df.columns if c.lower() in ['lat', 'latitude']), None)
        t_lon_c = next((c for c in track_df.columns if c.lower() in ['lon', 'longitude']), None)
        is_visible = plot_track and selected_platform == plat
        
        if t_lat_c and t_lon_c:
            if not is_3d:
                use_geo = len(fig.data) > 0 and fig.data[0].type == 'scattergeo'
                if use_geo:
                    fig.add_trace(go.Scattergeo(
                        lon=track_df[t_lon_c], lat=track_df[t_lat_c], mode='lines',
                        line=dict(color='black', width=1), name=f'{plat} Flight Track',
                        showlegend=False, visible=is_visible
                    ))
                else:
                    fig.add_trace(go.Scatter(
                        x=track_df[t_lon_c], y=track_df[t_lat_c], mode='lines',
                        line=dict(color='black', width=1), name=f'{plat} Flight Track',
                        showlegend=False, visible=is_visible
                    ))
            else:
                t_z_options = [c for c in track_df.columns if c.lower() in (['pres', 'pressure', 'p'] if is_target_pres else ['height', 'ght', 'altitude', 'elev'])]
                t_z_c = t_z_options[0] if t_z_options else None
                
                if t_z_c:
                    t_z_vals = track_df[t_z_c].copy()

                    fig.add_trace(go.Scatter3d(
                        x=track_df[t_lon_c], y=track_df[t_lat_c], z=t_z_vals,
                        mode='lines', line=dict(color='black', width=2), 
                        name=f'{plat} Flight Track', showlegend=False, visible=is_visible
                    ))
                    
                    show_bottom = proj_option in ["Bottom Only", "Bottom + Sides"]
                    show_sides = proj_option in ["Sides Only", "Bottom + Sides"]
                    
                    if show_bottom:
                        if domain_bounds and 'z_min' in domain_bounds:
                            floor_z = domain_bounds['z_max'] if is_target_pres else domain_bounds['z_min']
                        else:
                            floor_z = max(_SURFACE_PRESSURE_HPA, np.nanmax(t_z_vals)) if is_target_pres else min(0.0, np.nanmin(t_z_vals))
                            
                        z_shadow = np.full_like(t_z_vals, floor_z)
                        
                        fig.add_trace(go.Scatter3d(
                            x=track_df[t_lon_c], y=track_df[t_lat_c], z=z_shadow,
                            mode='lines', line=dict(color='lightgray', width=2), 
                            name=f'{plat} Surface Reflection', showlegend=False, visible=is_visible
                        ))
                    
                    if show_sides:
                        lon_wall = domain_bounds['lon_min'] if domain_bounds else track_df[t_lon_c].min()
                        lat_wall = domain_bounds['lat_max'] if domain_bounds else track_df[t_lat_c].max()
                        
                        lon_shadow = np.full_like(track_df[t_lon_c], lon_wall)
                        fig.add_trace(go.Scatter3d(
                            x=lon_shadow, y=track_df[t_lat_c], z=t_z_vals,
                            mode='lines', line=dict(color='lightgray', width=2), 
                            name=f'{plat} Lon Wall Reflection', showlegend=False, visible=is_visible
                        ))
                        
                        lat_shadow = np.full_like(track_df[t_lat_c], lat_wall)
                        fig.add_trace(go.Scatter3d(
                            x=track_df[t_lon_c], y=lat_shadow, z=t_z_vals,
                            mode='lines', line=dict(color='lightgray', width=2), 
                            name=f'{plat} Lat Wall Reflection', showlegend=False, visible=is_visible
                        ))
    return fig
    
