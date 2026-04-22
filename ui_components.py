# -*- coding: utf-8 -*-
"""
ui_components.py
----------------
Reusable Streamlit widget helpers and state management utilities.

Every function here encapsulates a recurring visual pattern so that call
sites stay concise and the visual behavior is defined in exactly one place.
All style values are imported from ui_layout rather than hardcoded, so
changes to the design tokens automatically propagate here.
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
    'sm':  5,   
    'md':  8,   
    'lg':  28,  
}

def spacer(size: str = 'sm'):
    """Vertical whitespace."""
    px = _SPACER_SIZES.get(size, _SPACER_SIZES['sm'])
    st.markdown(
        f"<div style='height: {px}px;'></div>",
        unsafe_allow_html=True
    )


# ---------------------------------------------------------------------------
# Sidebar label
# ---------------------------------------------------------------------------

def sidebar_label(text: str, enabled: bool = True, size: str = 'body'):
    """Render an inline HTML label above or beside a Streamlit widget."""
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

def multiselect_with_controls(label: str, options: list, key: str, **kwargs):
    """Render a st.multiselect followed by compact Select All / Deselect All buttons."""
    if key in st.session_state:
        st.session_state[key] = [
            x for x in st.session_state[key] if x in options
        ]

    # **kwargs allows format_func, help, etc. to pass through to the native widget
    st.multiselect(label, options, key=key, **kwargs)

    st.markdown('<div class="light-btn-marker" style="display:none;"></div>', unsafe_allow_html=True)

    cb1, cb2 = st.columns(2)
    
    cb1.markdown('<div class="light-btn-marker" style="display:none;"></div>', unsafe_allow_html=True)
    
    cb1.button(
        "Select All", type="secondary", width="stretch",
        on_click=lambda k=key, a=options: st.session_state.update({k: list(a)}),
        key=f"sa_{key}"
    )
    cb2.button(
        "Deselect All", type="secondary", width="stretch",
        on_click=lambda k=key: st.session_state.update({k: []}),
        key=f"da_{key}"
    )

# ---------------------------------------------------------------------------
# State Management Utilities
# ---------------------------------------------------------------------------

def init_state(key: str, default_value: any):
    """Safely initializes a session state key if it doesn't exist."""
    if key not in st.session_state:
        st.session_state[key] = default_value

def consume_flag(key: str) -> bool:
    """Reads and removes a boolean flag from session state, returning False if missing."""
    return st.session_state.pop(key, False)

def sync_namespace(prefix: str, dict_key: str):
    """
    Packs all session state variables starting with `prefix` into a persistent 
    dictionary at `dict_key`. Useful for cross-tab persistence.
    """
    if dict_key not in st.session_state:
        st.session_state[dict_key] = {}
    for k in list(st.session_state.keys()):
        if k.startswith(prefix):
            st.session_state[dict_key][k] = st.session_state[k]
            