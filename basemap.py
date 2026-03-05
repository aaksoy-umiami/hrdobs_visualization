# -*- coding: utf-8 -*-
"""
basemap.py
----------
Black-line basemap helper for StormPlotter.

One public function:

    get_geo_layout(domain_bounds)
        Returns a Plotly layout.geo dict that draws coastlines, country
        borders, state/province borders, and lake outlines as thin black
        lines on a transparent background.  No fill colours.  No network
        calls — all data is Natural Earth 50m, bundled with Plotly.

Limitation
----------
Plotly does not support a geo underlay beneath a 3-D scene.  The basemap
is therefore silently skipped for 3-D plots — the checkbox has no visible
effect in that mode.  plotter.py handles this by only calling get_geo_layout
when is_3d is False.
"""
import math
from ui_layout import TARGET_PLOT_TICKS

def get_geo_layout(domain_bounds: dict) -> dict:
    """
    Return a Plotly layout.geo dict for a black-line basemap.

    Draws coastlines, country borders, state/province borders, and lake
    outlines as thin black lines.  Land, ocean, and lake interiors are
    transparent so the figure background colour shows through unchanged.

    Resolution is 50m (Natural Earth 1:50,000,000).  This is adequate for
    synoptic and mesoscale domains (roughly 3° and larger).  At inner-core
    scales (~1° or less) the lines will appear coarser than the data.

    Parameters
    ----------
    domain_bounds : dict
        Must contain keys: lat_min, lat_max, lon_min, lon_max (floats).
    """
    lat_pad = max((domain_bounds['lat_max'] - domain_bounds['lat_min']) * 0.02, 0.1)
    lon_pad = max((domain_bounds['lon_max'] - domain_bounds['lon_min']) * 0.02, 0.1)

    # 1. Find the maximum span of the current view
    max_span = max(domain_bounds['lat_max'] - domain_bounds['lat_min'],
                   domain_bounds['lon_max'] - domain_bounds['lon_min'])
    
    # 2. Divide by the user's global rule to find the raw tick interval
    raw_dtick = max_span / max(1, TARGET_PLOT_TICKS)
    
    # 3. "Nice Number" Algorithm: snap the raw interval to a clean human-readable number
    if raw_dtick <= 0:
        dynamic_dtick = 1.0
    else:
        magnitude = 10 ** math.floor(math.log10(raw_dtick))
        norm = raw_dtick / magnitude
        if norm < 1.5: 
            nice_norm = 1.0
        elif norm < 3.5: 
            nice_norm = 2.0
        elif norm < 7.5: 
            nice_norm = 5.0
        else: 
            nice_norm = 10.0
        dynamic_dtick = nice_norm * magnitude

    return dict(
        resolution=50,
        showcoastlines=True,
        coastlinecolor="black",
        coastlinewidth=1.0,
        showland=False,
        showocean=False,
        showlakes=True,
        lakecolor="rgba(0,0,0,0)",   
        showrivers=False,
        showcountries=True,
        countrycolor="black",
        countrywidth=0.5,
        showsubunits=True,           
        subunitcolor="black",
        subunitwidth=0.35,
        bgcolor="rgba(0,0,0,0)",     

        lonaxis=dict(
            range=[domain_bounds['lon_min'] - lon_pad,
                   domain_bounds['lon_max'] + lon_pad],
            showgrid=True,
            gridcolor="rgba(180,180,180,0.4)",
            dtick=dynamic_dtick, # Extracted from the global rule
        ),
        lataxis=dict(
            range=[domain_bounds['lat_min'] - lat_pad,
                   domain_bounds['lat_max'] + lat_pad],
            showgrid=True,
            gridcolor="rgba(180,180,180,0.4)",
            dtick=dynamic_dtick, # Extracted from the global rule
        ),
        projection_type="mercator",
    )
