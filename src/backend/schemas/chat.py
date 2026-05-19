"""
Pydantic Request/Response Schema Definitions.

High level role: Validates inputs and outputs for Chat operations.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    """
    Represents a single message in a chat conversation.

    High level role: Validates individual message objects to ensure they
    have the required role and content fields.
    """
    role: str
    content: str


class ChatRequest(BaseModel):
    """
    Represents an incoming chat completion request from the frontend.

    High level role: Validates the payload sent to the /chat endpoint,
    ensuring it contains a model and a list of messages. It also provides
    optional fields for advanced Ollama features like tools and system prompts.
    """
    model: str
    messages: List[ChatMessage]
    system: Optional[str] = None
    stream: bool = False
    options: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None
