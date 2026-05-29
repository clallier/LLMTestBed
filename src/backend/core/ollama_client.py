"""
Ollama HTTP Client API Wrapper.

High level role: Handles REST API calls and chunked NDJSON stream parsing for Ollama.
"""

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
        """Initializes the production client with the configured base URL."""
        self.base_url = OLLAMA_BASE_URL

    async def list_models(self) -> list:
        """
        Retrieves the list of available models from the Ollama instance.

        Returns:
            list: A list of dictionary objects representing the models.
                Returns an empty list if no models are found.

        Raises:
            httpx.HTTPError: If the request to the Ollama API fails.
        """
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
            if response.status_code >= 400:
                error_msg = await self._handle_status_error(response)
                raise httpx.HTTPStatusError(
                    f"Ollama API Error ({response.status_code}): {error_msg}",
                    request=response.request,
                    response=response,
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
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        error_msg = await self._handle_status_error(response)
                        yield f'{{"error": "Ollama API Error ({response.status_code}): {error_msg}"}}\n'
                        return
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            yield line + "\n"
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Error in chat_stream: %s", e)
            yield f'{{"error": "{str(e)}"}}'

    async def web_search(self, query: str, max_results: int = 5) -> dict:
        """Performs a web search via the Ollama Search API.

        Args:
            query (str): The search query string.
            max_results (int): Maximum results to return. Defaults to 5.

        Returns:
            dict: Search results dictionary.
        """
        headers = {}
        if api_key := os.getenv("OLLAMA_API_KEY"):
            headers["Authorization"] = f"Bearer {api_key}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://ollama.com/api/web_search",
                headers=headers,
                json={"query": query, "max_results": max_results},
            )
            response.raise_for_status()
            return response.json()

    # ==========================================
    # Private Internal Helpers
    # ==========================================

    async def _handle_status_error(self, response: httpx.Response) -> str:
        """Handles HTTP response errors by logging and formatting the error body.

        High level role: Logs and parses error payloads from HTTP failures.

        Args:
            response (httpx.Response): The failed HTTP response object.

        Returns:
            str: Decoded string error message from the response body.
        """
        body = await response.aread()
        decoded_body = body.decode(errors="replace")
        logger.error("Ollama API Error (%d): %s", response.status_code, decoded_body)
        return decoded_body


# Factory pattern / IoC instantiation to load mock E2E client during testing
if os.getenv("E2E_TEST_MODE") == "true":
    # pylint: disable=import-error
    from tests.backend.mocks.ollama_client import E2ETestOllamaClient
    # pylint: enable=import-error

    ollama_client = E2ETestOllamaClient()
else:
    ollama_client = OllamaClient()
