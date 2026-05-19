"""
API Client for communicating with the backend completions server.

High level role: Provides clean async/sync HTTP client fetchers for models, tools, and streams.
"""

from typing import Any, AsyncGenerator, Dict, List

import httpx

from streamlit_app.constants import get_backend_url


def __getattr__(name: str) -> Any:
    """Dynamically resolves BACKEND_URL to support legacy test assertions without import caching."""
    if name == "BACKEND_URL":
        return get_backend_url()
    raise AttributeError(f"module {__name__} has no attribute {name}")


def fetch_models() -> List[Dict[str, Any]]:
    """
    Fetches the list of available models from the backend.

    High level role: Queries backend server models endpoint.

    Returns:
        List[Dict[str, Any]]: A list of model objects. Returns an empty list on failure.
    """
    try:
        resp = httpx.get(f"{get_backend_url()}/models", timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        print(f"Error fetching models: {e}")
        return []


def fetch_tools() -> List[Dict[str, Any]]:
    """
    Fetches the available tools registry from the backend.

    High level role: Queries backend server tools registry schema.

    Returns:
        List[Dict[str, Any]]: A list of tool schemas. Returns an empty list on failure.
    """
    try:
        resp = httpx.get(f"{get_backend_url()}/tools", timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        print(f"Error fetching tools: {e}")
        return []


async def send_chat_message(payload: Dict[str, Any]) -> AsyncGenerator[httpx.Response, None]:
    """
    Sends a chat message payload to the backend and yields the streaming response.

    High level role: Streams request payload to the backend chat API.

    Args:
        payload (Dict[str, Any]): The chat request payload.

    Yields:
        httpx.Response: The HTTPX streaming response context manager.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{get_backend_url()}/chat", json=payload) as r:
            yield r
