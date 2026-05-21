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


def test_format_system_prompt_with_tools():
    """Verifies that format_system_prompt_with_tools formats the system prompt correctly.

    High level role: Validates tools listing suffix in system prompt.
    Description: Verifies that tool names are appended with comma separation at the end
    of the system prompt when tools are present, and returns the original prompt when no tools exist.
    How it works:
    - Calls helper with empty tools and asserts original prompt is returned.
    - Calls helper with list of tools and asserts correct '-tools: name1, name2' line is appended.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If any assertions fail.
    """
    from backend.core.payload_builder import format_system_prompt_with_tools

    # 1. No tools
    assert format_system_prompt_with_tools("helper", None) == "helper"
    assert format_system_prompt_with_tools("helper", []) == "helper"

    # 2. With tools
    tools = [
        {"type": "function", "function": {"name": "web_fetch"}},
        {"type": "function", "function": {"name": "env"}},
    ]
    res = format_system_prompt_with_tools("helper", tools)
    assert res == "helper\n-tools: web_fetch, env"


def test_build_ollama_payload_with_system_and_tools():
    """Verifies that build_ollama_payload formats system prompt with tools correctly.

    High level role: Validates integration of tools listing in payload builder.
    Description: Verifies that the injected system prompt contains the expected '-tools:' line
    when tools are selected in the ChatRequest object.
    How it works:
    - Creates a ChatRequest with system prompt and list of tools.
    - Builds the payload.
    - Asserts that the system prompt message content includes the expected list of tools.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If any assertions fail.
    """
    request = ChatRequest(
        model="gemma",
        messages=[ChatMessage(role="user", content="Hello")],
        system="You are a helper",
        tools=[
            {"type": "function", "function": {"name": "web_fetch"}},
            {"type": "function", "function": {"name": "env"}}
        ]
    )
    payload = build_ollama_payload(request, stream=False)

    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][0]["content"] == "You are a helper\n-tools: web_fetch, env"
