import pytest
from pydantic import ValidationError

from backend.schemas.chat import ChatMessage, ChatRequest


def test_chat_message_valid():
    msg = ChatMessage(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"


def test_chat_message_multimodal_valid():
    msg = ChatMessage(role="user", content="Hello", images=["base64_image_data"])
    assert msg.role == "user"
    assert msg.content == "Hello"
    assert msg.images == ["base64_image_data"]


def test_chat_message_invalid():
    with pytest.raises(ValidationError):
        ChatMessage.model_validate({"role": "user"})


def test_chat_request_minimal_valid():
    req = ChatRequest(model="gemma", messages=[{"role": "user", "content": "hi"}])
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
        tools=[{"type": "function"}],
    )
    assert req.system == "You are a bot"
    assert req.stream is True
    assert req.options is not None
    assert req.options["temperature"] == 0.7
    assert req.tools is not None
    assert len(req.tools) == 1


def test_chat_request_invalid():
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"messages": [{"role": "user", "content": "hi"}]})
