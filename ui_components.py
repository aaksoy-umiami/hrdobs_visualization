# -*- coding: utf-8 -*-
"""
ui_components.py
----------------
Reusable Streamlit widget helpers.

Every function here encapsulates a recurring visual pattern so that call
sites stay concise and the visual behaviour is defined in exactly one place.
All style values are imported from ui_layout rather than hardcoded, so
changes to the design tokens automatically propagate here.

Public API
----------
section_divider()
    Thin horizontal rule used to separate sections within a sidebar container.

spacer(size)
    Vertical whitespace.  size='sm' (5 px) | 'md' (8 px) | 'lg' (28 px).

sidebar_label(text, enabled, size)
    Inline HTML label rendered above or beside a Streamlit widget when the
    native label would be hidden.  Supports enabled/disabled colour states.

multiselect_with_controls(label, options, key)
    st.multiselect with Select All / Deselect All buttons underneath.
"""

import streamlit as st
from ui_layout import CLR_MUTED, FS_LABEL, FS_BODY


# ---------------------------------------------------------------------------
# Section divider
# ---------------------------------------------------------------------------

def section_divider():
    """Thin rule used between sections inside a sidebar container."""
    st.markdown(
        "<hr style='margin: 8px 0; border: none; border-top: 1px solid #e0e0e0;'>",
        unsafe_allow_html=True
    )


# ---------------------------------------------------------------------------
# Spacer
# ---------------------------------------------------------------------------

_SPACER_SIZES = {
    'sm':  5,   # checkbox-align gap (before a checkbox row)
    'md':  8,   # light breathing room
    'lg':  28,  # button-align gap (before a button that needs to line up with a widget)
}

def spacer(size: str = 'sm'):
    """
    Vertical whitespace.

    Parameters
    ----------
    size : 'sm' | 'md' | 'lg'
        sm =  5 px  — used to align checkboxes with adjacent widgets
        md =  8 px  — general light breathing room
        lg = 28 px  — used to align buttons with adjacent select/radio widgets
    """
    px = _SPACER_SIZES.get(size, _SPACER_SIZES['sm'])
    st.markdown(
        f"<div style='height: {px}px;'></div>",
        unsafe_allow_html=True
    )


# ---------------------------------------------------------------------------
# Sidebar label
# ---------------------------------------------------------------------------

def sidebar_label(text: str, enabled: bool = True, size: str = 'body'):
    """
    Render an inline HTML label above or beside a Streamlit widget.

    Use this whenever st.slider / st.selectbox label_visibility="collapsed"
    is used and a custom label is needed in its place.

    Parameters
    ----------
    text    : Label text (plain string — no HTML).
    enabled : When False, renders in the muted colour to signal a disabled state.
    size    : 'body' (13 px, font-weight 500) | 'label' (16 px, normal weight)
    """
    color = "inherit" if enabled else CLR_MUTED

    if size == 'label':
        st.markdown(
            f"<div style='margin-top: 8px; font-size: {FS_LABEL}px; color: {color};'>"
            f"{text}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='font-size: {FS_BODY}px; font-weight: 500; color: {color};'>"
            f"{text}</div>",
            unsafe_allow_html=True
        )


# ---------------------------------------------------------------------------
# Multiselect with Select All / Deselect All
# ---------------------------------------------------------------------------

def multiselect_with_controls(label: str, options: list, key: str):
    """
    Render a st.multiselect followed by compact Select All / Deselect All buttons.

    The current selection is clamped to the available options before rendering
    so stale selections from a previous filter state are silently dropped.

    Parameters
    ----------
    label   : Widget label shown above the multiselect.
    options : Available choices (already sorted/filtered by the caller).
    key     : Streamlit session state key for the multiselect value.
    """
    # Clamp stale selections to the current available options
    if key in st.session_state:
        st.session_state[key] = [
            x for x in st.session_state[key] if x in options
        ]

    st.multiselect(label, options, key=key)

    # ---> NEW: Inject an invisible marker to target these specific buttons with our alternate CSS
    st.markdown('<div class="light-btn-marker" style="display:none;"></div>', unsafe_allow_html=True)

    cb1, cb2 = st.columns(2)
    
    # ---> NEW: Inject the invisible marker INSIDE the column block
    cb1.markdown('<div class="light-btn-marker" style="display:none;"></div>', unsafe_allow_html=True)
    
    cb1.button(
        "Select All", type="secondary", use_container_width=True,
        on_click=lambda k=key, a=options: st.session_state.update({k: list(a)}),
        key=f"sa_{key}"
    )
    cb2.button(
        "Deselect All", type="secondary", use_container_width=True,
        on_click=lambda k=key: st.session_state.update({k: []}),
        key=f"da_{key}"
    )
