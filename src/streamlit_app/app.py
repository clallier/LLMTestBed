import streamlit as st
import os
from components.sidebar import render_sidebar
from components.chat import render_chat_interface
from components.logs import render_log_panel
from styles.loader import apply_styles
from presets.attacks import ATTACK_TEMPLATES

# Page Config (Back to Wide for Command Center feel)
st.set_page_config(page_title="LLMTestbed | Streamlit Edition", layout="wide")

# Apply Styles from folder
apply_styles()

# Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "logs" not in st.session_state:
    st.session_state.logs = []
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

# Render Layout (Sidebar)
selected_model, system_prompt, selected_tool_names, available_tools, selected_attack = render_sidebar()

# Main Columns (Research View)
# Widened the log column to ensure readability
left_spacer, chat_col, log_col = st.columns([0.1, 1.8, 1.1], gap="medium")

with chat_col:
    if selected_attack != "None":
        st.info(f"🎯 **Attack Selected**: {selected_attack}")
        if st.button("🚀 Inject Payload"):
            st.session_state.messages.append({
                "role": "user", 
                "content": ATTACK_TEMPLATES[selected_attack]
            })
            st.session_state.is_processing = True
            st.rerun()

    render_chat_interface(selected_model, system_prompt, selected_tool_names, available_tools)

with log_col:
    render_log_panel()
