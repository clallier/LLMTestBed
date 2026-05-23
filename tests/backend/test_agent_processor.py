"""Unit tests for the AgentStreamProcessor class.

High level role: Validates the agent loop orchestration — security prompt assessment,
stream cleaning, parallel tool integration, and recursion depth limiting.
Tool-specific dispatch tests live in test_tool_executor.py.
"""

import json
from typing import Any, AsyncGenerator, Dict

import pytest

from backend.core.agent_processor import AgentStreamProcessor
from backend.core.ollama_client import OllamaClient
from backend.schemas.chat import ChatMessage, ChatRequest

from .mocks.ollama_client import MockOllamaClient


class TestAgentStreamProcessor:
    """Unit tests for AgentStreamProcessor covering orchestration and edge cases.

    High level role: Validates the end-to-end stream processing, security assessments,
    and integration with parallel tool execution via ToolExecutor.
    """

    @pytest.mark.asyncio
    async def test_nominal_no_tools(self):
        """Verifies nominal stream processing when the agent doesn't invoke any tools.

        Examples:
            >>> test = TestAgentStreamProcessor()
            >>> await test.test_nominal_no_tools()
        """
        mock_chunks = [
            json.dumps({"message": {"role": "assistant", "content": "Hello "}}),
            json.dumps({"message": {"role": "assistant", "content": "world!"}}),
        ]
        mock_client = MockOllamaClient(mock_chunks)
        processor = AgentStreamProcessor(client=mock_client)
        request = ChatRequest(model="test-model", messages=[ChatMessage(role="user", content="hi")])

        output_chunks = []
        async for chunk in processor.process_stream(request, []):
            output_chunks.append(json.loads(chunk.strip()))

        # Expect: security assessment + content chunks
        assert len(output_chunks) >= 3
        assert "security" in output_chunks[0]
        assert output_chunks[0]["security"]["target"] == "user_prompt"

        content = "".join(
            c["message"]["content"]
            for c in output_chunks
            if "message" in c and "content" in c["message"]
        )
        assert content == "Hello world!"

    @pytest.mark.asyncio
    async def test_parallel_tools(self):
        """Verifies stream processing when the agent triggers parallel tool calls.

        Examples:
            >>> test = TestAgentStreamProcessor()
            >>> await test.test_parallel_tools()
        """
        tool_call_chunks = [
            json.dumps(
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "type": "function",
                                "function": {
                                    "name": "read_file",
                                    "arguments": {"filename": ".env"},
                                },
                            },
                            {
                                "type": "function",
                                "function": {
                                    "name": "execute_shell_command",
                                    "arguments": {"command": "whoami"},
                                },
                            },
                        ],
                    }
                }
            )
        ]
        final_chunks = [
            json.dumps({"message": {"role": "assistant", "content": "Tool results received."}})
        ]

        class RecursiveMockClient(OllamaClient):
            def __init__(self):
                super().__init__()
                self.call_count = 0

            async def chat_stream(self, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
                self.call_count += 1
                chunks = tool_call_chunks if self.call_count == 1 else final_chunks
                for chunk in chunks:
                    yield chunk

        mock_client = RecursiveMockClient()
        processor = AgentStreamProcessor(client=mock_client)
        request = ChatRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="run sensitive diagnostics")],
        )

        output_chunks = []
        messages_history = [msg.model_dump() for msg in request.messages]
        async for chunk in processor.process_stream(request, messages_history):
            output_chunks.append(json.loads(chunk.strip()))

        log_types = []
        tool_response_names = set()
        for c in output_chunks:
            if "security" in c:
                log_types.append("SECURITY")
            elif "tool_response" in c:
                log_types.append("TOOL_RESPONSE")
                tool_response_names.add(c["tool_response"]["name"])
            elif "message" in c:
                log_types.append("MESSAGE")

        assert "SECURITY" in log_types
        assert "TOOL_RESPONSE" in log_types
        assert "read_file" in tool_response_names
        assert "execute_shell_command" in tool_response_names

        tool_responses = [c["tool_response"] for c in output_chunks if "tool_response" in c]
        for tr in tool_responses:
            if tr["name"] == "read_file":
                assert "DB_URL" in tr["content"]
            elif tr["name"] == "execute_shell_command":
                assert tr["content"] == "prod_agent_user"

    @pytest.mark.asyncio
    async def test_edge_case_malformed_chunk_handling(self):
        """Verifies that malformed JSON chunks are gracefully ignored without throwing exceptions.

        Examples:
            >>> test = TestAgentStreamProcessor()
            >>> await test.test_edge_case_malformed_chunk_handling()
        """
        mock_chunks = [
            "NOT VALID JSON",
            json.dumps({"message": {"role": "assistant", "content": "Passed!"}}),
        ]
        mock_client = MockOllamaClient(mock_chunks)
        processor = AgentStreamProcessor(client=mock_client)
        request = ChatRequest(model="test-model", messages=[ChatMessage(role="user", content="hi")])

        output_chunks = []
        async for chunk in processor.process_stream(request, []):
            output_chunks.append(json.loads(chunk.strip()))

        content = "".join(
            c["message"]["content"]
            for c in output_chunks
            if "message" in c and "content" in c["message"]
        )
        assert content == "Passed!"

    @pytest.mark.asyncio
    async def test_stream_cleaning_e2e_mock(self):
        """Simulates structured JSON-prefix output chunk-by-chunk to verify prefix cleaning.

        High level role: Integration test verifying end-to-end stream sanitization.
        Description: Replaces client stream with mock chunks containing JSON garbage and
        validates that AgentStreamProcessor correctly cleans the stream in-place.

        Examples:
            >>> test = TestAgentStreamProcessor()
            >>> await test.test_stream_cleaning_e2e_mock()
        """
        mock_chunks = [
            json.dumps({"message": {"role": "assistant", "content": '"}; [{"name": '}}),
            json.dumps({"message": {"role": "assistant", "content": '"get_env"}]Here is '}}),
            json.dumps({"message": {"role": "assistant", "content": "the key"}}),
        ]
        mock_client = MockOllamaClient(mock_chunks)
        processor = AgentStreamProcessor(client=mock_client)
        request = ChatRequest(model="test-model", messages=[ChatMessage(role="user", content="hi")])

        output_chunks = []
        async for chunk in processor.process_stream(request, []):
            output_chunks.append(json.loads(chunk.strip()))

        full_content = "".join(
            c["message"]["content"]
            for c in output_chunks
            if "message" in c and "content" in c["message"]
        )
        assert "Here is the key" in full_content
        assert "get_env" not in full_content

    @pytest.mark.asyncio
    async def test_recursion_depth_limit(self):
        """Verifies that the recursion depth limit prevents infinite tool execution loops.

        High level role: Unit test verifying recursion prevention bounds.
        Description: Simulates an agent that keeps returning tool calls endlessly,
        and asserts that the processor terminates safely after 5 iterations.

        Examples:
            >>> test = TestAgentStreamProcessor()
            >>> await test.test_recursion_depth_limit()
        """
        tool_call_chunk = json.dumps(
            {
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {"name": "get_env", "arguments": {}},
                        }
                    ],
                }
            }
        )

        class LoopMockClient(OllamaClient):
            def __init__(self):
                super().__init__()
                self.call_count = 0

            async def chat_stream(self, payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
                self.call_count += 1
                yield tool_call_chunk

        mock_client = LoopMockClient()
        processor = AgentStreamProcessor(client=mock_client)
        request = ChatRequest(
            model="test-model",
            messages=[ChatMessage(role="user", content="loop please")],
        )

        history = [{"role": "user", "content": "loop please"}]
        output_chunks = []
        async for chunk in processor.process_stream(request, history):
            output_chunks.append(json.loads(chunk.strip()))

        assert mock_client.call_count == 6
        assert len(history) > 1
        last_msg = history[-1]
        assert last_msg["role"] == "tool"
        assert "maximum tool recursion depth (5) was reached" in last_msg["content"]

        tool_responses = [c for c in output_chunks if "tool_response" in c]
        assert len(tool_responses) > 0
        assert (
            "maximum tool recursion depth (5) was reached"
            in tool_responses[-1]["tool_response"]["content"]
        )
