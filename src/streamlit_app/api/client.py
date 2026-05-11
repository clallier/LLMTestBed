import httpx
import json

BACKEND_URL = "http://localhost:8000"

def fetch_models():
    try:
        resp = httpx.get(f"{BACKEND_URL}/models")
        return resp.json()
    except Exception as e:
        return []

def fetch_tools():
    try:
        resp = httpx.get(f"{BACKEND_URL}/tools")
        return resp.json()
    except Exception as e:
        return []

async def send_chat_message(payload):
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", f"{BACKEND_URL}/chat", json=payload) as r:
            yield r
