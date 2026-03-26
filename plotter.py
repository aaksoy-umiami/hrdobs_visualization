# -*- coding: utf-8 -*-
"""
plotter.py
----------
Backward-compatible re-export shim.

The plotting logic has been split into three focused modules:

  plotter_base.py    — StormPlotterBase  (constructor, helpers, introspection)
  plotter_spatial.py — StormPlotterSpatial  (Cartesian, storm-relative, radial-height plots)
  plotter_stats.py   — StormPlotterStats   (histogram, 2-D histogram, scatter plots)

All existing callers that import from plotter.py continue to work unchanged:

    from plotter import StormPlotter, add_flight_tracks

The module-level tunable constants are also re-exported so any code that
references them directly keeps working.
"""

from config import EARTH_R_KM, SURFACE_PRESSURE_HPA
from plotter_base import (
    _CONE_DOMAIN_FRACTION,
    _FIG_HEIGHT_BASE,
    _FIG_HEIGHT_Z_THRESHOLD,
    _FIG_HEIGHT_Z_STRETCH,
)
from plotter_stats import StormPlotterStats
from plotter_spatial import add_flight_tracks


class StormPlotter(StormPlotterStats):
    """
    Unified StormPlotter — assembles all plotting capabilities by inheriting
    from the stats → spatial → base chain:

        StormPlotter
          └─ StormPlotterStats   (histogram, 2-D histogram, scatter)
               └─ StormPlotterSpatial  (Cartesian, storm-relative, radial-height)
                    └─ StormPlotterBase  (constructor, helpers, introspection)

    Public API is identical to the original single-file StormPlotter.
    """


__all__ = [
    "StormPlotter",
    "add_flight_tracks",
    # constants
    "_CONE_DOMAIN_FRACTION",
    "SURFACE_PRESSURE_HPA",
    "_FIG_HEIGHT_BASE",
    "_FIG_HEIGHT_Z_THRESHOLD",
    "_FIG_HEIGHT_Z_STRETCH",
    "EARTH_R_KM",
]
