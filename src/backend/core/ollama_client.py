import httpx
from core.config import OLLAMA_BASE_URL

class OllamaClient:
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL

    async def list_models(self):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])

    async def chat(self, payload: dict):
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def chat_stream(self, payload: dict):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            yield line + "\n"
        except Exception as e:
            print(f"Error in chat_stream: {e}")
            yield f'{{"error": "{str(e)}"}}'

ollama_client = OllamaClient()
