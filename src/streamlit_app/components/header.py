"""
Streamlit Header Navigation Component.

High level role: Renders segmented control navigation tabs.
"""

import streamlit as st


def render_top_nav():
    """
    Renders the page header with navigation and branding.
    Returns the currently selected view.
    """
    with st.container():
        view = st.segmented_control(
            "Navigation",
            ["Sandbox", "Observability"],
            selection_mode="single",
            default="Sandbox",
            label_visibility="collapsed",
            key="top_nav",
        )

    return view


def close_top_nav():
    """Closes the content wrapper div opened by render_top_nav."""
    st.markdown("</div>", unsafe_allow_html=True)
