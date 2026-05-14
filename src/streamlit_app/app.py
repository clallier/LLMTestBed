import streamlit as st
from streamlit_app.components.sidebar import render_sidebar
from streamlit_app.components.header import render_top_nav, close_top_nav
from streamlit_app.components.chat import _render_message_history, process_assistant_response
from streamlit_app.components.observability import render_observability_hub
from streamlit_app.styles.style_loader import apply_styles
from streamlit_app.presets.attacks import ATTACK_TEMPLATES

# Page Config (Back to Wide for Command Center feel)
st.set_page_config(page_title="LLMTestbed", layout="wide")

# Apply Styles from folder
apply_styles()

# 1. Render Fixed Top Navigation (Premium SaaS Look)
view = render_top_nav()

# 2. Render Sidebar (Model configs, tools, etc.)
selected_model, system_prompt, selected_tool_names, available_tools, selected_attack = render_sidebar()

# 3. Initialize Session State
if "messages" not in st.session_state:
    st.session_state.messages = []
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
            st.session_state.messages.append({
                "role": "user", 
                "content": ATTACK_TEMPLATES[selected_attack]
            })
            st.session_state.is_processing = True
            st.rerun()

    # Render History and handle Assistant
    _render_message_history()

    if st.session_state.is_processing and st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        process_assistant_response(selected_model, system_prompt, selected_tool_names, available_tools)

    # ROOT LEVEL INPUT - This ensures it sticks to the bottom of the viewport
    if prompt := st.chat_input("Type here and press Enter to attack..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.is_processing = True
        st.rerun()

else:
    render_observability_hub()

# Close the content wrapper opened in the top nav
close_top_nav()
