"""
Live logs component for trace and reasoning visualization.

High-level role: Implements the expandable Trace Explorer UI panel with
custom theme-aware styles and reasoning isolated blocks.
"""
import streamlit as st


def render_log_panel():
    """Renders the live logs panel in the Streamlit interface.

    High level role: Iterates through the session state logs in reverse order
    and displays them in interactive expander blocks.

    Returns:
        None
    """
    st.markdown("### 📝 Live Logs")
    st.markdown("---")

    # Log container
    for log in reversed(st.session_state.logs):
        badge_html = f'<span class="log-badge badge-{log["type"]}">{log["type"]}</span>'

        with st.expander(f"{log['time']} {log['type']}", expanded=False):
            # Header with Badge
            st.markdown(
                f"{badge_html} **{log['type']}** at {log['time']}",
                unsafe_allow_html=True
            )

            # Show Reasoning if available (Critical parity feature)
            is_resp = log['type'] == 'RESPONSE'
            has_thinking = isinstance(log['data'], dict) and log['data'].get('thinking')
            if is_resp and has_thinking:
                thinking_text = log["data"]["thinking"]
                st.markdown(
                    f'<div class="thinking-log">🧠 <b>REASONING:</b><br>{thinking_text}</div>',
                    unsafe_allow_html=True
                )

            # Main Data
            st.json(log['data'])
