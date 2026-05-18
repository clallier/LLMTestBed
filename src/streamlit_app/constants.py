"""
Constants for the Streamlit frontend application component system.

High level role: Encapsulates all public/shared styling, role markers, and configurations.
"""

import os
from typing import Any

# UI Styling & Role Markers
AVATAR_TOOLS: str = "⚙️"
ROLE_TOOLS: str = "tools"
ROLE_USER: str = "user"
ROLE_ASSISTANT: str = "assistant"

def get_backend_url() -> str:
    """
    Returns the backend API server URL dynamically from environment variables.

    High level role: Resolves target server locations at execution time to support dynamic mocking.

    Arguments:
        None

    Returns:
        str: Fully qualified HTTP URL of the backend server.
    """
    return os.getenv("BACKEND_URL", "http://localhost:8000")

def __getattr__(name: str) -> Any:
    """
    Dynamically resolves module-level attributes to avoid import-time state caching.

    High level role: Intercepts BACKEND_URL reads and routes them dynamically.

    Arguments:
        name (str): Attribute name being queried.

    Returns:
        Any: Attribute value.

    Raises:
        AttributeError: If attribute is not recognized.
    """
    if name == "BACKEND_URL":
        return get_backend_url()
    raise AttributeError(f"module {__name__} has no attribute {name}")
