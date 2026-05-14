import pytest
from pydantic import ValidationError
from backend.schemas.chat import ChatMessage, ChatRequest

def test_chat_message_valid():
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"

def test_chat_message_invalid():
    with pytest.raises(ValidationError):
        # Missing content
        ChatMessage(role="user")

def test_chat_request_minimal_valid():
    req = ChatRequest(
        model="gemma",
        messages=[{"role": "user", "content": "hi"}]
    )
    assert req.model == "gemma"
    assert len(req.messages) == 1
    assert req.messages[0].role == "user"
    assert req.stream is False
    assert req.system is None

def test_chat_request_full_valid():
    req = ChatRequest(
        model="llama3",
        messages=[{"role": "assistant", "content": "hello"}],
        system="You are a bot",
        stream=True,
        options={"temperature": 0.7},
        tools=[{"type": "function"}]
    )
    assert req.system == "You are a bot"
    assert req.stream is True
    assert req.options["temperature"] == 0.7
    assert len(req.tools) == 1

def test_chat_request_invalid():
    with pytest.raises(ValidationError):
        # Missing required 'model'
        ChatRequest(messages=[{"role": "user", "content": "hi"}])
