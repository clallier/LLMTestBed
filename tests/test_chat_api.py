import pytest
import httpx
from httpx import AsyncClient, ASGITransport
import respx
from src.backend.main import app
import json
import re

# Mock URL that matches both localhost and 127.0.0.1
MOCK_OLLAMA_URL = re.compile(r"http://(localhost|127\.0\.0\.1):11434/api/chat")

@pytest.mark.asyncio
async def test_chat_direct_response():
    """Test a simple direct response without tool calls."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with respx.mock:
            respx.post(MOCK_OLLAMA_URL).mock(return_value=httpx.Response(200, json={
                "message": {"role": "assistant", "content": "Hello, I am a test AI."}
            }))
            
            response = await ac.post("/chat", json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": False
            })
            
        if response.status_code != 200:
            print(f"Error Response: {response.text}")
            
        assert response.status_code == 200
        assert response.json()["message"]["content"] == "Hello, I am a test AI."

@pytest.mark.asyncio
async def test_chat_tool_call_loop():
    """Test the two-pass loop when a tool is called."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with respx.mock:
            route1 = respx.post(MOCK_OLLAMA_URL).mock()
            route1.side_effect = [
                httpx.Response(200, json={
                    "message": {
                        "role": "assistant", 
                        "content": "",
                        "tool_calls": [{"function": {"name": "get_current_time", "arguments": {}}}]
                    }
                }),
                httpx.Response(200, json={
                    "message": {"role": "assistant", "content": "The current time is 12:00."}
                })
            ]
            
            response = await ac.post("/chat", json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "What time is it?"}],
                "stream": False,
                "tools": [{"function": {"name": "get_current_time"}}]
            })
            
        if response.status_code != 200:
            print(f"Error Response: {response.text}")
            
        assert response.status_code == 200
        assert "12:00" in response.json()["message"]["content"]

@pytest.mark.asyncio
async def test_chat_streaming():
    """Test that streaming responses are correctly emitted."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        with respx.mock:
            # The backend makes TWO calls to Ollama for a streaming request:
            # 1. Non-streaming call to check for tools
            # 2. Streaming call to get the content
            route = respx.post(MOCK_OLLAMA_URL).mock()
            
            streaming_content = [
                json.dumps({"message": {"content": "Hello"}}),
                json.dumps({"message": {"content": " world"}}),
                json.dumps({"done": True})
            ]
            
            route.side_effect = [
                # Pass 1: No tools found
                httpx.Response(200, json={"message": {"role": "assistant", "content": "Pre-check"}}),
                # Pass 2: The actual stream
                httpx.Response(200, content="\n".join(streaming_content))
            ]
            
            response = await ac.post("/chat", json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "Hi"}],
                "stream": True
            })
            
        if response.status_code != 200:
            print(f"Error Response: {response.text}")
            
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"
        
        chunks = []
        async for line in response.aiter_lines():
            if line:
                chunks.append(json.loads(line))
        
        # We expect 3 chunks from our mock
        assert len(chunks) == 3
        assert chunks[0]["message"]["content"] == "Hello"
