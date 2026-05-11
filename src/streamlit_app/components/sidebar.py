import streamlit as st
from api.client import fetch_models, fetch_tools
from presets.system import SYSTEM_PRESETS
from presets.attacks import ATTACK_TEMPLATES

def render_sidebar():
    with st.sidebar:
        st.title("🛡️ LLMTestbed")
        st.markdown("---")
        
        # Model Selection
        models = fetch_models()
        model_names = [m["name"] for m in models] if models else ["gemma4:e4b"]
        selected_model = st.selectbox(
            "Select Model", 
            model_names, 
            disabled=st.session_state.is_processing
        )

        # System Presets
        selected_preset = st.selectbox(
            "System Preset", 
            list(SYSTEM_PRESETS.keys()), 
            disabled=st.session_state.is_processing
        )
        system_prompt = st.text_area(
            "System Prompt", 
            SYSTEM_PRESETS[selected_preset], 
            height=150, 
            disabled=st.session_state.is_processing
        )

        # Attack Templates
        st.markdown("### 🏹 Attack Templates")
        selected_attack = st.selectbox(
            "Load Attack",
            ["None"] + list(ATTACK_TEMPLATES.keys()),
            disabled=st.session_state.is_processing
        )
        
        # Tools
        st.markdown("### 🛠️ Mock Tools")
        available_tools = fetch_tools()
        selected_tool_names = []
        if available_tools:
            for tool in available_tools:
                if st.checkbox(tool["function"]["name"], value=True, disabled=st.session_state.is_processing):
                    selected_tool_names.append(tool["function"]["name"])
        
        if st.button("Clear History", type="secondary", use_container_width=True):
            st.session_state.messages = []
            st.session_state.logs = []
            st.rerun()
            
        return selected_model, system_prompt, selected_tool_names, available_tools, selected_attack
