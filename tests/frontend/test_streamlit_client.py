import pytest
import respx
from httpx import Response

import streamlit_app.api.client as client
from streamlit_app.api.client import fetch_models, fetch_tools, send_chat_message


def test_fetch_models_success():
    with respx.mock:
        respx.get(f"{client.BACKEND_URL}/models").mock(
            return_value=Response(200, json=[{"name": "gemma"}])
        )
        models = fetch_models()
        assert len(models) == 1
        assert models[0]["name"] == "gemma"


def test_fetch_models_error():
    import httpx
    with respx.mock:
        respx.get(f"{client.BACKEND_URL}/models").mock(
            side_effect=httpx.HTTPError("Connection refused")
        )
        models = fetch_models()
        assert models == []


def test_fetch_tools_success():
    with respx.mock:
        respx.get(f"{client.BACKEND_URL}/tools").mock(
            return_value=Response(200, json={"mock_tool": {}})
        )
        tools = fetch_tools()
        assert "mock_tool" in tools


def test_fetch_tools_error():
    import httpx
    with respx.mock:
        respx.get(f"{client.BACKEND_URL}/tools").mock(
            side_effect=httpx.HTTPError("Connection refused")
        )
        tools = fetch_tools()
        assert tools == []


@pytest.mark.asyncio
async def test_send_chat_message():
    with respx.mock:
        respx.post(f"{client.BACKEND_URL}/chat").mock(return_value=Response(200, content="chunk1"))
        payload = {"model": "gemma"}

        chunks = []
        async for response in send_chat_message(payload):
            async for chunk in response.aiter_text():
                chunks.append(chunk)

        assert len(chunks) == 1
        assert chunks[0] == "chunk1"
