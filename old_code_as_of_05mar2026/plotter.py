# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from config import GLOBAL_VAR_CONFIG
from data_utils import decode_metadata

class StormPlotter:
    def __init__(self, data_dict, track_data, metadata, var_attrs):
        self.data = data_dict
        self.track = track_data
        self.metadata = metadata
        self.var_attrs = var_attrs  

    def get_plottable_variables(self, sel_group, active_z_col=None):
        if sel_group not in self.data: return []
        
        df = self.data[sel_group]
        valid_cols = []
        
        for col in df.columns:
            if active_z_col and col == active_z_col: continue
            col_lower = col.lower()
            if GLOBAL_VAR_CONFIG.get(col_lower, {}).get('hide', False): continue
            if col_lower.endswith('err'): continue
            if df[col].dtype == 'object': continue
            valid_cols.append(col)
            
        # Custom sort key to force 2D derived to appear before 3D derived
        def custom_sort(c):
            c_lower = c.lower()
            if c_lower == 'wspd_hz_comp':
                return 'wspd_comp_1'
            if c_lower == 'wspd_3d_comp':
                return 'wspd_comp_2'
            if c_lower == 'wind_vec_hz':
                return 'wspd_comp_3'
            if c_lower == 'wind_vec_3d':
                return 'wspd_comp_4'
            return c_lower
            
        return sorted(valid_cols, key=custom_sort)

    def _get_var_display_name(self, group_name, variable):
        meta = self.var_attrs.get(group_name, {}).get(variable, {})
        long_name = decode_metadata(meta.get('long_name', ''))

        if not long_name:
            # If it's an error field missing a long_name, intelligently format it
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

    def _format_title(self, group_name, variable, constraint_lbl):
        parts = group_name.split('_')
        
        # 1. Isolate the instrument name in lowercase
        inst_lower = next((p.lower() for p in parts if p.lower() in ['dropsonde', 'tdr', 'sfmr', 'flight']), parts[0].lower())
        
        # 2. Intelligently format acronyms vs words
        if inst_lower in ['sfmr', 'tdr']:
            inst = inst_lower.upper()
        elif inst_lower == 'flight':
            inst = "Flight-Level"
        else:
            inst = inst_lower.capitalize()
            
        # 3. Extract and format the platform
        platform = next((p.upper() for p in parts if 'noaa' in p.lower() or 'af' in p.lower() or 'usaf' in p.lower()), '')
        if not platform and len(parts) > 1: platform = parts[-1].upper()

        var_display = self._get_var_display_name(group_name, variable)

        # 4. Assemble the final string
        title = f"{inst} {var_display}"
        if platform: title += f" from {platform}"
        
        if constraint_lbl: # Only add the HTML break if a constraint actually exists
            title += f"<br><sup>{constraint_lbl}</sup>"
            
        return title

    def plot(self, group_name, variable, z_con, domain_bounds, show_center, 
             is_3d=False, z_col=None, thinning_pct=None, marker_size_pct=100,
             time_bounds=None, z_ratio=0.3, vec_scale=1.0):
        
        if group_name not in self.data: return None, None
            
        df = self.data[group_name].copy()
        is_track = 'TRACK' in group_name.upper()
        
        cols_lower = {c.lower(): c for c in df.columns}
        x_col = next((cols_lower[c] for c in ['lon', 'longitude'] if c in cols_lower), None)
        y_col = next((cols_lower[c] for c in ['lat', 'latitude'] if c in cols_lower), None)
        
        if not x_col or not y_col: return None, None
            
        cols_to_check = [x_col, y_col]
        if not is_track and variable in df.columns: cols_to_check.append(variable)
        if z_col and z_col in df.columns: cols_to_check.append(z_col)
            
        df = df.dropna(subset=cols_to_check)
        if df.empty: return None, None
        
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
        
        if time_bounds and time_bounds['col'] in plot_df.columns:
            t_col = time_bounds['col']
            t_min, t_max = time_bounds['min'], time_bounds['max']
            plot_df = plot_df[(plot_df[t_col] >= t_min) & (plot_df[t_col] <= t_max)]
            lats, lons = plot_df[y_col].values, plot_df[x_col].values
            
            if plot_df.empty:
                st.warning("No data found within the selected time window.")
                return None, None

        fig = go.Figure()

        z_vals = None
        if is_3d and z_col and z_col in plot_df.columns:
            z_vals = plot_df[z_col].values.copy()
            # ---> FIX: Convert Z-axis Pascals to hPa so they fit inside the axis limits!
            z_unit = decode_metadata(self.var_attrs.get(group_name, {}).get(z_col, {}).get('units', ''))
            if 'Pa' in z_unit and 'hPa' not in z_unit:
                z_vals = z_vals / 100.0

        var_conf = GLOBAL_VAR_CONFIG.get(variable.lower(), {})
        cmap = var_conf.get('colorscale', 'Jet') 
        
        if is_track:
            cmin, cmax = 0, 1
        else:
            cmin_conf = var_conf.get('cmin')
            cmax_conf = var_conf.get('cmax')
            cmin = float(cmin_conf) if cmin_conf is not None else float(plot_df[variable].min(skipna=True))
            cmax = float(cmax_conf) if cmax_conf is not None else float(plot_df[variable].max(skipna=True))

        cmid = var_conf.get('cmid', None)
        sz_mult = marker_size_pct / 100.0

        display_name = self._get_var_display_name(group_name, variable)
        cols_lower = {c.lower(): c for c in plot_df.columns}
        is_vector = variable.lower() in ['wind_vec_hz', 'wind_vec_3d']

        if is_track:
            fig.add_trace(go.Scatter(x=lons, y=lats, mode='lines', line=dict(width=4, color='blue'), name=group_name, showlegend=False))
        
        elif is_vector:
            u_col, v_col = cols_lower.get('u'), cols_lower.get('v')
            
            # ---> FIX: Extract raw numpy arrays to prevent Plotly indexing crashes! <---
            u_vals = plot_df[u_col].values
            v_vals = plot_df[v_col].values
            magnitude_vals = plot_df[variable].values
            
            if is_3d and z_vals is not None:
                w_col = cols_lower.get('w')
                w_vals = plot_df[w_col].values if variable.lower() == 'wind_vec_3d' and w_col else np.zeros_like(u_vals)
                
                # --- FIX FOR 3D CONE SIZING ---
                # Bypass Plotly's distance-based scaling by forcing raw coordinates
                max_span = max(np.nanmax(lons) - np.nanmin(lons), np.nanmax(lats) - np.nanmin(lats))
                if pd.isna(max_span) or max_span == 0: max_span = 1.0
                
                # Target max arrow length: exactly ~3% of the domain span
                target_length = max_span * 0.03 * vec_scale
                max_mag = np.nanmax(magnitude_vals)
                
                # 'raw' sizemode mathematically forces the cone length to: norm * sizeref
                cone_sizeref = (target_length / max_mag) if max_mag > 0 else 1.0
                
                fig.add_trace(go.Cone(
                    x=lons, y=lats, z=z_vals,
                    u=u_vals, v=v_vals, w=w_vals,
                    colorscale=cmap, cmin=cmin, cmax=cmax,
                    sizemode="raw",       # <-- CRITICAL: Disables Plotly's unpredictable auto-scaling
                    sizeref=cone_sizeref, # <-- Locks the exact size to our math above
                    anchor="tail",
                    name=display_name,
                    showscale=True,
                    colorbar=dict(title=display_name.split('(')[-1].replace(')', '') if '(' in display_name else "", len=0.8, thickness=20)
                ))
            else:
                # 2D Rotated Arrows
                angles = np.degrees(np.arctan2(u_vals, v_vals))
                
                fig.add_trace(go.Scatter(
                    x=lons, y=lats, mode='markers',
                    marker=dict(
                        symbol='arrow-up',
                        angle=angles,
                        angleref='up',
                        size=12 * sz_mult * vec_scale, # Applied vec_scale linearly!
                        color=magnitude_vals,
                        colorscale=cmap, cmin=cmin, cmax=cmax, cmid=cmid,
                        showscale=True,
                        colorbar=dict(title=display_name.split('(')[-1].replace(')', '') if '(' in display_name else "", len=0.8, thickness=20, tickfont=dict(size=14))
                    ),
                    name=display_name,
                    text=[f"Magnitude: {m:.1f}" if not pd.isna(m) else "NaN" for m in magnitude_vals],
                    hoverinfo='text+x+y',
                    showlegend=False
                ))

        elif is_3d and z_vals is not None:
            fig.add_trace(go.Scatter3d(
                x=lons, y=lats, z=z_vals, mode='markers',
                marker=dict(
                    size=4 * sz_mult, color=plot_df[variable], colorscale=cmap,
                    colorbar=dict(len=0.8, thickness=20),
                    cmin=cmin, cmax=cmax, cmid=cmid, opacity=0.8
                ),
                text=[f"{v:,.2f}" if not pd.isna(v) else "NaN" for v in plot_df[variable]],
                name=group_name, showlegend=False
            ))
            if show_center and self.metadata.get('storm_center'):
                clat, clon = self.metadata['storm_center']
                is_pres = z_col and any(p in z_col.lower() for p in ['pres', 'pressure', 'p'])
                z_bottom = np.nanmax(z_vals) if is_pres else np.nanmin(z_vals)
                fig.add_trace(go.Scatter3d(
                    x=[clon], y=[clat], z=[z_bottom], mode='markers', 
                    marker=dict(symbol='x', size=4, color='black'), name='Center', showlegend=False
                ))

        else:
            fig.add_trace(go.Scatter(
                x=lons, y=lats, mode='markers',
                marker=dict(
                    size=9 * sz_mult, color=plot_df[variable], colorscale=cmap,
                    colorbar=dict(len=0.8, thickness=20, tickfont=dict(size=14)),
                    cmin=cmin, cmax=cmax, cmid=cmid
                ),
                text=[f"{v:,.2f}" if not pd.isna(v) else "NaN" for v in plot_df[variable]],
                name=group_name, showlegend=False
            ))
            if show_center and self.metadata.get('storm_center'):
                clat, clon = self.metadata['storm_center']
                fig.add_trace(go.Scatter(x=[clon], y=[clat], mode='markers', marker=dict(symbol='x-thin', size=14, line=dict(color='black', width=2.5)), name='Center', showlegend=False))

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
            
            # Reverses the Z-axis if the vertical coordinate is Pressure
            if z_col and any(p in z_col.lower() for p in ['pres', 'pressure', 'p']):
                scene_dict['zaxis']['autorange'] = 'reversed'

            # 1. Dynamically pull the camera back as the aspect ratio gets taller
            scene_dict['camera'] = dict(
                eye=dict(x=1.5, y=-1.5, z=1.0 + (z_ratio * 0.8))
            )

            # 2. Dynamically stretch the figure height if the plot is extremely tall
            dynamic_height = 800 if z_ratio <= 0.6 else int(800 + (z_ratio - 0.6) * 400)

            fig.update_layout(
                title={'text': nice_title, 'y':0.95, 'x':0.5, 'xanchor': 'center'},
                title_font=dict(size=24),
                width=800, height=dynamic_height,
                showlegend=False,
                scene=scene_dict,
                # 3. Added 40px of bottom margin (b=40) to protect the lower axis ticks
                margin=dict(l=0, r=0, b=40, t=80) 
            )
        else:
            fig.add_trace(go.Scatter(x=[None], y=[None], xaxis='x2', yaxis='y2', showlegend=False))
            fig.update_layout(
                title={'text': nice_title, 'y':0.95, 'x':0.5, 'xanchor': 'center'},
                title_font=dict(size=24),
                width=800, height=800,
                showlegend=False,
                xaxis=dict(
                    title="Longitude", title_font=dict(size=18),
                    range=x_range, mirror='ticks', showline=True, linecolor='black',
                    showgrid=True, gridcolor='lightgray', tickfont=dict(size=14)
                ),
                yaxis=dict(
                    title="Latitude", title_font=dict(size=18),
                    range=y_range, mirror='ticks', showline=True, linecolor='black', 
                    scaleanchor="x", scaleratio=1,
                    showgrid=True, gridcolor='lightgray', tickfont=dict(size=14)
                ),
                xaxis2=dict(overlaying='x', side='top', matches='x', showline=False, showgrid=False),
                yaxis2=dict(overlaying='y', side='right', matches='y', showline=False, showgrid=False),
                plot_bgcolor="rgb(250, 250, 250)",
                margin=dict(l=60, r=40, t=80, b=60)
            )
            
        return fig, plot_df

