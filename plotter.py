# -*- coding: utf-8 -*-
"""
plotter.py
----------
Main Assembler for the StormPlotter.

Uses a Mixin architecture to keep files small and focused.
"""

from config import EARTH_R_KM, SURFACE_PRESSURE_HPA
from plotter_base import (
    StormPlotterBase,
    _CONE_DOMAIN_FRACTION,
    _FIG_HEIGHT_BASE,
    _FIG_HEIGHT_Z_THRESHOLD,
    _FIG_HEIGHT_Z_STRETCH,
)

# Import the specialized Plotting Mixins
from plotter_cartesian import CartesianMixin, add_flight_tracks
from plotter_storm_relative import StormRelativeMixin
from plotter_histogram import HistogramMixin
from plotter_scatter import ScatterMixin

class StormPlotter(
    CartesianMixin,
    StormRelativeMixin,
    HistogramMixin,
    ScatterMixin,
    StormPlotterBase
):
    """
    Unified StormPlotter.
    Inherits all plotting capabilities from the modular mixin classes, 
    and core data/state management from StormPlotterBase.
    """
    pass

__all__ = [
    "StormPlotter",
    "add_flight_tracks",
    "_CONE_DOMAIN_FRACTION",
    "SURFACE_PRESSURE_HPA",
    "_FIG_HEIGHT_BASE",
    "_FIG_HEIGHT_Z_THRESHOLD",
    "_FIG_HEIGHT_Z_STRETCH",
    "EARTH_R_KM",
]
