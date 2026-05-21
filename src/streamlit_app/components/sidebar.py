"""
Streamlit Sidebar Configuration Component.

High level role: Renders model selectors, system prompt presets, and mock tools checklists.
"""
from typing import Any, Dict, List, Tuple

import streamlit as st

from streamlit_app.api.client import fetch_models, fetch_tools
from streamlit_app.presets.attacks import ATTACK_TEMPLATES, FLAT_ATTACK_TEMPLATES
from streamlit_app.presets.system import SYSTEM_PRESETS


def render_sidebar() -> Tuple[str, str, List[str], List[Dict[str, Any]], str]:
    """Renders the sidebar and returns the selected configuration."""
    with st.sidebar:
        # Official branding logo
        st.logo(
            "src/streamlit_app/assets/logo_text.png",
            icon_image="src/streamlit_app/assets/logo.png",
            size="large"
        )

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
    model_names = []
    if isinstance(models, list):
        model_names = [
            m.get("name", m) if isinstance(m, dict) else m
            for m in models
        ]

    if not model_names:
        model_names = ["No model available. Please run 'ollama serve' first."]

    return st.selectbox("Select Model", model_names)


def _render_system_presets() -> str:
    """Renders system prompt presets and the editable text area."""
    selected_preset = st.selectbox("System Preset", list(SYSTEM_PRESETS.keys()))
    return st.text_area("System Prompt", SYSTEM_PRESETS[selected_preset], height=150)


def _render_attack_presets() -> str:
    """Renders a single hierarchical dropdown for selecting attack templates.

    High level role: Renders a single selectbox where attack templates are grouped
    under section headers using indentations and visual divider marks. If a header
    is selected, it acts as a null selection. Renders the 'Inject Payload' button
    directly under the selectbox if an attack is selected.

    Args:
        None

    Returns:
        str: The key of the selected attack template (with leading whitespace stripped),
            or "None" if a header or "None" is selected.

    Raises:
        None

    Examples:
        >>> selected_attack = _render_attack_presets()
    """
    st.markdown("### 🏹 Attack Templates")
    options = ["None"]
    for category, templates in ATTACK_TEMPLATES.items():
        options.append(f"── {category} ──")
        for template_name in templates.keys():
            options.append(f"   {template_name}")

    selected_option = st.selectbox("Load Attack", options)
    selected_attack = "None"
    if selected_option.startswith("   "):
        selected_attack = selected_option.strip()

    if selected_attack != "None":
        if st.button("Inject Payload", type="primary", use_container_width=True):
            payload_content = FLAT_ATTACK_TEMPLATES[selected_attack]
            st.session_state.setdefault("messages", []).append({"role": "user", "content": payload_content})
            st.session_state.setdefault("raw_messages", []).append({"role": "user", "content": payload_content})
            st.session_state.is_processing = True
            st.rerun()

    return selected_attack




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