def add_flight_tracks(fig, data_pack, track_mapping, plot_track, selected_platform, is_3d, is_target_pres, proj_option="Bottom Only", domain_bounds=None):
    """Dynamically applies 2D or 3D flight tracks and wall projections to an existing figure."""
    for plat, track_group in track_mapping.items():
        track_df = data_pack['data'][track_group]
        
        t_lat_c = next((c for c in track_df.columns if c.lower() in ['lat', 'latitude']), None)
        t_lon_c = next((c for c in track_df.columns if c.lower() in ['lon', 'longitude']), None)
        is_visible = True if (plot_track and selected_platform == plat) else False
        
        if t_lat_c and t_lon_c:
            if not is_3d:
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
                    if is_target_pres:
                        t_z_unit = data_pack['var_attrs'].get(track_group, {}).get(t_z_c, {}).get('units', '')
                        t_z_unit = decode_metadata(t_z_unit)
                        if 'Pa' in t_z_unit and 'hPa' not in t_z_unit: t_z_vals = t_z_vals / 100.0

                    # 1. The Actual 3D Flight Track
                    fig.add_trace(go.Scatter3d(
                        x=track_df[t_lon_c], y=track_df[t_lat_c], z=t_z_vals,
                        mode='lines', line=dict(color='black', width=2), 
                        name=f'{plat} Flight Track', showlegend=False, visible=is_visible
                    ))
                    
                    show_bottom = proj_option in ["Bottom Only", "Bottom + Sides"]
                    show_sides = proj_option in ["Sides Only", "Bottom + Sides"]
                    
                    # 2. The Bottom Shadow
                    if show_bottom:
                        if domain_bounds and 'z_min' in domain_bounds:
                            floor_z = domain_bounds['z_max'] if is_target_pres else domain_bounds['z_min']
                        else:
                            floor_z = max(1013.25, np.nanmax(t_z_vals)) if is_target_pres else min(0.0, np.nanmin(t_z_vals))
                            
                        z_shadow = np.full_like(t_z_vals, floor_z)
                        
                        fig.add_trace(go.Scatter3d(
                            x=track_df[t_lon_c], y=track_df[t_lat_c], z=z_shadow,
                            mode='lines', line=dict(color='lightgray', width=2), 
                            name=f'{plat} Surface Reflection', showlegend=False, visible=is_visible
                        ))
                    
                    # 3. The Side Wall Shadows
                    if show_sides:
                        lon_wall = domain_bounds['lon_min'] if domain_bounds else track_df[t_lon_c].min()
                        lat_wall = domain_bounds['lat_min'] if domain_bounds else track_df[t_lat_c].min()
                        
                        # Left Wall (YZ Plane)
                        lon_shadow = np.full_like(track_df[t_lon_c], lon_wall)
                        fig.add_trace(go.Scatter3d(
                            x=lon_shadow, y=track_df[t_lat_c], z=t_z_vals,
                            mode='lines', line=dict(color='lightgray', width=2), 
                            name=f'{plat} Lon Wall Reflection', showlegend=False, visible=is_visible
                        ))
                        
                        # Back Wall (XZ Plane)
                        lat_shadow = np.full_like(track_df[t_lat_c], lat_wall)
                        fig.add_trace(go.Scatter3d(
                            x=track_df[t_lon_c], y=lat_shadow, z=t_z_vals,
                            mode='lines', line=dict(color='lightgray', width=2), 
                            name=f'{plat} Lat Wall Reflection', showlegend=False, visible=is_visible
                        ))
    return fig
