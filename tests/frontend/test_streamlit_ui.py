from unittest.mock import patch

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest


@pytest.fixture
def mocked_app():
    """Fixture that provides a mocked AppTest instance."""
    with (
        patch("streamlit_app.components.sidebar.fetch_models") as mock_models,
        patch("streamlit_app.components.sidebar.fetch_tools") as mock_tools,
        patch("streamlit_app.components.chat.render_streaming_response") as mock_exec,
    ):
        mock_models.return_value = [{"name": "gemma-test"}]
        mock_tools.return_value = []

        def fake_exec(processor, payload):
            st.session_state.messages.append({"role": "assistant", "content": "Fake response"})

        mock_exec.side_effect = fake_exec

        at = AppTest.from_file("src/streamlit_app/app.py").run()
        yield at


def test_app_boots_and_renders_title(mocked_app):
    """Verifies that the app successfully boots and renders the main titles."""
    assert not mocked_app.exception
    assert mocked_app.header[0].value == "Agent Attack Sandbox"


def test_sidebar_model_selection(mocked_app):
    """Verifies that the model selection dropdown gets populated by the mock."""
    model_selectbox = mocked_app.sidebar.selectbox[0]
    assert model_selectbox.value == "gemma-test"


def test_chat_input_changes_processing_state(mocked_app):
    """Verifies that submitting a chat message triggers the processing state and response."""
    # Ensure we are in Sandbox view (default)
    chat_input = mocked_app.chat_input[0]
    chat_input.set_value("Test Message").run(timeout=30)

    # After the run(), the app should have processed the message and reset is_processing to False
    assert mocked_app.session_state["is_processing"] is False
    assert len(mocked_app.session_state["messages"]) == 2
    assert mocked_app.session_state["messages"][0]["content"] == "Test Message"
    assert mocked_app.session_state["messages"][1]["content"] == "Fake response"
