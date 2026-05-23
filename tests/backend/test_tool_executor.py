"""Unit tests for the ToolExecutor class.

High level role: Validates synchronous tool dispatching, parallel execution,
result formatting, tool_call_id propagation, and recursion limit error handling.
"""

import json
from typing import Any, Dict

import pytest

from backend.core.tool_executor import ToolExecutor


class TestToolExecutor:
    """Unit tests for ToolExecutor covering dispatch, parallel execution, and error paths.

    High level role: Ensures tool running, ID propagation, and failure resilience
    are all correctly handled by the ToolExecutor in isolation.
    """

    def test_run_tool_nominal(self):
        """Verifies that run_tool returns the expected name field and content for a known tool.

        Examples:
            >>> test = TestToolExecutor()
            >>> test.test_run_tool_nominal()
        """
        executor = ToolExecutor()
        res = executor.run_tool(
            {"function": {"name": "read_file", "arguments": {"filename": ".env"}}}
        )

        assert res["role"] == "tool"
        assert res["name"] == "read_file"
        assert "DB_URL" in res["content"]

    def test_run_tool_destructive_command_blocking(self):
        """Verifies that destructive shell commands like 'rm' are securely blocked.

        Examples:
            >>> test = TestToolExecutor()
            >>> test.test_run_tool_destructive_command_blocking()
        """
        executor = ToolExecutor()
        res = executor.run_tool(
            {"function": {"name": "execute_shell_command", "arguments": {"command": "rm -rf /"}}}
        )

        assert "Permission denied" in res["content"]

    def test_run_tool_tool_call_id_propagation(self):
        """Verifies that tool_call_id is propagated into the result on nominal execution.

        Examples:
            >>> test = TestToolExecutor()
            >>> test.test_run_tool_tool_call_id_propagation()
        """
        executor = ToolExecutor()
        res = executor.run_tool(
            {
                "id": "call_nom_123",
                "function": {"name": "read_file", "arguments": {"filename": ".env"}},
            }
        )

        assert res["role"] == "tool"
        assert res["name"] == "read_file"
        assert res["tool_call_id"] == "call_nom_123"
        assert "DB_URL" in res["content"]

    @pytest.mark.asyncio
    async def test_execute_and_stream_tool_call_id_on_exception(self):
        """Verifies that tool_call_id is propagated inside exception payloads.

        Description: Monkey-patches run_tool to raise, then checks that the resulting
        tool message in history still carries the correct tool_call_id.

        Examples:
            >>> test = TestToolExecutor()
            >>> await test.test_execute_and_stream_tool_call_id_on_exception()
        """
        executor = ToolExecutor()

        def crash_run_tool(tool_call: Dict[str, Any]) -> Dict[str, Any]:
            raise RuntimeError("Simulated crash")

        executor.run_tool = crash_run_tool

        tool_calls = [
            {
                "id": "call_err_123",
                "function": {"name": "execute_shell_command", "arguments": {"command": "ls"}},
            }
        ]

        messages: list = []
        chunks = []
        async for chunk in executor.execute_and_stream(tool_calls, messages):
            chunks.append(json.loads(chunk.strip()))

        assert len(messages) == 1
        assert messages[0]["role"] == "tool"
        assert messages[0]["tool_call_id"] == "call_err_123"
        assert "Simulated crash" in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_handle_recursion_limit_yields_error_payloads(self):
        """Verifies that handle_recursion_limit yields error tool_response chunks for each call.

        Description: Passes two pending tool calls and asserts both produce a
        tool_response payload containing the recursion-limit error message.

        Examples:
            >>> test = TestToolExecutor()
            >>> await test.test_handle_recursion_limit_yields_error_payloads()
        """
        executor = ToolExecutor()
        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": ""}
        messages: list = []
        tool_calls = [
            {"function": {"name": "get_env", "arguments": {}}},
            {"function": {"name": "read_file", "arguments": {"filename": ".env"}}},
        ]

        chunks = []
        async for chunk in executor.handle_recursion_limit(messages, assistant_msg, tool_calls):
            chunks.append(json.loads(chunk.strip()))

        tool_responses = [c for c in chunks if "tool_response" in c]
        assert len(tool_responses) == 2
        for tr in tool_responses:
            assert "maximum tool recursion depth (5) was reached" in tr["tool_response"]["content"]

        # assistant_msg should now be in messages
        assert messages[0]["role"] == "assistant"
        assert len(messages) == 3  # assistant + 2 tool error responses
