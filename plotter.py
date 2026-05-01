# -*- coding: utf-8 -*-
"""
Purpose:
    Serves as the main assembler for the StormPlotter, aggregating various plotting mixins into a unified class architecture.

Functions/Classes:
    - StormPlotter: Unified class inheriting capabilities from all modular plotting mixins and base state management.
"""

from config import EARTH_R_KM, SURFACE_PRESSURE_HPA
from plotter_base import (
    StormPlotterBase,
    _CONE_DOMAIN_FRACTION,
    _FIG_HEIGHT_BASE,
    _FIG_HEIGHT_Z_THRESHOLD,
    _FIG_HEIGHT_Z_STRETCH,
)

from plotter_cartesian import CartesianMixin, add_flight_tracks
from plotter_storm_relative import StormRelativeMixin
from plotter_radial_height import RadialHeightMixin
from plotter_histogram import HistogramMixin
from plotter_scatter import ScatterMixin

class StormPlotter(
    CartesianMixin,
    StormRelativeMixin,
    RadialHeightMixin,
    HistogramMixin,
    ScatterMixin,
    StormPlotterBase
):
    """
    Unified StormPlotter inheriting all plotting capabilities from the modular mixin classes 
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