import pytest

from backend.core.payload_builder import build_ollama_payload
from backend.schemas.chat import ChatMessage, ChatRequest


def test_build_ollama_payload_basic():
    request = ChatRequest(model="gemma", messages=[ChatMessage(role="user", content="Hello")])
    payload = build_ollama_payload(request, stream=False)

    assert payload["model"] == "gemma"
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["role"] == "user"
    assert payload["stream"] is False


def test_build_ollama_payload_with_system():
    request = ChatRequest(
        model="gemma",
        messages=[ChatMessage(role="user", content="Hello")],
        system="You are a helper",
    )
    payload = build_ollama_payload(request, stream=True)

    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][0]["content"] == "You are a helper"
    assert payload["messages"][1]["role"] == "user"
    assert payload["stream"] is True


def test_build_ollama_payload_with_tools():
    request = ChatRequest(
        model="gemma",
        messages=[ChatMessage(role="user", content="Hello")],
        tools=[{"type": "function", "function": {"name": "test_tool"}}],
    )
    payload = build_ollama_payload(request)

    assert "tools" in payload
    assert payload["tools"][0]["function"]["name"] == "test_tool"
