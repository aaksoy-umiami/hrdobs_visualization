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
# Safe Slider Wrappers
# ---------------------------------------------------------------------------

def safe_slider(label: str, min_value: float, max_value: float, key: str, **kwargs):
    """
    A wrapper around st.slider that guarantees the session_state value 
    never violates the min/max bounds, preventing Streamlit exceptions.
    """
    # Failsafe: Ensure max is always strictly greater than min
    if min_value >= max_value:
        max_value = min_value + kwargs.get('step', 1.0)

    # Check and sanitize current state
    curr_val = st.session_state.get(key)
    if curr_val is not None:
        if isinstance(curr_val, tuple):
            v0 = max(min_value, min(curr_val[0], max_value))
            v1 = max(min_value, min(curr_val[1], max_value))
            st.session_state[key] = (v0, v1) if v0 <= v1 else (min_value, max_value)
        else:
            st.session_state[key] = max(min_value, min(curr_val, max_value))
            
    return st.slider(label, min_value=min_value, max_value=max_value, key=key, **kwargs)


def dynamic_range_slider(label: str, global_min: float, global_max: float, data_min: float, data_max: float, key: str, **kwargs):
    """
    Range slider that respects data bounds while remembering if the user 
    intended to be fully 'zoomed out' at the edges. Also prevents min/max crashes.
    """
    # Failsafe: Ensure valid bounds
    if data_min >= data_max:
        data_max = data_min + kwargs.get('step', 1.0)
        
    last_min_key = f"_last_t_min_{key}"
    last_max_key = f"_last_t_max_{key}"
    
    last_t_min = st.session_state.get(last_min_key, global_min)
    last_t_max = st.session_state.get(last_max_key, global_max)
    curr_val = st.session_state.get(key, (global_min, global_max))

    # If user was essentially at the bounds, snap to new bounds
    if curr_val[0] <= last_t_min + 0.1 and curr_val[1] >= last_t_max - 0.1:
        new_val = (data_min, data_max)
    else:
        # Otherwise, clamp their custom selection
        v0 = max(data_min, min(curr_val[0], data_max))
        v1 = max(data_min, min(curr_val[1], data_max))
        new_val = (v0, v1) if v0 <= v1 else (data_min, data_max)

    # Update state
    st.session_state[key] = new_val
    st.session_state[last_min_key] = data_min
    st.session_state[last_max_key] = data_max

    return st.slider(label, min_value=data_min, max_value=data_max, key=key, **kwargs)

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
            