"""
Ollama Payload Builder Utility.

High level role: Formats ChatRequest models into JSON schemas accepted by Ollama API.
"""

from typing import Any, Dict, List, Optional

from backend.schemas.chat import ChatRequest


def format_system_prompt_with_tools(
    system_prompt: Optional[str], tools: Optional[List[Dict[str, Any]]]
) -> Optional[str]:
    """Formats the system prompt by appending the list of activated tools.

    High level role: Appends activated tools list to the system prompt if tools are present.
    Description: Inspects the system prompt and tools list, extracts the tool names,
    and appends a formatted tools line to the end of the system prompt.
    How it works:
    - If system_prompt is None or empty, returns system_prompt.
    - If tools is None or empty, returns system_prompt.
    - Extracts tool names and joins them with commas.
    - Returns the system prompt with the appended tools line.

    Args:
        system_prompt (Optional[str]): The original system prompt.
        tools (Optional[List[Dict[str, Any]]]): List of tools to register.

    Returns:
        Optional[str]: Formatted system prompt with tools appended.

    Raises:
        None

    Examples:
        >>> format_system_prompt_with_tools(
        ...     "Be helpful",
        ...     [{"type": "function", "function": {"name": "fetch_url"}}]
        ... )
        'Be helpful\\n-tools: fetch_url'
    """
    if not system_prompt or not tools:
        return system_prompt
    tool_names = [
        t["function"]["name"] for t in tools if "function" in t and "name" in t["function"]
    ]
    if not tool_names:
        return system_prompt
    return f"{system_prompt}\n-tools: {', '.join(tool_names)}"


def build_ollama_payload(request: ChatRequest, stream: bool = False) -> Dict[str, Any]:
    """
    Constructs a dictionary payload formatted for the Ollama API from a ChatRequest object.

    High level role: Centralized transformer that converts internal Pydantic request models
    into the specific JSON structure expected by the Ollama /api/chat endpoint.
    It handles the injection of the system prompt as the first message, ensures message models are
    serialized to dictionaries, and allows for overriding the streaming behavior (useful for
    multi-step tool detection loops).

    Args:
        request (ChatRequest): The internal Pydantic model containing user input, model choice,
            and optional configurations.
        stream (bool, optional): Whether the final payload should request a streaming response
            from Ollama. Defaults to False.

    Returns:
        Dict[str, Any]: A dictionary ready to be passed to httpx as a JSON payload.
            Includes 'model', 'messages', 'stream', and optionally 'options' and 'tools'.

    Errors:
        AttributeError: If the request object is missing required fields like 'model' or 'messages'.

    Example:
        >>> req = ChatRequest(model="gemma", messages=[{"role": "user", "content": "hi"}])
        >>> payload = build_ollama_payload(req, stream=True)
        >>> print(payload['stream'])
        True
    """
    payload: Dict[str, Any] = {
        "model": request.model,
        "messages": [msg.model_dump(exclude_none=True) for msg in request.messages],
        "stream": stream,
    }

    # Inject system prompt at the very beginning of the message history if provided
    if request.system:
        sys_content = format_system_prompt_with_tools(request.system, request.tools)
        payload["messages"].insert(0, {"role": "system", "content": sys_content})

    if request.options:
        payload["options"] = request.options

    if request.tools:
        payload["tools"] = request.tools

    return payload
