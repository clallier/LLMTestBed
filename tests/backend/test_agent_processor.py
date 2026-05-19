import json
from typing import Any, AsyncGenerator, Dict

import pytest

from backend.core.agent_processor import AgentStreamProcessor
from backend.core.ollama_client import OllamaClient
from backend.schemas.chat import ChatMessage, ChatRequest

from .mocks.ollama_client import MockOllamaClient


class TestAgentStreamProcessor:
    """
    Unit tests for the AgentStreamProcessor class covering normal and edge cases.

    High level role: Validates the end-to-end stream processing, safety assessments,
    and parallel tool executions.
    """

    @pytest.mark.asyncio
    async def test_nominal_no_tools(self):
        """
        Verifies nominal stream processing when the agent doesn't invoke any tools.

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

        # Read the entire processed stream
        output_chunks = []
        async for chunk in processor.process_stream(request, []):
            output_chunks.append(json.loads(chunk.strip()))

        # We expect:
        # 1. The initial user prompt security assessment packet
        # 2. Content chunks
        assert len(output_chunks) >= 3

        # Check initial security analysis
        assert "security" in output_chunks[0]
        assert output_chunks[0]["security"]["target"] == "user_prompt"

        # Check aggregated assistant content
        content = "".join(
            c["message"]["content"]
            for c in output_chunks
            if "message" in c and "content" in c["message"]
        )
        assert content == "Hello world!"

    @pytest.mark.asyncio
    async def test_parallel_tools(self):
        """
        Verifies nominal stream processing when the agent triggers parallel tool calls.

        Examples:
            >>> test = TestAgentStreamProcessor()
            >>> await test.test_parallel_tools()
        """
        # Phase 1 chunks: The agent generated 2 tool calls
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
                                    "name": "read_sensitive_file",
                                    "arguments": {"filename": ".env"},
                                },
                            },
                            {
                                "type": "function",
                                "function": {
                                    "name": "execute_command",
                                    "arguments": {"command": "whoami"},
                                },
                            },
                        ],
                    }
                }
            )
        ]

        # Phase 2 chunks: Final response after receiving tool results
        final_chunks = [
            json.dumps({"message": {"role": "assistant", "content": "Tool results received."}})
        ]

        # A mock client that handles the recursive chat stream calls:
        # First call gets parallel tool calls; second recursive call gets final assistant text.
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

        # Verify that parallel tools were simulated, output logs yielded, and final text received
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

        # We expect:
        # - SECURITY (initial user prompt risk check)
        # - MESSAGE (the tool calls payload)
        # - TOOL_RESPONSE (for read_sensitive_file)
        # - SECURITY (tool response safety risk check)
        # - TOOL_RESPONSE (for execute_command)
        # - SECURITY (tool response safety risk check)
        # - MESSAGE (final response)
        assert "SECURITY" in log_types
        assert "TOOL_RESPONSE" in log_types
        assert "read_sensitive_file" in tool_response_names
        assert "execute_command" in tool_response_names

        # Confirm that tool outputs are correctly simulated in tool responses
        tool_responses = [c["tool_response"] for c in output_chunks if "tool_response" in c]
        for tr in tool_responses:
            if tr["name"] == "read_sensitive_file":
                assert "SECRET_DATABASE_URL" in tr["content"]
            elif tr["name"] == "execute_command":
                assert tr["content"] == "sandbox_agent_user"

    def test_edge_case_destructive_command_blocking(self):
        """
        Verifies that destructive shell commands like 'rm' or 'mv' are securely blocked.

        Examples:
            >>> test = TestAgentStreamProcessor()
            >>> test.test_edge_case_destructive_command_blocking()
        """
        processor = AgentStreamProcessor()

        # Invoke execute_command with a destructive command
        res = processor.run_tool(
            {"function": {"name": "execute_command", "arguments": {"command": "rm -rf /"}}}
        )

        assert "Error: Permission denied" in res["content"]

    @pytest.mark.asyncio
    async def test_edge_case_malformed_chunk_handling(self):
        """
        Verifies that malformed JSON chunks are gracefully ignored without throwing exceptions.

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

        # The malformed chunk should be skipped, and the nominal chunk should render correctly
        content = "".join(
            c["message"]["content"]
            for c in output_chunks
            if "message" in c and "content" in c["message"]
        )
        assert content == "Passed!"

    def test_tool_response_name_field(self):
        """
        Verifies that tool responses contain the required 'name' field in compliance with standard protocols.

        High level role: Asserts presence of required API protocol fields to prevent multi-step reasoning failures.

        Examples:
            >>> test = TestAgentStreamProcessor()
            >>> test.test_tool_response_name_field()
        """
        processor = AgentStreamProcessor()
        res = processor.run_tool(
            {"function": {"name": "read_sensitive_file", "arguments": {"filename": ".env"}}}
        )

        assert res["role"] == "tool"
        assert res["name"] == "read_sensitive_file"
        assert "SECRET_DATABASE_URL" in res["content"]

    def test_tool_call_id_propagation_standard(self):
        """
        Verifies that tool_call_id is successfully propagated during nominal tool executions.
        """
        processor = AgentStreamProcessor()
        res = processor.run_tool(
            {
                "id": "call_nom_123",
                "function": {"name": "read_sensitive_file", "arguments": {"filename": ".env"}},
            }
        )

        assert res["role"] == "tool"
        assert res["name"] == "read_sensitive_file"
        assert res["tool_call_id"] == "call_nom_123"
        assert "SECRET_DATABASE_URL" in res["content"]

    @pytest.mark.asyncio
    async def test_tool_call_id_propagation_exception(self):
        """
        Verifies that tool_call_id is successfully propagated inside exception payloads.
        """
        processor = AgentStreamProcessor()

        # Stub run_tool to throw an exception
        def crash_run_tool(tool_call):
            raise RuntimeError("Simulated crash")

        processor.run_tool = crash_run_tool

        tool_calls = [
            {
                "id": "call_err_123",
                "function": {"name": "execute_command", "arguments": {"command": "ls"}},
            }
        ]

        messages = []
        chunks = []
        async for chunk in processor._execute_tools_and_stream_results(tool_calls, messages):
            chunks.append(json.loads(chunk.strip()))

        assert len(messages) == 1
        assert messages[0]["role"] == "tool"
        assert messages[0]["tool_call_id"] == "call_err_123"
        assert "Simulated crash" in messages[0]["content"]
