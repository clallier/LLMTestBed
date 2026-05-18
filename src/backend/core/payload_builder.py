from typing import Any, Dict

from backend.schemas.chat import ChatRequest


def build_ollama_payload(request: ChatRequest, stream: bool = False) -> Dict[str, Any]:
    """
    Constructs a dictionary payload formatted for the Ollama API from a ChatRequest object.

    High level role: This function serves as a centralized transformer that converts our internal 
    Pydantic request models into the specific JSON structure expected by the Ollama /api/chat endpoint. 
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
        "messages": [msg.model_dump() for msg in request.messages],
        "stream": stream
    }
    
    # Inject system prompt at the very beginning of the message history if provided
    if request.system:
        payload["messages"].insert(0, {"role": "system", "content": request.system})
        
    if request.options:
        payload["options"] = request.options
        
    if request.tools:
        payload["tools"] = request.tools
        
    return payload
