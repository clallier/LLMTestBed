import pytest
from unittest.mock import MagicMock, patch
import streamlit as st
from streamlit_app.components.processors.chat import ChatProcessor

class TestStreamlitChatComponent:
    """
    Unit tests for the Streamlit chat completions processor stream handling.

    High level role: Guarantees correct accumulation of responses, tool logs, and safety tags.
    """

    @pytest.fixture(autouse=True)
    def mock_session_state(self, monkeypatch):
        """
        Mocks Streamlit session state logs and messages for unit testing.

        High level role: Provides isolated session state cache to keep unit tests fast.
        """
        session_state = MagicMock()
        session_state.logs = []
        session_state.messages = []
        session_state.raw_messages = []
        monkeypatch.setattr(st, "session_state", session_state)
        return session_state

    @pytest.fixture
    def processor(self):
        """Provides a fully initialized ChatProcessor target instance."""
        return ChatProcessor("http://mock-backend")

    def test_process_chunk_content(self, processor):
        """Verifies that assistant content chunks are accumulated and returned."""
        state = {"full_response": "", "thinking_content": ""}
        chunk = {"message": {"role": "assistant", "content": "Hello world"}}
        
        result = processor._process_chunk(chunk, state)
        
        assert result == "Hello world"
        assert state["full_response"] == "Hello world"

    def test_process_chunk_thinking(self, processor):
        """Verifies that thinking chunks update the thinking state and return None."""
        state = {"full_response": "", "thinking_content": ""}
        chunk = {"message": {"role": "assistant", "content": "", "thinking": "Evaluating prompt..."}}
        
        result = processor._process_chunk(chunk, state)
        
        assert result is None
        assert state["thinking_content"] == "Evaluating prompt..."

    def test_process_chunk_tool_calls(self, processor):
        """Verifies that tool call chunks are styled, logged, and returned."""
        state = {"full_response": "", "thinking_content": ""}
        tool_calls = [{"function": {"name": "read_sensitive_file", "arguments": {"filename": ".env"}}}]
        chunk = {"message": {"role": "assistant", "content": "", "tool_calls": tool_calls}}
        
        result = processor._process_chunk(chunk, state)
        
        assert result is not None
        assert "🛠️ **[Tool Call] read_sensitive_file**" in result
        assert ".env" in result
        
        assert len(st.session_state.logs) == 1
        assert st.session_state.logs[0]["type"] == "TOOL"
        assert st.session_state.logs[0]["data"] == tool_calls

    def test_process_chunk_tool_response(self, processor):
        """Verifies that tool execution responses are styled, logged, and returned."""
        state = {"full_response": "", "thinking_content": ""}
        tr = {"name": "execute_command", "content": "sandbox_user"}
        chunk = {"tool_response": tr}
        
        result = processor._process_chunk(chunk, state)
        
        assert result is not None
        assert "⚙️ **[Tool Response] execute_command**" in result
        assert "sandbox_user" in result
        
        assert len(st.session_state.logs) == 1
        assert st.session_state.logs[0]["type"] == "TOOL_RESPONSE"
        assert st.session_state.logs[0]["data"] == tr

    def test_process_chunk_security(self, processor):
        """Verifies that security logs are processed and recorded."""
        state = {"full_response": "", "thinking_content": ""}
        security_data = {"risk_score": 0.1, "target": "user_prompt"}
        chunk = {"security": security_data}
        
        result = processor._process_chunk(chunk, state)
        
        assert result is None
        assert len(st.session_state.logs) == 1
        assert st.session_state.logs[0]["type"] == "SECURITY"
        assert st.session_state.logs[0]["data"] == security_data

    def test_process_chunk_tool_grouping(self, processor):
        """
        Verifies that parallel tool calls and responses are tracked and grouped
        together dynamically during streaming.
        """
        state = {"full_response": "", "thinking_content": "", "tool_runs": {}}
        
        # 1. Process parallel tool call chunk
        tool_calls = [
            {"id": "call_1", "type": "function", "function": {"name": "execute_command", "arguments": {"command": "ls"}}},
            {"id": "call_2", "type": "function", "function": {"name": "read_sensitive_file", "arguments": {"filename": "config.json"}}}
        ]
        chunk_calls = {"message": {"role": "assistant", "content": "", "tool_calls": tool_calls}}
        
        res1 = processor._process_chunk(chunk_calls, state)
        
        assert res1 is not None
        assert "execute_command" in res1
        assert "read_sensitive_file" in res1
        assert "*⌛ Executing tool in parallel...*" in res1
        
        # 2. Process first tool response chunk
        chunk_res1 = {"tool_response": {"id": "call_1", "name": "execute_command", "content": "file1.txt\nfile2.txt"}}
        res2 = processor._process_chunk(chunk_res1, state)
        
        assert res2 is not None
        assert "file1.txt" in res2
        assert "config.json" in res2
        assert "file1.txt\nfile2.txt" in res2
        assert "*⌛ Executing tool in parallel...*" in res2
        
        # 3. Process second tool response chunk
        chunk_res2 = {"tool_response": {"id": "call_2", "name": "read_sensitive_file", "content": "SECRET_DB_URL=postgres..."}}
        res3 = processor._process_chunk(chunk_res2, state)
        
        assert res3 is not None
        assert "file1.txt" in res3
        assert "SECRET_DB_URL=postgres" in res3
        assert "*⌛ Executing tool in parallel...*" not in res3

    def test_build_chat_payload_role_mapping(self, processor):
        """Verifies that build_chat_payload maps 'tools' role to 'assistant' for the backend."""
        st.session_state.raw_messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "tool call detail", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "x", "arguments": {}}}]},
            {"role": "tool", "name": "x", "content": "tool reply"}
        ]
        
        payload = processor.build_chat_payload(
            selected_model="test-model",
            system_prompt="system test",
            selected_tool_names=[],
            available_tools=[]
        )
        
        messages = payload["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "tool"

    def test_render_message(self, monkeypatch):
        """Verifies that render_message calls st.chat_message with correct role and content."""
        from streamlit_app.components.chat import render_message
        
        chat_message_mock = MagicMock()
        monkeypatch.setattr(st, "chat_message", chat_message_mock)
        
        # Test tools role receives avatar='⚙️'
        message_tools = {"role": "tools", "content": "tool details"}
        render_message(message_tools)
        chat_message_mock.assert_called_with("tools", avatar="⚙️")
        
        # Test default role does not receive custom avatar
        message_user = {"role": "user", "content": "user query"}
        render_message(message_user)
        chat_message_mock.assert_called_with("user")


def run_message_history_tools():
    """Wrapper function to test isolated message history rendering with tool role."""
    import streamlit as st
    from streamlit_app.components.chat import render_message_history
    st.session_state.messages = [
        {"role": "user", "content": "hello"},
        {"role": "tools", "content": "tool call output"},
        {"role": "assistant", "content": "final answer"}
    ]
    render_message_history()


def run_execute_chat_request():
    """Wrapper function to test execute_chat_request with dynamic streaming."""
    import streamlit as st
    from unittest.mock import patch
    from streamlit_app.components.chat import render_streaming_response
    from streamlit_app.components.processors.chat import ChatProcessor
    
    st.session_state.messages = []
    st.session_state.raw_messages = []
    
    def mock_stream(payload):
        yield ("tools", "🛠️ **[Tool Call] read_sensitive_file**")
        yield ("assistant", "Hello! Here is the file content.")
        
    processor = ChatProcessor("http://mock-backend")
    with patch.object(processor, "stream_response", side_effect=mock_stream):
        render_streaming_response(processor, {"model": "test"})


def test_render_message_history_roles():
    """Verifies that render_message_history renders custom 'tools' bubbles and standard bubbles."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_function(run_message_history_tools).run()
    assert not at.exception
    
    assert len(at.chat_message) == 3
    assert at.chat_message[0].name == "user"
    assert at.chat_message[1].name == "tools"
    assert at.chat_message[2].name == "assistant"
    
    assert at.chat_message[0].markdown[0].value == "hello"
    assert at.chat_message[1].markdown[0].value == "tool call output"
    assert at.chat_message[2].markdown[0].value == "final answer"


def test_execute_chat_request_creates_separate_blocks():
    """Verifies that render_streaming_response creates separate tools and assistant chat message blocks."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_function(run_execute_chat_request).run()
    assert not at.exception
    
    assert len(at.chat_message) == 2
    assert at.chat_message[0].name == "tools"
    assert at.chat_message[1].name == "assistant"
    
    assert "🛠️ **[Tool Call] read_sensitive_file**" in at.chat_message[0].markdown[0].value
    assert "Hello! Here is the file content." in at.chat_message[1].markdown[0].value
    
    messages = at.session_state["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "tools"
    assert messages[0]["content"] == "🛠️ **[Tool Call] read_sensitive_file**"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hello! Here is the file content."
