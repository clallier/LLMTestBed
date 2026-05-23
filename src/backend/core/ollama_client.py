"""
Ollama HTTP Client API Wrapper.

High level role: Handles REST API calls and chunked NDJSON stream parsing for Ollama.
"""
import asyncio
import json
import logging
import os

import httpx

from backend.core.config import OLLAMA_BASE_URL

logger = logging.getLogger(__name__)


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
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error in chat_stream: %s", e)
            yield f'{{"error": "{str(e)}"}}'

    def _load_test_chunks(self) -> tuple[list, list]:
        """Loads choreographed sequence of mock chunks from disk.

        High level role: Reads E2E test data assets dynamically from the tests directory.
        Description: Resolves the local absolute path of the mock JSON file relative to
        the codebase files and parses the first/second turn datasets.

        Returns:
            tuple[list, list]: Tuple containing first-turn and second-turn mock chunk lists.
        """
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.abspath(
            os.path.join(curr_dir, "..", "..", "..", "tests", "backend", "mocks", "ollama_client_data.json")
        )
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["TEST_CHUNKS_FIRST_TURN"], data["TEST_CHUNKS_SECOND_TURN"]

    async def _get_test_chunks(self, payload: dict):
        """Yields a choreographed sequence of chunks for E2E testing.

        High level role: Handles asynchronous streaming of mock E2E data chunks.
        Description: Determines current session progress to select the appropriate dataset
        and streams them with micro-delays.

        Args:
            payload (dict): Stream API request payload containing the conversation history.

        Yields:
            str: Trailing-newline terminated NDJSON data stream chunks.
        """
        has_tool = any(m.get("role") == "tool" for m in payload.get("messages", []))
        first_turn, second_turn = self._load_test_chunks()
        chunks = second_turn if has_tool else first_turn
        for chunk in chunks:
            await asyncio.sleep(0.1)
            yield json.dumps(chunk) + "\n"


ollama_client = OllamaClient()
