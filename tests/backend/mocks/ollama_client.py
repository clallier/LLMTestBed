from typing import Any, AsyncGenerator, Dict, List

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
