# -*- coding: utf-8 -*-
"""
plotter_base.py
---------------
Base class for StormPlotter. Contains the constructor, all shared helper
methods, and the variable/coordinate introspection utilities.
"""

import math
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import GLOBAL_VAR_CONFIG, EARTH_R_KM, SURFACE_PRESSURE_HPA
from data_utils import decode_metadata
from ui_layout import (
    CLR_PRIMARY, CLR_PLOT_BG, CLR_PLOT_GRID, CLR_MUTED,
    CLR_EXTRA, FS_PLOT_TITLE, FS_PLOT_AXIS, FS_PLOT_TICK,
    TARGET_PLOT_TICKS, PLOT_TITLE_Y,
)

# ---------------------------------------------------------------------------
# Tunable display constants
# ---------------------------------------------------------------------------
_CONE_DOMAIN_FRACTION   = 0.03
_FIG_HEIGHT_BASE        = 800
_FIG_HEIGHT_Z_THRESHOLD = 0.6
_FIG_HEIGHT_Z_STRETCH   = 400


class StormPlotterBase:
    """
    Base class that holds shared state and helper utilities for all
    StormPlotter rendering methods.
    """

    def __init__(self, data_dict, track_data, metadata, var_attrs):
        self.data      = data_dict
        self.track     = track_data
        self.metadata  = metadata
        self.var_attrs = var_attrs

    def _get_color_setup(self, group_name, variable, color_scale):
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

    def _ensure_derived_spatial_coords(self, group_name):
        """
        Dynamically calculates Distance from Center, Azimuth from North, 
        and Azimuth from Storm Motion if not already present.
        """
        if group_name not in self.data or group_name.startswith('track_'):
            return
        df = self.data[group_name]
        
        if all(col in df.columns for col in ['dist_from_center', 'azimuth_north', 'azimuth_motion']):
            return

        from datetime import datetime, timezone

        track_grp = None
        for pref in ('track_spline_track', 'track_best_track'):
            if pref in self.data:
                track_grp = pref
                break
        if track_grp is None:
            for k in self.data:
                if k.startswith('track_'):
                    track_grp = k
                    break
        if track_grp is None:
            return

        tr     = self.data[track_grp]
        tcols  = {c.lower(): c for c in tr.columns}
        t_col  = tcols.get('time')
        lat_col = next((tcols[c] for c in ['lat', 'latitude', 'clat'] if c in tcols), None)
        lon_col = next((tcols[c] for c in ['lon', 'longitude', 'clon'] if c in tcols), None)
        if not all([t_col, lat_col, lon_col]):
            return

        def _ts(v):
            try:
                dt = datetime.strptime(f"{v:.0f}", '%Y%m%d%H%M%S')
                return dt.replace(tzinfo=timezone.utc).timestamp()
            except Exception:
                return np.nan

        te    = np.array([_ts(v) for v in tr[t_col].values])
        valid = np.isfinite(te)
        if valid.sum() < 2:
            return
            
        order    = np.argsort(te[valid])
        t_epochs = te[valid][order]
        t_lats   = tr[lat_col].values.astype(float)[valid][order]
        t_lons   = tr[lon_col].values.astype(float)[valid][order]

        dlat_tr = np.diff(t_lats)
        dlon_tr = np.diff(t_lons)
        mean_lat_tr = np.radians((t_lats[:-1] + t_lats[1:]) / 2.0)
        dy_tr = EARTH_R_KM * np.radians(dlat_tr)
        dx_tr = EARTH_R_KM * np.radians(dlon_tr) * np.cos(mean_lat_tr)
        headings = np.degrees(np.arctan2(dx_tr, dy_tr)) % 360
        mean_heading = float(np.nanmedian(headings)) if len(headings) > 0 else 0.0

        gcols  = {c.lower(): c for c in df.columns}
        lat_c  = next((gcols[c] for c in ['lat', 'latitude']  if c in gcols), None)
        lon_c  = next((gcols[c] for c in ['lon', 'longitude'] if c in gcols), None)
        time_c = gcols.get('time')
        
        if not (lat_c and lon_c and time_c):
            return

        obs_epochs = np.array([_ts(v) for v in df[time_c].values])
        cen_lats   = np.interp(obs_epochs, t_epochs, t_lats)
        cen_lons   = np.interp(obs_epochs, t_epochs, t_lons)
        
        dlat       = np.radians(df[lat_c].values.astype(float) - cen_lats)
        dlon       = np.radians(df[lon_c].values.astype(float) - cen_lons)
        mean_lat   = np.radians((df[lat_c].values.astype(float) + cen_lats) / 2.0)
        
        x_km       = EARTH_R_KM * dlon * np.cos(mean_lat)
        y_km       = EARTH_R_KM * dlat
        
        dist       = np.sqrt(x_km**2 + y_km**2)
        az_north   = np.degrees(np.arctan2(x_km, y_km)) % 360
        az_motion  = (az_north - mean_heading) % 360

        nan_mask   = (~np.isfinite(obs_epochs) | df[lat_c].isna().values | df[lon_c].isna().values)
        
        dist[nan_mask]      = np.nan
        az_north[nan_mask]  = np.nan
        az_motion[nan_mask] = np.nan

        df['dist_from_center'] = dist
        df['azimuth_north']    = az_north
        df['azimuth_motion']   = az_motion
        
        if group_name not in self.var_attrs:
            self.var_attrs[group_name] = {}
            
        self.var_attrs[group_name]['dist_from_center'] = {'units': 'km', 'long_name': 'Distance from Storm Center (Computed)'}
        self.var_attrs[group_name]['azimuth_north']    = {'units': 'deg', 'long_name': 'Azimuth from North (Computed)'}
        self.var_attrs[group_name]['azimuth_motion']   = {'units': 'deg', 'long_name': 'Azimuth from Storm Motion (Computed)'}

    def sort_variables(self, var_list, group_name):
        """
        Unified sorting method for all UI dropdowns.
        Ensures standard variables come first, standard coordinates (Lat/Lon) second, 
        and derived coordinates (Distance, Azimuths) absolute last.
        """
        def _sort_key(c):
            c_lower = c.lower()
            cfg = GLOBAL_VAR_CONFIG.get(c_lower, {})
            is_derived = cfg.get('is_derived', False)
            is_coord   = cfg.get('is_coord', False)
            weight     = cfg.get('sort_weight', 50)
            
            if is_derived and is_coord:
                tier = 3
            elif is_coord:
                tier = 2
            elif is_derived:
                tier = 1
            else:
                tier = 0
                
            disp = self._get_var_display_name(group_name, c)
            return f"{tier}_{weight:03d}_{disp}"
            
        # Use dict.fromkeys to strip duplicates before sorting
        unique_vars = list(dict.fromkeys(var_list))
        return sorted(unique_vars, key=_sort_key)

    def get_plottable_variables(self, sel_group, active_z_col=None, exclude_vectors=False):
        if sel_group not in self.data:
            return []
        self._ensure_derived_spatial_coords(sel_group)

        df         = self.data[sel_group]
        valid_cols = []

        for col in df.columns:
            if active_z_col and col == active_z_col:
                continue
            col_lower = col.lower()
            cfg = GLOBAL_VAR_CONFIG.get(col_lower, {})
            if cfg.get('hide', False):
                continue
            if exclude_vectors and cfg.get('is_vector', False):
                continue
            if col_lower.endswith('err'):
                continue
            if df[col].dtype == 'object':
                continue
            valid_cols.append(col)

        return self.sort_variables(valid_cols, sel_group)

    def get_coordinate_variables(self, group_name):
        if group_name not in self.data:
            return []
        self._ensure_derived_spatial_coords(group_name)
        df           = self.data[group_name]
        valid_coords = []

        for col in df.columns:
            c_lower = col.lower()
            if GLOBAL_VAR_CONFIG.get(c_lower, {}).get('is_coord', False):
                valid_coords.append(col)

        if not valid_coords:
            valid_coords = [c for c in df.columns if df[c].dtype != 'object']

        return self.sort_variables(valid_coords, group_name)

    def _get_var_display_name(self, group_name, variable):
        if variable.lower() == 'time':
            return "Time (relative to cycle center)"
        meta      = self.var_attrs.get(group_name, {}).get(variable, {})
        long_name = decode_metadata(meta.get('long_name', ''))

        if not long_name:
            if variable.lower().endswith('err'):
                base_var  = variable[:-3] if not variable.lower().endswith('_err') else variable[:-4]
                long_name = base_var.replace('_', ' ').title() + " Error"
            else:
                long_name = variable.replace('_', ' ').title()
        else:
            long_name = long_name.title()

        units = decode_metadata(meta.get('units', ''))
        if units:
            return f"{long_name} ({units})"
        return long_name

    def _format_storm_subtitle(self):
        info     = self.metadata.get('info', {})
        storm_id = info.get('storm_id', '').strip()
        dt_raw   = info.get('storm_datetime', '').strip()

        if not storm_id:
            return ''

        dt_str = ''
        if dt_raw:
            try:
                from datetime import datetime
                dt     = datetime.strptime(dt_raw.rstrip('Z'), '%Y-%m-%dT%H:%M:%S')
                dt_str = dt.strftime('%d-%b-%Y %H:%M UTC')
            except ValueError:
                dt_str = dt_raw

        if dt_str:
            return f"{storm_id} ({dt_str})"
        return storm_id

    def _format_title(self, group_name, variable, constraint_lbl):
        parts = group_name.split('_')

        if parts[0].lower() == 'track':
            inst     = ' '.join(p.capitalize() for p in parts[1:])
            platform = ''
        else:
            inst_lower = next(
                (p.lower() for p in parts
                 if p.lower() in ['dropsonde', 'tdr', 'sfmr', 'flight']),
                parts[0].lower()
            )
            if inst_lower in ['sfmr', 'tdr']:
                inst = inst_lower.upper()
            elif inst_lower == 'flight':
                inst = "Flight-Level"
            else:
                inst = inst_lower.capitalize()
            platform = next(
                (p.upper() for p in parts
                 if 'noaa' in p.lower() or 'af' in p.lower() or 'usaf' in p.lower()),
                ''
            )
            if not platform and len(parts) > 1:
                platform = parts[-1].upper()

        var_display = self._get_var_display_name(group_name, variable)
        line1 = f"{inst} {var_display}"
        if platform:
            line1 += f" from {platform}"

        lines = [f"<span style='font-size:{FS_PLOT_TITLE}px'>{line1}</span>"]
        if constraint_lbl:
            lines.append(f"<span style='font-size:{FS_PLOT_AXIS}px'>{constraint_lbl}</span>")

        storm_sub = self._format_storm_subtitle()
        if storm_sub:
            lines.append(f"<span style='font-size:{FS_PLOT_AXIS}px'>{storm_sub}</span>")

        # THE FIX: Prepend a <br> to explicitly push the text block down
        # away from the absolute top of the container where the modebar lives.
        return "<br>" + "<br>".join(lines)

    def _title_top_margin(self, title: str, gap: int = 45) -> int:
        # THE FIX: Bumped the default gap from 20 to 45.
        # This ensures the plot box itself drops down enough to make room 
        # for both the lowered title and the empty hover zone above it.
        n_lines = title.count('<br>') + 1
        height  = FS_PLOT_TITLE
        height += max(0, n_lines - 1) * FS_PLOT_AXIS
        return height + gap

    def _convert_time_to_relative(self, vals):
        from datetime import datetime, timezone
        info      = self.metadata.get('info', {})
        epoch_raw = info.get('storm_epoch', '')
        try:
            cycle_epoch = float(epoch_raw)
        except (ValueError, TypeError):
            dt_raw = info.get('storm_datetime', '').strip()
            try:
                dt          = datetime.strptime(dt_raw.rstrip('Z'), '%Y-%m-%dT%H:%M:%S')
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
        interval   = 1800
        tick_start = np.ceil(t_min / interval) * interval
        tick_end   = np.floor(t_max / interval) * interval
        tick_vals  = np.arange(tick_start, tick_end + 1, interval)

        def fmt_seconds(s):
            sign = '-' if s < 0 else '+'
            s    = abs(int(s))
            h, rem = divmod(s, 3600)
            m, sec = divmod(rem, 60)
            return f"{sign}{h:02d}:{m:02d}:{sec:02d}"

        tick_labels = [fmt_seconds(t) for t in tick_vals]
        return rel_vals, tick_vals, tick_labels

    def _apply_time_axis(self, var_col, vals, axis_dict, is_x=True):
        if var_col.lower() != 'time':
            return vals
        result = self._convert_time_to_relative(vals)
        if result is None:
            return vals
        rel_vals, tick_vals, tick_labels = result
        axis_dict['tickvals'] = tick_vals
        axis_dict['ticktext'] = tick_labels
        axis_dict['title']    = 'Time relative to cycle center (HH:MM:SS)'
        if is_x:
            axis_dict['tickangle'] = -45
        return rel_vals

    def _apply_filters(self, df, req_cols=None, z_con=None, time_bounds=None, 
                       thinning_pct=None, domain_bounds=None, filter_spatial=True):
        plot_df = df.copy()
        
        if req_cols:
            valid_cols = [c for c in req_cols if c and c in plot_df.columns]
            if valid_cols:
                plot_df = plot_df.dropna(subset=valid_cols)
        if plot_df.empty: return plot_df, ""

        constraint_lbl = ""

        if z_con and z_con.get('col') in plot_df.columns:
            t_col = z_con['col']
            val = z_con['val']
            tol = z_con['tol']
            zv = plot_df[t_col] / 100.0 if z_con.get('convert_pa_to_hpa') else plot_df[t_col]
            mask = (zv >= val - tol) & (zv <= val + tol)
            plot_df = plot_df[mask]
            unit_str = "hPa" if z_con.get('convert_pa_to_hpa') else ""
            constraint_lbl = f"Level: {val} ± {tol} {unit_str}"
        if plot_df.empty: return plot_df, constraint_lbl

        if time_bounds and time_bounds.get('col') in plot_df.columns:
            t_col = time_bounds['col']
            t_min, t_max = time_bounds['min'], time_bounds['max']
            plot_df = plot_df[(plot_df[t_col] >= t_min) & (plot_df[t_col] <= t_max)]
        if plot_df.empty: return plot_df, constraint_lbl

        if thinning_pct is not None and thinning_pct < 100:
            plot_df = plot_df.sample(frac=thinning_pct / 100.0, random_state=42)
        if plot_df.empty: return plot_df, constraint_lbl

        if domain_bounds:
            if 'z_min' in domain_bounds and domain_bounds.get('z_col') in plot_df.columns:
                z_b_col = domain_bounds['z_col']
                z_b_vals = plot_df[z_b_col] / 100.0 if domain_bounds.get('z_convert') else plot_df[z_b_col]
                plot_df = plot_df[(z_b_vals >= domain_bounds['z_min']) & (z_b_vals <= domain_bounds['z_max'])]
            if plot_df.empty: return plot_df, constraint_lbl

            if filter_spatial:
                cols_lower = {c.lower(): c for c in plot_df.columns}
                x_col = next((cols_lower[c] for c in ['lon', 'longitude', 'clon'] if c in cols_lower), None)
                y_col = next((cols_lower[c] for c in ['lat', 'latitude', 'clat'] if c in cols_lower), None)
                if x_col and y_col:
                    lats, lons = plot_df[y_col].values, plot_df[x_col].values
                    mask = ((lats >= domain_bounds.get('lat_min', -90)) & 
                            (lats <= domain_bounds.get('lat_max', 90)) &
                            (lons >= domain_bounds.get('lon_min', -180)) & 
                            (lons <= domain_bounds.get('lon_max', 180)))
                    plot_df = plot_df[mask]

        return plot_df, constraint_lbl
    