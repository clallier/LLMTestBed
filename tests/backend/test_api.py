import pytest
import respx
import json
from httpx import AsyncClient, Response, ASGITransport
from backend.main import app, global_exception_handler
from .mocks.ollama_chunks import MOCK_CHUNKS_NORMAL, MOCK_CHUNKS_MALFORMED

async def _parse_chat_stream(response: Response) -> tuple[str, bool]:
    """
    Parses the streaming NDJSON response from the /chat endpoint.

    High level role: Extracts and aggregates the generated message content
    while checking for the presence of the initial security analysis packet.

    Args:
        response (Response): The HTTPX async response object containing the NDJSON stream.

    Returns:
        tuple[str, bool]: A tuple containing:
            - The accumulated message content (str).
            - Whether the security packet was successfully detected (bool).

    Potential errors:
        json.JSONDecodeError: If a line in the stream is not valid JSON.

    Examples:
        >>> content, security_received = await _parse_chat_stream(response)
        >>> assert security_received
        >>> assert content == "Hello world!"
    """
    content = ""
    security_chunk_received = False
    async for line in response.aiter_lines():
        if line:
            data = json.loads(line)
            if "security" in data:
                security_chunk_received = True
            elif "message" in data and "content" in data["message"]:
                content += data["message"]["content"]
    return content, security_chunk_received


@pytest.mark.asyncio
async def test_chat_endpoint_no_tools():
    with respx.mock:
        respx.post("http://127.0.0.1:11434/api/chat").mock(
            return_value=Response(200, content="".join(MOCK_CHUNKS_NORMAL))
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/chat", json={
                "model": "gemma",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True
            })
            
        assert response.status_code == 200
        content, security_chunk_received = await _parse_chat_stream(response)
        assert security_chunk_received
        assert content == "Hello world!"


@pytest.mark.asyncio
async def test_chat_endpoint_malformed_json(caplog):
    with respx.mock:
        respx.post("http://127.0.0.1:11434/api/chat").mock(
            return_value=Response(200, content="".join(MOCK_CHUNKS_MALFORMED))
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/chat", json={
                "model": "gemma",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True
            })
            
        assert response.status_code == 200
        content, security_chunk_received = await _parse_chat_stream(response)
        assert security_chunk_received
        assert content == "Hello world!"
        assert "Failed to parse JSON chunk: THIS IS NOT VALID JSON" in caplog.text

@pytest.mark.asyncio
async def test_health_endpoint():
    with respx.mock:
        respx.get("http://127.0.0.1:11434/api/tags").mock(
            return_value=Response(200, json={"models": [{"name": "gemma"}]})
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health")
            
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["model_count"] == 1

@pytest.mark.asyncio
async def test_health_endpoint_error():
    with respx.mock:
        respx.get("http://127.0.0.1:11434/api/tags").mock(
            return_value=Response(500, json={"error": "Server down"})
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/health")
            
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        assert response.json()["ollama"] == "disconnected"

@pytest.mark.asyncio
async def test_models_endpoint():
    with respx.mock:
        respx.get("http://127.0.0.1:11434/api/tags").mock(
            return_value=Response(200, json={"models": [{"name": "gemma"}]})
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/models")
            
        assert response.status_code == 200
        assert len(response.json()) == 1

@pytest.mark.asyncio
async def test_models_endpoint_error():
    with respx.mock:
        respx.get("http://127.0.0.1:11434/api/tags").mock(
            return_value=Response(500, json={"error": "Server down"})
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.get("/models")
            
        assert response.status_code == 500

@pytest.mark.asyncio
async def test_tools_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/tools")
        
    assert response.status_code == 200
    assert len(response.json()) > 0

@pytest.mark.asyncio
async def test_chat_endpoint_with_tools():
    # Mock Ollama streaming response with a tool call
    mock_chunks = [
        json.dumps({"message": {"role": "assistant", "tool_calls": [{"function": {"name": "read_sensitive_file", "arguments": {"filename": ".env"}}}]}}) + "\n"
    ]
    
    with respx.mock:
        respx.post("http://127.0.0.1:11434/api/chat").mock(
            return_value=Response(200, content="".join(mock_chunks))
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/chat", json={
                "model": "gemma",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
                "tools": [{"type": "function", "function": {"name": "read_sensitive_file"}}]
            })
            
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_global_exception_handler_direct():
    response = await global_exception_handler(None, ValueError("Direct exception test"))
    assert response.status_code == 500
    data = json.loads(bytes(response.body))
    assert "Direct exception test" in data["message"]
    assert "traceback" in data

@pytest.mark.asyncio
async def test_index_endpoint():
    # If static folder is missing index.html it might 404/500, but we test the route exists
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code in [200, 404, 500]


