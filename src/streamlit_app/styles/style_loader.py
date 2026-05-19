"""
Streamlit CSS Style Loader Utility.

High level role: Loads theme-aware external CSS stylesheet styles into the page.
"""
from pathlib import Path

import streamlit as st


def apply_styles():
    """Reads the main.css file relative to this script and injects it."""
    css_path = Path(__file__).parent / "main.css"

    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
