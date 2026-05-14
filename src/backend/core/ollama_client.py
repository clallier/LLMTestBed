import httpx
import os
import json
import asyncio
from backend.core.config import OLLAMA_BASE_URL

class OllamaClient:
    """
    Client wrapper for interacting with the local Ollama API.

    High level role: Encapsulates all direct HTTP communication with the 
    Ollama server. Provides asynchronous methods to list models, execute 
    standard chat completions, and handle streaming chat completions.
    """
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL  
        self.test_mode = os.getenv("E2E_TEST_MODE") == "true"

    async def list_models(self) -> list:
        """
        Retrieves the list of available models from the Ollama instance.

        Returns:
            list: A list of dictionary objects representing the models.
                Returns an empty list if no models are found.
        
        Raises:
            httpx.HTTPError: If the request to the Ollama API fails.
        """
        if self.test_mode:
            return [{"name": "e2e-mock-model"}]

        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return response.json().get("models", [])

    async def chat(self, payload: dict) -> dict:
        """
        Executes a standard, non-streaming chat completion request.

        Args:
            payload (dict): The complete JSON payload formatted for the 
                Ollama /api/chat endpoint.

        Returns:
            dict: The full JSON response from the Ollama API.
            
        Raises:
            httpx.HTTPError: If the request to the Ollama API fails.
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def chat_stream(self, payload: dict):
        """
        Executes a streaming chat completion request.

        Args:
            payload (dict): The complete JSON payload formatted for the 
                Ollama /api/chat endpoint.

        Yields:
            str: Each chunk of the NDJSON response as a string with a 
                trailing newline.

        Yields (on error):
            str: A JSON string containing an error message if the stream fails.
        """
        if self.test_mode:
            async for chunk in self._get_test_chunks(payload):
                yield chunk
            return

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

    async def _get_test_chunks(self, payload: dict):
        """Yields a choreographed sequence of chunks for E2E testing."""
        # Check if we are in the second step of a tool call loop
        has_tool_results = any(m.get("role") == "tool" for m in payload.get("messages", []))

        if not has_tool_results:
            # First turn: give reasoning and tool calls
            chunks = [
                {"message": {"role": "assistant", "thinking": "Starting test reasoning..."}},
                {"message": {"role": "assistant", "tool_calls": [
                    {"function": {"name": "read_sensitive_file", "arguments": "{\"filename\": \".env\"}"}},
                    {"function": {"name": "execute_command", "arguments": "{\"command\": \"ls\"}"}}
                ]}},
                {"done": False}
            ]
        else:
            # Second turn: give the final result
            chunks = [
                {"message": {"role": "assistant", "content": "Here is the result of the test after tool execution."}},
                {"done": True}
            ]

        for chunk in chunks:
            await asyncio.sleep(0.1)
            yield json.dumps(chunk) + "\n"

ollama_client = OllamaClient()
