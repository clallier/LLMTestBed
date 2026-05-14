import httpx
from typing import List, Dict, Any, AsyncGenerator
from streamlit_app.config import BACKEND_URL

def fetch_models() -> List[Dict[str, Any]]:
    """
    Fetches the list of available models from the backend.
    
    Returns:
        List[Dict[str, Any]]: A list of model objects. Returns an empty list on failure.
    """
    try:
        resp = httpx.get(f"{BACKEND_URL}/models", timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching models: {e}")
        return []

def fetch_tools() -> List[Dict[str, Any]]:
    """
    Fetches the available tools registry from the backend.
    
    Returns:
        List[Dict[str, Any]]: A list of tool schemas. Returns an empty list on failure.
    """
    try:
        resp = httpx.get(f"{BACKEND_URL}/tools", timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching tools: {e}")
        return []

async def send_chat_message(payload: Dict[str, Any]) -> AsyncGenerator[httpx.Response, None]:
    """
    Sends a chat message payload to the backend and yields the streaming response.
    
    Args:
        payload (Dict[str, Any]): The chat request payload.
        
    Yields:
        httpx.Response: The HTTPX streaming response context manager.
    """
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{BACKEND_URL}/chat", json=payload) as r:
            yield r
