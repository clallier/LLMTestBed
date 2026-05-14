import pytest
from streamlit.testing.v1 import AppTest
from streamlit_app.components.logs import render_log_panel

def run_logs_component():
    """Wrapper function to test the isolated logs component."""
    import streamlit as st
    from streamlit_app.components.logs import render_log_panel
    if "logs" not in st.session_state:
        st.session_state.logs = [
            {"time": "12:00:00", "type": "REQUEST", "data": {"model": "test-model"}},
            {"time": "12:00:01", "type": "RESPONSE", "data": {"content": "Hello", "thinking": "Let me think..."}}
        ]
    render_log_panel()

def test_logs_rendering():
    """Verifies that the logs panel renders correctly using AppTest."""
    at = AppTest.from_function(run_logs_component).run()
    
    # Assert there are no exceptions
    assert not at.exception
    
    # Assert the title rendered
    assert at.markdown[0].value == "### 📝 Live Logs"
    
    # Assert expanders are created for the logs (we have 2 logs)
    # They are rendered in reverse order (newest first), so RESPONSE comes first
    assert len(at.expander) == 2
    
    # Validate the first expander (RESPONSE)
    expander1 = at.expander[0]
    assert "12:00:01 RESPONSE" in expander1.label
    
    # Validate the second expander (REQUEST)
    expander2 = at.expander[1]
    assert "12:00:00 REQUEST" in expander2.label
