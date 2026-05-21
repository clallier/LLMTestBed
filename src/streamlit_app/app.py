"""
Streamlit Multi-Agent Security Sandbox App.

High level role: Entry point for the frontend Streamlit dashboard, layouts, and routes.
"""
import streamlit as st

from streamlit_app.components.chat import process_assistant_response, render_message_history
from streamlit_app.components.header import close_top_nav, render_top_nav
from streamlit_app.components.observability import render_observability_hub
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.presets.attacks import FLAT_ATTACK_TEMPLATES
from streamlit_app.styles.style_loader import apply_styles

# Page Config
st.set_page_config(
    page_title="LLMTestbed",
    page_icon="src/streamlit_app/assets/logo.png",
    layout="wide"
)

# Apply Styles from folder
apply_styles()

# 1. Render Fixed Top Navigation
view = render_top_nav()

# 2. Render Sidebar (Model configs, tools, etc.)
(
    selected_model,
    system_prompt,
    selected_tool_names,
    available_tools,
    selected_attack
) = render_sidebar()

# 3. Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
if "raw_messages" not in st.session_state:
    st.session_state.raw_messages = []
if "logs" not in st.session_state:
    st.session_state.logs = []
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

# 4. Main Application Logic
if view == "Sandbox":
    st.header("Agent Attack Sandbox")

    if selected_attack != "None":
        st.info(f"Attack Selected: {selected_attack}")
        if st.button("Inject Payload"):
            payload_content = FLAT_ATTACK_TEMPLATES[selected_attack]
            st.session_state.messages.append({
                "role": "user",
                "content": payload_content
            })
            st.session_state.raw_messages.append({
                "role": "user",
                "content": payload_content
            })
            st.session_state.is_processing = True
            st.rerun()

    # Render History and handle Assistant
    render_message_history()

    is_user_turn = (
        st.session_state.is_processing
        and st.session_state.messages
        and st.session_state.messages[-1]["role"] == "user"
    )
    if is_user_turn:
        process_assistant_response(
            selected_model,
            system_prompt,
            selected_tool_names,
            available_tools
        )

    # ROOT LEVEL INPUT - This ensures it sticks to the bottom of the viewport
    if prompt := st.chat_input("Type here and press Enter to attack..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.raw_messages.append({"role": "user", "content": prompt})
        st.session_state.is_processing = True
        st.rerun()

else:
    render_observability_hub()

# Close the content wrapper opened in the top nav
close_top_nav()
