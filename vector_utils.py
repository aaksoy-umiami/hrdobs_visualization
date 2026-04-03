# -*- coding: utf-8 -*-
"""
vector_utils.py
---------------
Utility functions for calculating and rendering vectorized, color-binned 
stick arrows for 2D and 3D Plotly plots without breaking the rendering engine.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.colors

from ui_layout import FS_PLOT_TICK
from config import (
    VEC_COLOR_BINS, 
    VEC_WING_ANGLE_DEG, 
    VEC_WING_LEN_FRAC, 
    VEC_WING_SPREAD_FRAC
)


def build_2d_vector_traces(
    x0, y0, u, v,
    color_vals, cmap, cmin, cmax, cmid,
    cb_tickvals, cb_ticktext,
    hover_text, display_name,
    vec_scale=1.0, y_scale_factor=1.0, arrow_fraction=0.05
):
    """
    Builds a list of 2D go.Scatter line traces representing color-binned stick arrows.
    Applies dimensionally-corrected math so the arrows don't deform on distorted axes.
    """
    max_span_x = np.nanmax(x0) - np.nanmin(x0)
    if pd.isna(max_span_x) or max_span_x == 0: max_span_x = 1.0
    
    mag = np.sqrt(u**2 + v**2)
    max_mag = np.nanmax(mag)
    S = (max_span_x * arrow_fraction * vec_scale) / (max_mag if max_mag > 0 else 1.0)
    
    # 1. Visual vectors (un-distorted)
    vx = u * S
    vy = v * S
    
    # 2. Map coordinates with y-axis scaling applied
    dx = vx
    dy = vy * y_scale_factor
    x1 = x0 + dx
    y1 = y0 + dy
    
    # 3. Calculate visual wing vectors
    theta1 = np.radians(VEC_WING_ANGLE_DEG)
    theta2 = np.radians(-VEC_WING_ANGLE_DEG)
    wing_len = VEC_WING_LEN_FRAC
    
    vwx1 = vx * np.cos(theta1) - vy * np.sin(theta1)
    vwy1 = vx * np.sin(theta1) + vy * np.cos(theta1)
    vwx2 = vx * np.cos(theta2) - vy * np.sin(theta2)
    vwy2 = vx * np.sin(theta2) + vy * np.cos(theta2)
    
    # 4. Apply scale to the wings and attach to tip
    wx1 = x1 + wing_len * vwx1
    wy1 = y1 + wing_len * vwy1 * y_scale_factor
    wx2 = x1 + wing_len * vwx2
    wy2 = y1 + wing_len * vwy2 * y_scale_factor
    
    # 5. Color Binning
    N_BINS = VEC_COLOR_BINS
    c_array_clean = np.nan_to_num(color_vals, nan=cmin)
    norm_c = np.clip((c_array_clean - cmin) / (cmax - cmin if cmax > cmin else 1.0), 0, 1)
    bin_indices = np.clip((norm_c * (N_BINS - 1)).astype(int), 0, N_BINS - 1)
    
    try: 
        sampled_colors = plotly.colors.sample_colorscale(cmap, np.linspace(0, 1, N_BINS))
    except Exception: 
        sampled_colors = plotly.colors.sample_colorscale('Turbo', np.linspace(0, 1, N_BINS))
        
    text_arr_np = np.array(hover_text)
    traces = []
        
    # 6. Generate a separate trace for each color bin
    for b in range(N_BINS):
        mask = (bin_indices == b)
        if not mask.any(): continue
        
        m_x0, m_x1, m_wx1, m_wx2 = x0[mask], x1[mask], wx1[mask], wx2[mask]
        m_y0, m_y1, m_wy1, m_wy2 = y0[mask], y1[mask], wy1[mask], wy2[mask]
        m_text = text_arr_np[mask]
        
        nan_arr = np.full_like(m_x0, np.nan)
        
        # 7-point stroke: Base -> Tip -> Break -> Wing1 -> Tip -> Wing2 -> Break
        b_x = np.column_stack([m_x0, m_x1, nan_arr, m_wx1, m_x1, m_wx2, nan_arr]).ravel()
        b_y = np.column_stack([m_y0, m_y1, nan_arr, m_wy1, m_y1, m_wy2, nan_arr]).ravel()
        b_t = np.repeat(m_text, 7)
        
        traces.append(go.Scatter(
            x=b_x, y=b_y, mode='lines',
            line=dict(color=sampled_colors[b], width=2),
            name=display_name, text=b_t, hoverinfo='text', showlegend=False
        ))

    # 7. Add single invisible trace to spawn the perfect colorbar
    dummy_x = [x0[0]] if len(x0) > 0 else [0]
    dummy_y = [y0[0]] if len(y0) > 0 else [0]
    traces.append(go.Scatter(
        x=dummy_x, y=dummy_y, mode='markers',
        marker=dict(
            size=0, opacity=0, color=[cmin, cmax], colorscale=cmap,
            cmin=cmin, cmax=cmax, cmid=cmid, showscale=True,
            colorbar=dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK),
                          tickvals=cb_tickvals, ticktext=cb_ticktext)
        ),
        showlegend=False, hoverinfo='skip'
    ))
    return traces


def build_3d_vector_traces(
    x0, y0, z0, u, v, w,
    color_vals, cmap, cmin, cmax, cmid,
    cb_tickvals, cb_ticktext,
    hover_text, display_name,
    vec_scale=1.0, z_scale_factor=1.0, arrow_fraction=0.05
):
    """
    Builds a list of 3D go.Scatter3d line traces representing color-binned stick arrows.
    Applies dimensionally-corrected math so the arrows don't deform on distorted Z axes.
    """
    max_span_x = np.nanmax(x0) - np.nanmin(x0)
    if pd.isna(max_span_x) or max_span_x == 0: max_span_x = 1.0
    
    mag = np.sqrt(u**2 + v**2 + w**2)
    max_mag = np.nanmax(mag)
    S = (max_span_x * arrow_fraction * vec_scale) / (max_mag if max_mag > 0 else 1.0)
    
    # 1. Visual vectors (un-distorted)
    vx, vy, vz = u * S, v * S, w * S
    
    # 2. Map coordinates with z-axis scaling applied
    dx, dy = vx, vy
    dz = vz * z_scale_factor
    x1, y1, z1 = x0 + dx, y0 + dy, z0 + dz
    
    # 3. Calculate visual wing vectors
    h_mag = np.sqrt(vx**2 + vy**2)
    h_mag[h_mag == 0] = 1e-5
    v_mag = np.sqrt(vx**2 + vy**2 + vz**2)
    
    wing_len = VEC_WING_LEN_FRAC
    wing_spread = VEC_WING_SPREAD_FRAC
    
    bx, by, bz = -vx * wing_len, -vy * wing_len, -vz * wing_len
    px = -vy / h_mag * (wing_spread * v_mag)
    py = vx / h_mag * (wing_spread * v_mag)
    pz = np.zeros_like(vz)
    
    vwx1, vwy1, vwz1 = bx + px, by + py, bz + pz
    vwx2, vwy2, vwz2 = bx - px, by - py, bz - pz
    
    # 4. Apply Z-scale to the wings and attach to the tip
    wx1, wy1, wz1 = x1 + vwx1, y1 + vwy1, z1 + vwz1 * z_scale_factor
    wx2, wy2, wz2 = x1 + vwx2, y1 + vwy2, z1 + vwz2 * z_scale_factor
    
    # 5. Color Binning
    N_BINS = VEC_COLOR_BINS
    c_array_clean = np.nan_to_num(color_vals, nan=cmin)
    norm_c = np.clip((c_array_clean - cmin) / (cmax - cmin if cmax > cmin else 1.0), 0, 1)
    bin_indices = np.clip((norm_c * (N_BINS - 1)).astype(int), 0, N_BINS - 1)
    
    try: 
        sampled_colors = plotly.colors.sample_colorscale(cmap, np.linspace(0, 1, N_BINS))
    except Exception: 
        sampled_colors = plotly.colors.sample_colorscale('Turbo', np.linspace(0, 1, N_BINS))
        
    text_arr_np = np.array(hover_text)
    traces = []
        
    # 6. Generate a separate trace for each color bin
    for b in range(N_BINS):
        mask = (bin_indices == b)
        if not mask.any(): continue
        
        m_x0, m_x1, m_wx1, m_wx2 = x0[mask], x1[mask], wx1[mask], wx2[mask]
        m_y0, m_y1, m_wy1, m_wy2 = y0[mask], y1[mask], wy1[mask], wy2[mask]
        m_z0, m_z1, m_wz1, m_wz2 = z0[mask], z1[mask], wz1[mask], wz2[mask]
        m_text = text_arr_np[mask]
        
        nan_arr = np.full_like(m_x0, np.nan)
        
        # 7-point stroke: Base -> Tip -> Break -> Wing1 -> Tip -> Wing2 -> Break
        b_x = np.column_stack([m_x0, m_x1, nan_arr, m_wx1, m_x1, m_wx2, nan_arr]).ravel()
        b_y = np.column_stack([m_y0, m_y1, nan_arr, m_wy1, m_y1, m_wy2, nan_arr]).ravel()
        b_z = np.column_stack([m_z0, m_z1, nan_arr, m_wz1, m_z1, m_wz2, nan_arr]).ravel()
        b_t = np.repeat(m_text, 7)
        
        traces.append(go.Scatter3d(
            x=b_x, y=b_y, z=b_z, mode='lines',
            line=dict(color=sampled_colors[b], width=3),
            name=display_name, text=b_t, hoverinfo='text', showlegend=False
        ))

    # 7. Add single invisible trace to spawn the perfect colorbar
    dummy_x = [x0[0]] if len(x0) > 0 else [0]
    dummy_y = [y0[0]] if len(y0) > 0 else [0]
    dummy_z = [z0[0]] if len(z0) > 0 else [0]
    traces.append(go.Scatter3d(
        x=dummy_x, y=dummy_y, z=dummy_z, mode='markers',
        marker=dict(
            size=0, opacity=0, color=[cmin, cmax], colorscale=cmap,
            cmin=cmin, cmax=cmax, cmid=cmid, showscale=True,
            colorbar=dict(len=0.8, thickness=15, tickfont=dict(size=FS_PLOT_TICK),
                          tickvals=cb_tickvals, ticktext=cb_ticktext)
        ),
        showlegend=False, hoverinfo='skip'
    ))
    return traces
