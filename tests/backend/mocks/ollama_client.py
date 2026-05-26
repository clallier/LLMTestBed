import asyncio
import json
import os
from typing import Any, AsyncGenerator, Dict, List, Tuple

from backend.core.ollama_client import OllamaClient


class MockOllamaClient(OllamaClient):
    """
    Mock Ollama client for testing components without live Ollama instances.

    High level role: Simulates the async chat stream API of Ollama Client.
    It inherits from OllamaClient to be fully compatible with static type checkers.
    """

    def __init__(self, chunks: List[str]):
        """
        Initializes the MockOllamaClient with canned stream chunks.

        Args:
            chunks (List[str]): List of canned response string chunks.
        """
        super().__init__()
        self.chunks = chunks

    async def chat_stream(self, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Yields mock stream chunks as an async generator.

        Args:
            payload (Dict[str, Any]): Ollama request payload.

        Yields:
            str: Canned string chunk.
        """
        for chunk in self.chunks:
            yield chunk


class E2ETestOllamaClient(OllamaClient):
    """
    Subclass of OllamaClient used exclusively during E2E_TEST_MODE.

    High level role: Streams choreographed sequence of mock chunks from disk for E2E tests.
    Description: Simulates a live Ollama connection by reading pre-recorded test turns
    from a local JSON data asset.
    """

    def __init__(self):
        """Initializes the E2E test mock client."""
        super().__init__()

    async def list_models(self) -> list:
        """Mock implementation of list_models that returns a dummy E2E test model."""
        return [{"name": "e2e-mock-model"}]

    def _load_test_chunks(self) -> Tuple[List[Any], List[Any]]:
        """Loads choreographed sequence of mock chunks from disk.

        Returns:
            Tuple[List[Any], List[Any]]: First-turn and second-turn mock chunk lists.
        """
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(curr_dir, "ollama_client_data.json")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["TEST_CHUNKS_FIRST_TURN"], data["TEST_CHUNKS_SECOND_TURN"]

    async def _get_test_chunks(self, payload: dict) -> AsyncGenerator[str, None]:
        """Yields a choreographed sequence of chunks for E2E testing.

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

    async def chat_stream(self, payload: dict) -> AsyncGenerator[str, None]:
        """Yields mock streaming completions for E2E tests.

        Args:
            payload (dict): Request payload dictionary.

        Yields:
            str: Trailing-newline terminated JSON chunk strings.
        """
        async for chunk in self._get_test_chunks(payload):
            yield chunk

    async def web_search(self, query: str, max_results: int = 5) -> dict:
        """Mock E2E implementation of web_search."""
        return {
            "results": [
                {
                    "title": "Mock Search Result",
                    "url": "https://mocksite.org/result",
                    "content": f"This is mock content for search query: {query}",
                }
            ]
        }

    async def web_fetch(self, url: str) -> dict:
        """Mock E2E implementation of web_fetch."""
        return {
            "title": "Mock Fetched Page",
            "content": f"This is mock content fetched from URL: {url}",
            "links": ["https://mocksite.org/link1", "https://mocksite.org/link2"],
        }
