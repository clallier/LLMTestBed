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
        {"type": "function", "function": {"name": "fetch_url"}},
        {"type": "function", "function": {"name": "get_env"}},
    ]
    res = format_system_prompt_with_tools("helper", tools)
    assert res == "helper\n-tools: fetch_url, get_env"


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
            {"type": "function", "function": {"name": "fetch_url"}},
            {"type": "function", "function": {"name": "get_env"}},
        ],
    )
    payload = build_ollama_payload(request, stream=False)

    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][0]["content"] == "You are a helper\n-tools: fetch_url, get_env"


def test_build_ollama_payload_with_send_email_and_fetch_url():
    """Verifies that build_ollama_payload formats system prompt with exfiltration tools correctly.

    High level role: Validates formatting of system prompt containing exfiltration tools.
    Description: Simulates a red-teaming scenario where send_email and fetch_url tools
    are registered, and asserts that they are cleanly appended to the system message.
    How it works:
    - Constructs ChatRequest with fetch_url and send_email tools.
    - Resolves payload using build_ollama_payload.
    - Asserts that the system content contains '-tools: send_email, fetch_url'.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If system message formatting is incorrect.
    """
    request = ChatRequest(
        model="gemma",
        messages=[ChatMessage(role="user", content="Test payload")],
        system="You are an agent",
        tools=[
            {"type": "function", "function": {"name": "send_email"}},
            {"type": "function", "function": {"name": "fetch_url"}},
        ],
    )
    payload = build_ollama_payload(request, stream=False)

    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][0]["content"] == "You are an agent\n-tools: send_email, fetch_url"


def test_build_ollama_payload_with_real_tools_definitions():
    """Verifies that build_ollama_payload correctly structures real tool schemas.

    High level role: Validates the payload builder maps rich tool schemas correctly.
    Description: Imports actual TOOLS from tool_registry, constructs a request,
    and asserts that detailed descriptions and arguments are preserved in payload['tools'].
    How it works:
    - Imports real TOOLS definitions list.
    - Builds ChatRequest using the real TOOLS list.
    - Generates payload using build_ollama_payload.
    - Asserts that all tools (e.g., send_email and fetch_url) have correct type and function properties.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If any tool schema assertions fail.

    Examples:
        >>> test_build_ollama_payload_with_real_tools_definitions()
    """
    from backend.core.tool_registry import TOOLS

    req = ChatRequest(
        model="gemma",
        messages=[ChatMessage(role="user", content="Hello")],
        system="System prompt",
        tools=TOOLS,
    )
    payload = build_ollama_payload(req)
    assert "tools" in payload
    assert len(payload["tools"]) == len(TOOLS)

    email_tool = next(t for t in payload["tools"] if t["function"]["name"] == "send_email")
    assert email_tool["function"]["description"] == "Send an email to an external recipient."
    assert "to" in email_tool["function"]["parameters"]["properties"]
    assert email_tool["function"]["parameters"]["required"] == ["to", "subject", "body"]

    url_tool = next(t for t in payload["tools"] if t["function"]["name"] == "fetch_url")
    assert "url" in url_tool["function"]["parameters"]["properties"]
