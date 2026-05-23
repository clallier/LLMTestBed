"""
Isolated Streamlit AppTest helper wrappers for Chat component testing.

High level role: Contains isolated functions called by AppTest context to test rendering
of chat message histories and dynamic response streaming.
"""


def run_message_history_tools():
    """Wrapper function to test isolated message history rendering with tool role.

    High level role: Provides an isolated Streamlit context to render message history.

    Arguments:
        None

    Returns:
        None
    """
    import streamlit as st

    from streamlit_app.components.chat import render_message_history

    st.session_state.messages = [
        {"role": "user", "content": "hello"},
        {"role": "tools", "content": "tool call output"},
        {"role": "assistant", "content": "final answer"},
    ]
    render_message_history()


def run_execute_chat_request():
    """Wrapper function to test execute_chat_request with dynamic streaming.

    High level role: Provides an isolated Streamlit context to test streaming response.

    Arguments:
        None

    Returns:
        None
    """
    from unittest.mock import patch

    import streamlit as st

    from streamlit_app.components.chat import render_streaming_response
    from streamlit_app.components.processors.chat import ChatProcessor

    st.session_state.messages = []
    st.session_state.raw_messages = []

    def mock_stream(payload):
        yield ("tools", "🛠️ **[Tool Call] read_file**")
        yield ("assistant", "Hello! Here is the file content.")

    processor = ChatProcessor("http://mock-backend")
    with patch.object(processor, "stream_response", side_effect=mock_stream):
        render_streaming_response(processor, {"model": "test"})
