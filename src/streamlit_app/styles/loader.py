import streamlit as st
import os

def apply_styles():
    """Reads the main.css file and injects it into the Streamlit app."""
    # We use a relative path based on the project root
    css_path = "src/streamlit_app/styles/main.css"
    
    if os.path.exists(css_path):
        with open(css_path) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        # Fallback for different run contexts
        alt_path = "styles/main.css"
        if os.path.exists(alt_path):
            with open(alt_path) as f:
                st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
