from pydantic import functional_serializers
import streamlit as st
from typing import Tuple, List, Dict, Any
from streamlit_app.api.client import fetch_models, fetch_tools
from streamlit_app.presets.system import SYSTEM_PRESETS
from streamlit_app.presets.attacks import ATTACK_TEMPLATES

def render_sidebar() -> Tuple[str, str, List[str], List[Dict[str, Any]], str]:
    """Renders the sidebar and returns the selected configuration."""
    with st.sidebar:
        # Official branding logo
        st.logo("src/streamlit_app/assets/logo_text.png", icon_image="src/streamlit_app/assets/logo.png", size="large")
        
        # Configuration controls (Model, Tools, etc.)
        selected_model = _render_model_selection()
        system_prompt = _render_system_presets()
        selected_attack = _render_attack_presets()
        selected_tool_names, available_tools = _render_tool_selection()
        
        if st.button("Clear History", type="secondary", use_container_width=True):
            st.session_state.messages = []
            st.session_state.raw_messages = []
            st.session_state.logs = []
            st.rerun()
            
        return selected_model, system_prompt, selected_tool_names, available_tools, selected_attack

def _render_model_selection() -> str:
    """Fetches and renders the model selection dropdown."""
    models = fetch_models()
    model_names = [m.get("name", m) if isinstance(m, dict) else m for m in models] if isinstance(models, list) else []
    
    if not model_names:
        model_names = ["No model available. Please run 'ollama serve' first."]
        
    return st.selectbox("Select Model", model_names)

def _render_system_presets() -> str:
    """Renders system prompt presets and the editable text area."""
    selected_preset = st.selectbox("System Preset", list(SYSTEM_PRESETS.keys()))
    return st.text_area("System Prompt", SYSTEM_PRESETS[selected_preset], height=150)

def _render_attack_presets() -> str:
    """Renders the dropdown for selecting attack templates."""
    st.markdown("### 🏹 Attack Templates")
    return st.selectbox("Load Attack", ["None"] + list(ATTACK_TEMPLATES.keys()))

def _render_tool_selection() -> Tuple[List[str], List[Dict[str, Any]]]:
    """Fetches and renders the tool selection checkboxes."""
    st.markdown("### 🛠️ Mock Tools")
    available_tools = fetch_tools()
    selected_tool_names = []
    
    if available_tools:
        for tool in available_tools:
            if st.checkbox(tool["function"]["name"], value=True):
                selected_tool_names.append(tool["function"]["name"])
                
    return selected_tool_names, available_tools
