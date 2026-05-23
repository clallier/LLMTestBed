"""Tests for the logs component rendering."""

from streamlit.testing.v1 import AppTest

from tests.frontend.utils_streamlit_logs import run_logs_component


def test_logs_rendering():
    """Verifies that the logs panel renders correctly using AppTest.

    Sets up two log entries and checks that the panel renders without
    exceptions, displays the correct title, and creates expanders in
    reverse chronological order (RESPONSE first, REQUEST second).

    Returns:
        None
    """
    at = AppTest.from_function(run_logs_component).run()

    assert not at.exception

    assert at.markdown[0].value == "### 📝 Live Logs"

    # Rendered in reverse order (newest first), so RESPONSE comes first
    assert len(at.expander) == 2

    expander1 = at.expander[0]
    assert "12:00:01 RESPONSE" in expander1.label

    expander2 = at.expander[1]
    assert "12:00:00 REQUEST" in expander2.label
