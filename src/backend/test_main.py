import pytest
from fastapi.testclient import TestClient
from main import app
import httpx
import respx

client = TestClient(app)

@pytest.mark.asyncio
@respx.mock
async def test_health_check_ollama_connected():
    # Mock Ollama /api/tags
    respx.get("http://127.0.0.1:11434/api/tags").mock(return_value=httpx.Response(200, json={"models": []}))
    
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ollama"] == "connected"

@pytest.mark.asyncio
@respx.mock
async def test_list_models():
    # Mock Ollama /api/tags
    mock_models = {"models": [{"name": "llama3:latest"}, {"name": "mistral"}]}
    respx.get("http://127.0.0.1:11434/api/tags").mock(return_value=httpx.Response(200, json=mock_models))
    
    response = client.get("/models")
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["name"] == "llama3:latest"

@pytest.mark.asyncio
@respx.mock
async def test_chat_proxy():
    # Mock Ollama /api/chat
    mock_response = {"message": {"role": "assistant", "content": "Hello!"}}
    respx.post("http://127.0.0.1:11434/api/chat").mock(return_value=httpx.Response(200, json=mock_response))
    
    payload = {
        "model": "llama3",
        "messages": [{"role": "user", "content": "Hi"}],
        "system": "You are a bot"
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    assert response.json()["message"]["content"] == "Hello!"

@pytest.mark.asyncio
@respx.mock
async def test_chat_stream():
    # Mock Ollama /api/chat streaming response
    mock_lines = [
        '{"message": {"role": "assistant", "content": "Part 1"}, "done": false}\n',
        '{"message": {"role": "assistant", "content": " Part 2"}, "done": true}\n'
    ]
    respx.post("http://127.0.0.1:11434/api/chat").mock(return_value=httpx.Response(200, content="".join(mock_lines)))
    
    payload = {
        "model": "llama3",
        "messages": [{"role": "user", "content": "Hi"}],
        "stream": True
    }
    
    # In TestClient, we can iterate over the response or just check the text
    response = client.post("/chat", json=payload)
    assert response.status_code == 200
    content = response.text
    assert "Part 1" in content
    assert "Part 2" in content

@pytest.mark.asyncio
@respx.mock
async def test_list_tools():
    response = client.get("/tools")
    assert response.status_code == 200
    assert len(response.json()) >= 3
    assert response.json()[0]["function"]["name"] == "read_sensitive_file"
