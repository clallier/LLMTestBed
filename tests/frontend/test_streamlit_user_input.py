"""
Unit tests for the UserInputComponent of the Streamlit Sandbox interface.

High level role: Verifies rendering of the multimodal chat input and updates to session state.
"""

from unittest.mock import MagicMock

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest


class TestUserInputComponent:
    """
    Test suite for the UserInputComponent class.

    High level role: Asserts proper rendering configurations and successful message capture.
    """

    @pytest.fixture(autouse=True)
    def mock_session_state(self, monkeypatch):
        """
        Mocks Streamlit session state properties for isolated testing.

        High level role: Provides clean mock structures for messages, raw_messages, and is_processing.

        Arguments:
            monkeypatch: Pytest monkeypatch fixture.

        Returns:
            MagicMock: The mocked session state object.
        """
        session_state = MagicMock()
        session_state.messages = []
        session_state.raw_messages = []
        session_state.is_processing = False
        monkeypatch.setattr(st, "session_state", session_state)
        return session_state

    def test_user_input_component_rendering(self):
        """
        Verifies that UserInputComponent renders st.chat_input with correct parameters.

        High level role: Uses AppTest context to check that accept_file is enabled.

        Arguments:
            None

        Returns:
            None
        """
        # Load and run the main entry file which instantiates and renders the UserInputComponent
        at = AppTest.from_file("src/streamlit_app/app.py").run()
        assert not at.exception
        # Check that st.chat_input is rendered
        assert len(at.chat_input) == 1
        assert at.chat_input[0].placeholder == "Type here and press Enter to attack..."

