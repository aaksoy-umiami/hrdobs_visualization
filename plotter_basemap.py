# -*- coding: utf-8 -*-
"""
Purpose:
    Provides black-line basemap helpers for drawing geographic coastlines and country borders underneath Plotly data traces.

Functions/Classes:
    - _decode_arc: Decodes a delta-encoded topojson arc to longitude and latitude lists.
    - _find_topo_path: Locates the Natural Earth topojson file, prioritizing the project-bundled copy.
    - get_basemap_traces: Returns a list of Scatter line traces for geographic coastlines and borders.
    - get_geo_layout: Legacy function returning a geographic layout dictionary for older Plotly versions.
"""

import math
import os
import json
from ui_layout import TARGET_PLOT_TICKS


def _decode_arc(arc, scale, translate):
    """
    Decodes a delta-encoded topojson arc to longitude and latitude lists.
    """
    lons, lats = [], []
    x, y = 0, 0
    for pt in arc:
        x += pt[0]
        y += pt[1]
        lons.append(x * scale[0] + translate[0])
        lats.append(y * scale[1] + translate[1])
    return lons, lats


def _find_topo_path():
    """
    Locates the Natural Earth topojson file, prioritizing the project-bundled copy.
    """
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for fname in ('world_50m.json', 'world_110m.json'):
        project_copy = os.path.join(script_dir, fname)
        if os.path.exists(project_copy):
            return project_copy

    try:
        import plotly
        base = os.path.dirname(plotly.__file__)
        candidates = [
            os.path.join(base, 'package_data', 'topojson', 'world_50m.json'),
            os.path.join(base, 'package_data', 'topojson', 'world_110m.json'),
            os.path.join(base, 'data', 'world_110m.json'),
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
    except Exception:
        pass
    return None


def get_basemap_traces(domain_bounds: dict) -> list:
    """
    Returns a list of Scatter line traces for geographic coastlines and borders.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        return []

    topo_path = _find_topo_path()
    if topo_path is None:
        return []

    try:
        with open(topo_path) as f:
            topo = json.load(f)
    except Exception:
        return []

    arcs = topo.get('arcs', [])
    transform = topo.get('transform', {})
    scale = transform.get('scale', [1.0, 1.0])
    translate = transform.get('translate', [0.0, 0.0])

    pad = 1.0
    lo_min = domain_bounds['lon_min'] - pad
    lo_max = domain_bounds['lon_max'] + pad
    la_min = domain_bounds['lat_min'] - pad
    la_max = domain_bounds['lat_max'] + pad

    all_lons = []
    all_lats = []

    for arc in arcs:
        lons, lats = _decode_arc(arc, scale, translate)

        in_domain = any(
            lo_min <= lo <= lo_max and la_min <= la <= la_max
            for lo, la in zip(lons, lats)
        )
        if not in_domain:
            continue

        all_lons.extend(lons + [None])
        all_lats.extend(lats + [None])

    if not all_lons:
        return []

    return [go.Scatter(
        x=all_lons,
        y=all_lats,
        mode='lines',
        line=dict(color='black', width=0.8),
        hoverinfo='skip',
        showlegend=False,
        name='_basemap',
    )]


def get_geo_layout(domain_bounds: dict) -> dict:
    """
    Legacy function returning a geographic layout dictionary for older Plotly versions.
    """
    lat_pad = max((domain_bounds['lat_max'] - domain_bounds['lat_min']) * 0.02, 0.1)
    lon_pad = max((domain_bounds['lon_max'] - domain_bounds['lon_min']) * 0.02, 0.1)
    max_span = max(domain_bounds['lat_max'] - domain_bounds['lat_min'],
                   domain_bounds['lon_max'] - domain_bounds['lon_min'])
    raw_dtick = max_span / max(1, TARGET_PLOT_TICKS)
    if raw_dtick <= 0:
        dynamic_dtick = 1.0
    else:
        magnitude = 10 ** math.floor(math.log10(raw_dtick))
        norm = raw_dtick / magnitude
        if norm < 1.5:   nice_norm = 1.0
        elif norm < 3.5: nice_norm = 2.0
        elif norm < 7.5: nice_norm = 5.0
        else:            nice_norm = 10.0
        dynamic_dtick = nice_norm * magnitude

    return dict(
        resolution=50,
        showcoastlines=True, coastlinecolor="black", coastlinewidth=1.0,
        showland=False, showocean=False,
        showlakes=True, lakecolor="rgba(0,0,0,0)",
        showcountries=True, countrycolor="black", countrywidth=0.5,
        showsubunits=True, subunitcolor="black", subunitwidth=0.35,
        bgcolor="rgba(0,0,0,0)",
        lonaxis=dict(range=[domain_bounds['lon_min'] - lon_pad,
                            domain_bounds['lon_max'] + lon_pad],
                     showgrid=True, gridcolor="rgba(180,180,180,0.4)",
                     dtick=dynamic_dtick),
        lataxis=dict(range=[domain_bounds['lat_min'] - lat_pad,
                            domain_bounds['lat_max'] + lat_pad],
                     showgrid=True, gridcolor="rgba(180,180,180,0.4)",
                     dtick=dynamic_dtick),
        projection_type="mercator",
        domain=dict(x=[0.0, 1.0], y=[0.0, 1.0]),
    )