"""Multi-turn Agent Loop Stream Processor.

High level role: Orchestrates Ollama streaming sessions, security pipelines,
and recursive tool delegation. Tool execution is fully delegated to ToolExecutor.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.core.ollama_client import OllamaClient, ollama_client
from backend.core.payload_builder import build_ollama_payload
from backend.core.stream_sanitizer import clean_chunks_stream, parse_chunk
from backend.core.tool_executor import ToolExecutor
from backend.schemas.chat import ChatRequest
from backend.security.preprocessor import SecurityPreprocessor

logger = logging.getLogger(__name__)


class AgentStreamProcessor:
    """Manages the multi-turn agent loop and streaming responses.

    High level role: Thin orchestration layer coordinating the Ollama streaming
    client, security risk assessment for user prompts, and recursive tool loops.
    All tool dispatching and tool telemetry are delegated to ToolExecutor, keeping
    this class focused solely on the agent conversation lifecycle.
    """

    def __init__(
        self,
        client: OllamaClient = ollama_client,
        security_engine: Optional[SecurityPreprocessor] = None,
        tool_executor: Optional[ToolExecutor] = None,
    ):
        """Initializes the AgentStreamProcessor with optional dependency injection.

        Args:
            client (OllamaClient): Client to communicate with Ollama.
                Defaults to the global ollama_client singleton.
            security_engine (Optional[SecurityPreprocessor]): Safety preprocessor
                for user prompt risk assessment. Defaults to a new instance.
            tool_executor (Optional[ToolExecutor]): Tool dispatcher instance.
                Defaults to a ToolExecutor sharing the same security_engine.
        """
        self._client = client
        self._security_engine = security_engine or SecurityPreprocessor()
        self._tool_executor = tool_executor or ToolExecutor(self._security_engine)

    # ==========================================
    # Public API
    # ==========================================

    async def process_stream(
        self,
        request: ChatRequest,
        messages: List[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """Primary entry point of the pipeline: checks prompt risk and starts the stream.

        High level role: Coordinates input security preprocessing and Ollama chunk generation.
        Description: Assesses the risk score of the last user prompt, yields the security
        assessment, and streams the model's reply including recursive tool executions.
        How it works:
        - Extracts the last user prompt from conversation history.
        - Emits a security risk payload for the user prompt.
        - Delegates to handle_model_stream for all subsequent streaming.

        Args:
            request (ChatRequest): The incoming request payload.
            messages (List[Dict[str, Any]]): The active conversation messages history.

        Yields:
            str: NDJSON line chunks — security assessment followed by assistant response.

        Raises:
            Exception: Propagates internal client or preprocessor execution failures.

        Examples:
            >>> processor = AgentStreamProcessor()
            >>> async for chunk in processor.process_stream(req, msgs):
            ...     print(chunk)
        """
        last_prompt = messages[-1]["content"] if messages else ""
        yield self._create_security_payload("user_prompt", last_prompt)

        async for chunk in self.handle_model_stream(request, messages):
            yield chunk

    async def handle_model_stream(
        self,
        request: ChatRequest,
        messages: List[Dict[str, Any]],
        depth: int = 0,
    ) -> AsyncGenerator[str, None]:
        """Manages the recursive agent loop, streaming cleaned chunks and delegating tools.

        High level role: Coordinates multi-turn model interactions and tool delegation.
        Description: Prepares payload history, runs the stream through the sanitizer,
        and recursively delegates to ToolExecutor when tool calls are detected.
        How it works:
        - Builds Ollama request payload including system settings and messages.
        - Pipes the raw streaming response into the clean_chunks_stream filter.
        - Delegates tool execution to ToolExecutor, or triggers recursion limit handling.

        Args:
            request (ChatRequest): Incoming chat request parameters.
            messages (List[Dict[str, Any]]): Active conversation history.
            depth (int): Current recursion depth of the tool loop. Starts at 0.

        Yields:
            str: Cleaned NDJSON line stream chunks.

        Raises:
            None

        Examples:
            >>> processor = AgentStreamProcessor()
            >>> async for chunk in processor.handle_model_stream(req, msgs):
            ...     print(chunk)
        """
        payload = build_ollama_payload(request, stream=True)
        payload["messages"] = messages
        tool_calls: List[Dict[str, Any]] = []
        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": ""}

        raw_stream = self._raw_model_stream(payload, assistant_msg, tool_calls)
        async for chunk in clean_chunks_stream(raw_stream, assistant_msg):
            yield chunk

        if tool_calls:
            if depth >= 5:
                logger.warning("Max tool recursion depth reached: %d", depth)
                async for chunk in self._tool_executor.handle_recursion_limit(
                    messages, assistant_msg, tool_calls
                ):
                    yield chunk
                return
            async for chunk in self._recurse_tools(
                request, messages, assistant_msg, tool_calls, depth + 1
            ):
                yield chunk

    # ==========================================
    # Private Internal Helpers
    # ==========================================

    async def _raw_model_stream(
        self,
        payload: Dict[str, Any],
        assistant_msg: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """Generates raw NDJSON stream chunks from the Ollama client connection.

        High level role: Connects directly to the streaming client.
        Description: Streams client completions chunk by chunk, parsing each line
        and routing security events and message content to the appropriate handler.
        How it works: Iterates through client stream, parses NDJSON, and delegates
        to _process_message_chunk to accumulate text and tool call structures.

        Args:
            payload (Dict[str, Any]): The Ollama payload configuration.
            assistant_msg (Dict[str, Any]): Mutable dict tracking accumulated assistant text.
            tool_calls (List[Dict[str, Any]]): Mutable list accumulating detected tool calls.

        Yields:
            str: Raw NDJSON line stream chunks.

        Raises:
            None

        Examples:
            >>> processor = AgentStreamProcessor()
            >>> async for chunk in processor._raw_model_stream(pay, msg, calls):
            ...     print(chunk)
        """
        async for chunk_str in self._client.chat_stream(payload):
            logger.debug("Received chunk: %s", chunk_str)
            data = parse_chunk(chunk_str)
            if not data:
                continue
            if "security" in data:
                yield json.dumps(data) + "\n"
            elif "message" in data:
                for line in self._process_message_chunk(data, assistant_msg, tool_calls):
                    yield line

    def _process_message_chunk(
        self,
        data: Dict[str, Any],
        assistant_msg: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
    ) -> List[str]:
        """Extracts content chunks and accumulates tool calls from a parsed message chunk.

        High level role: Message chunk router.
        Description: Inspects a parsed chunk's message field, appends text content to
        the assistant accumulator, and collects any tool call structures found.

        Args:
            data (Dict[str, Any]): Parsed NDJSON message chunk.
            assistant_msg (Dict[str, Any]): Mutable assistant message accumulator.
            tool_calls (List[Dict[str, Any]]): Mutable accumulated tool calls list.

        Returns:
            List[str]: Serialized NDJSON lines ready to yield downstream.

        Raises:
            None

        Examples:
            >>> processor = AgentStreamProcessor()
            >>> processor._process_message_chunk(data, assistant_msg, tool_calls)
            ['{"message": {"role": "assistant", "content": "Hi"}}\\n']
        """
        to_yield = []
        msg = data["message"]

        if "content" in msg and msg["content"]:
            logger.info("Yielding content chunk: %s...", msg["content"][:20])
            assistant_msg["content"] += msg["content"]
            to_yield.append(json.dumps(data) + "\n")

        if "tool_calls" in msg:
            logger.info("Detected tool call in stream: %d calls", len(msg["tool_calls"]))
            tool_calls.extend(msg["tool_calls"])
            to_yield.append(json.dumps(data) + "\n")

        return to_yield

    async def _recurse_tools(
        self,
        request: ChatRequest,
        messages: List[Dict[str, Any]],
        assistant_msg: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
        depth: int,
    ) -> AsyncGenerator[str, None]:
        """Appends the assistant tool-call message and recurses with tool execution.

        High level role: Tool recursion coordinator.
        Description: Stamps the assistant message with its tool calls, appends it to
        history, delegates parallel execution to ToolExecutor, then recurses into the
        next model turn with the updated message history.

        Args:
            request (ChatRequest): Original request options.
            messages (List[Dict[str, Any]]): Active conversation history (mutated in place).
            assistant_msg (Dict[str, Any]): The current step's assistant message.
            tool_calls (List[Dict[str, Any]]): Tool calls to execute.
            depth (int): Current recursion depth of the tool loop.

        Yields:
            str: Stream chunks from tool execution and subsequent model turns.

        Raises:
            None

        Examples:
            >>> processor = AgentStreamProcessor()
            >>> async for chunk in processor._recurse_tools(req, msgs, amsg, tcalls, 1):
            ...     print(chunk)
        """
        assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)

        async for chunk in self._tool_executor.execute_and_stream(tool_calls, messages):
            yield chunk

        async for next_chunk in self.handle_model_stream(request, messages, depth):
            yield next_chunk

    def _create_security_payload(self, target: str, content: str) -> str:
        """Calculates risk score and creates a security telemetry payload for user prompts.

        High level role: User-prompt security packet builder.
        Description: Runs the content through the safety preprocessor, rounds the
        resulting risk score to two decimal places, and packages it as an NDJSON line.

        Args:
            target (str): Assessment target identifier (e.g. 'user_prompt').
            content (str): The user prompt text to evaluate.

        Returns:
            str: JSON string containing risk_score, target, and value, followed by a newline.

        Raises:
            Exception: Propagates internal preprocessor analysis errors.

        Examples:
            >>> processor = AgentStreamProcessor()
            >>> processor._create_security_payload("user_prompt", "hello")
            '{"security": {"risk_score": 0.05, "target": "user_prompt", ...}}\\n'
        """
        risk_score = self._security_engine.calculate_risk(content)
        return (
            json.dumps(
                {
                    "security": {
                        "risk_score": round(risk_score, 2),
                        "target": target,
                        "value": content,
                    }
                }
            )
            + "\n"
        )
