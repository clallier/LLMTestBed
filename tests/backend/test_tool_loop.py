import pytest
import respx
import json
from httpx import AsyncClient, Response, ASGITransport
from backend.main import app

@pytest.mark.asyncio
async def test_recursive_tool_call_history_integrity():
    """
    Verifies that when a tool is called, the assistant's intent (tool_calls)
    is correctly preserved in the history for the subsequent recursive call.
    """
    # 1. Define the sequence of responses from Ollama
    # Turn 1: Model requests a tool call
    chunk_1 = json.dumps({
        "message": {
            "role": "assistant",
            "tool_calls": [{
                "function": {
                    "name": "read_sensitive_file",
                    "arguments": {"filename": "config.json"}
                }
            }]
        }
    }) + "\n"
    
    # Turn 2: Model gives final response after seeing tool result
    chunk_2 = json.dumps({
        "message": {
            "role": "assistant",
            "content": "I have read the config."
        }
    }) + "\n"

    with respx.mock:
        # Mock the two consecutive calls to Ollama
        route = respx.post("http://127.0.0.1:11434/api/chat")
        route.side_effect = [
            Response(200, content=chunk_1),
            Response(200, content=chunk_2)
        ]
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/chat", json={
                "model": "gemma",
                "messages": [{"role": "user", "content": "Read the config"}],
                "stream": True,
                "tools": [{"type": "function", "function": {"name": "read_sensitive_file"}}]
            })
            
        assert response.status_code == 200
        
        # Collect stream content to ensure it finished
        lines = [line async for line in response.aiter_lines() if line]
        assert len(lines) >= 2 # Should have tool call chunk and content chunk
        
        # 2. VERIFY THE HISTORY SENT IN THE SECOND CALL
        # The second request to Ollama should contain the tool_calls in the history
        second_request = route.calls[1].request
        second_payload = json.loads(second_request.content)
        
        # messages should be: [user, assistant (with tool_calls), tool (result)]
        messages = second_payload["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        
        # This is what we fixed!
        assert messages[1]["role"] == "assistant"
        assert "tool_calls" in messages[1]
        assert messages[1]["tool_calls"][0]["function"]["name"] == "read_sensitive_file"
        
        assert messages[2]["role"] == "tool"
        assert "SECRET" in messages[2]["content"] # Result of the mock tool
