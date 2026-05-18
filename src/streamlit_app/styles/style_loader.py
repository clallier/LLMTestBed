from pathlib import Path

import streamlit as st


def apply_styles():
    """Reads the main.css file relative to this script and injects it."""
    css_path = Path(__file__).parent / "main.css"
    
    if css_path.exists():
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
