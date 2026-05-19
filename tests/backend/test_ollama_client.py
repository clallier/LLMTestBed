import pytest
import respx
from httpx import Response

from backend.core.ollama_client import ollama_client


@pytest.mark.asyncio
async def test_list_models_success():
    with respx.mock:
        respx.get("http://127.0.0.1:11434/api/tags").mock(
            return_value=Response(200, json={"models": [{"name": "gemma"}]})
        )
        models = await ollama_client.list_models()
        assert len(models) == 1
        assert models[0]["name"] == "gemma"


@pytest.mark.asyncio
async def test_chat_success():
    with respx.mock:
        respx.post("http://127.0.0.1:11434/api/chat").mock(
            return_value=Response(200, json={"message": {"role": "assistant", "content": "Hello"}})
        )
        response = await ollama_client.chat({"model": "gemma"})
        assert response["message"]["content"] == "Hello"


@pytest.mark.asyncio
async def test_chat_stream_error():
    with respx.mock:
        respx.post("http://127.0.0.1:11434/api/chat").mock(side_effect=Exception("Network error"))

        chunks = []
        async for chunk in ollama_client.chat_stream({"model": "gemma"}):
            chunks.append(chunk)

        assert len(chunks) == 1
        assert "Network error" in chunks[0]
