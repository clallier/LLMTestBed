"""Utility functions for streamlit logs component tests.

These functions use internal imports to isolate streamlit's state management.
PLC0415 is intentionally suppressed here per project convention for test utilities.
"""


def run_logs_component():
    """Render the isolated logs component with pre-seeded session state.

    Sets up a session state with two sample log entries (REQUEST and RESPONSE)
    and calls ``render_log_panel()`` to test its rendering in isolation.

    Returns:
        None
    """
    import streamlit as st

    from streamlit_app.components.logs import render_log_panel

    if "logs" not in st.session_state:
        st.session_state.logs = [
            {"time": "12:00:00", "type": "REQUEST", "data": {"model": "test-model"}},
            {
                "time": "12:00:01",
                "type": "RESPONSE",
                "data": {"content": "Hello", "thinking": "Let me think..."},
            },
        ]
    render_log_panel()
