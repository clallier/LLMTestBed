"""Tool dispatching, parallel execution, and result telemetry.

High level role: Encapsulates all tool-related execution logic, including
synchronous dispatch, parallel streaming, and security telemetry for tool
responses. Keeps the agent loop orchestrator free of tool-specific concerns.
"""

import concurrent.futures
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.core.tool_registry import TOOL_MAP
from backend.security.preprocessor import SecurityPreprocessor

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Dispatches tool calls, manages parallel execution, and formats result payloads.

    High level role: Single-responsibility owner of tool execution. Runs tools
    synchronously or in parallel thread pools, wraps results as NDJSON payloads,
    and emits security telemetry for each tool response. Accepts a shared
    SecurityPreprocessor via dependency injection to stay consistent with the
    agent's risk scoring.
    """

    def __init__(self, security_engine: Optional[SecurityPreprocessor] = None):
        """Initializes the ToolExecutor with an optional shared security engine.

        Args:
            security_engine (Optional[SecurityPreprocessor]): Safety preprocessor
                instance. Defaults to a fresh SecurityPreprocessor if not provided.
        """
        self._security_engine = security_engine or SecurityPreprocessor()

    # ==========================================
    # Public API
    # ==========================================

    def run_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a single tool call payload against the system's registered tools.

        High level role: Standardizes individual tool dispatching.
        Description: Resolves target function names and extracts input parameters,
        invoking the matching routine from the global TOOL_MAP registry.
        How it works:
        - Parses input parameters (de-serializing from JSON if structured as a string).
        - Instantiates the response dictionary with function metadata and target ID.
        - Dispatches parameters dynamically, handling missing tools gracefully.

        Args:
            tool_call (Dict[str, Any]): The detailed tool call payload, containing the
                target function's name and input arguments dictionary.

        Returns:
            Dict[str, Any]: A tool response structure formatted with 'role', 'name',
                'tool_call_id' (if supplied), and the execution result string as 'content'.

        Raises:
            json.JSONDecodeError: If stringified arguments fail to parse.

        Examples:
            >>> executor = ToolExecutor()
            >>> call = {"function": {"name": "get_env", "arguments": {}}}
            >>> executor.run_tool(call)
            {'role': 'tool', 'name': 'get_env', 'content': '...'}
        """
        func_name = tool_call["function"]["name"]
        args = tool_call["function"]["arguments"]
        tc_id = tool_call.get("id")

        if isinstance(args, str):
            args = json.loads(args)

        res = {"role": "tool", "name": func_name}
        if tc_id:
            res["tool_call_id"] = tc_id

        if func_name in TOOL_MAP:
            logger.info("Executing tool: %s", func_name)
            result = TOOL_MAP[func_name](**args)
            res["content"] = str(result)
        else:
            res["content"] = f"Error: Tool {func_name} not found"

        return res

    async def execute_and_stream(
        self,
        tool_calls: List[Dict[str, Any]],
        messages: List[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """Executes a list of tool calls in parallel and yields NDJSON response chunks.

        High level role: Parallel tool runner with telemetry streaming.
        Description: Submits all tool calls to a thread pool concurrently, collects
        results as they complete, appends them to the message history, and yields
        both a tool response payload and a security risk payload for each.
        How it works:
        - Submits each tool call to a ThreadPoolExecutor.
        - Iterates over completed futures, processing results via _process_task_result.
        - Appends each result to messages and yields two NDJSON lines per tool.

        Args:
            tool_calls (List[Dict[str, Any]]): Tool calls to run in parallel.
            messages (List[Dict[str, Any]]): Active conversation history (mutated in place).

        Yields:
            str: NDJSON lines — one tool_response payload and one security payload per tool.

        Raises:
            None

        Examples:
            >>> executor = ToolExecutor()
            >>> async for chunk in executor.execute_and_stream(calls, msgs):
            ...     print(chunk)
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = {executor.submit(self.run_tool, tc): tc for tc in tool_calls}
            for future in concurrent.futures.as_completed(futures):
                tc = futures[future]
                tool_res = self._process_task_result(future, tc)
                messages.append(tool_res)
                yield self._create_tool_response_payload(
                    tc["function"]["name"],
                    tc["function"]["arguments"],
                    tool_res["content"],
                    tc.get("id"),
                )
                yield self._create_tool_security_payload(
                    tc["function"]["name"],
                    tool_res["content"],
                )

    async def handle_recursion_limit(
        self,
        messages: List[Dict[str, Any]],
        assistant_msg: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
    ) -> AsyncGenerator[str, None]:
        """Appends recursion-limit error responses to history and yields tool stream chunks.

        High level role: Recursion failure reporter.
        Description: When the agent loop has exceeded the maximum tool recursion depth,
        marks every pending tool call as failed, appends structured error messages to
        history, and yields standardized tool response and security payloads.
        How it works:
        - Stamps the assistant message with the pending tool calls and appends it.
        - Iterates over each tool call, builds a recursion-limit error response,
          appends it to history, and yields a tool_response + security chunk pair.

        Args:
            messages (List[Dict[str, Any]]): Active conversation history (mutated in place).
            assistant_msg (Dict[str, Any]): The current step's assistant message (mutated in place).
            tool_calls (List[Dict[str, Any]]): List of pending tool calls to fail.

        Yields:
            str: Tool response and security risk evaluation chunks.

        Raises:
            None

        Examples:
            >>> executor = ToolExecutor()
            >>> async for chunk in executor.handle_recursion_limit(msgs, amsg, tcalls):
            ...     print(chunk)
        """
        assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)
        for tc in tool_calls:
            name, tc_id = tc["function"]["name"], tc.get("id")
            err = "Error: Tool execution failed because maximum tool recursion depth (5) was reached."
            res = {"role": "tool", "name": name, "content": err}
            if tc_id:
                res["tool_call_id"] = tc_id
            messages.append(res)
            yield self._create_tool_response_payload(name, tc["function"]["arguments"], err, tc_id)
            yield self._create_tool_security_payload(name, err)

    # ==========================================
    # Private Internal Helpers
    # ==========================================

    def _process_task_result(
        self,
        future: concurrent.futures.Future,
        tc: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Obtains a future result and safely formats the tool output payload.

        High level role: Safe future unwrapper.
        Description: Retrieves the result of a submitted tool future, catching any
        exceptions and wrapping them into a structured error tool message.

        Args:
            future (concurrent.futures.Future): Active task future.
            tc (Dict[str, Any]): The original tool call description.

        Returns:
            Dict[str, Any]: Formatted tool response message with role, name, and content.

        Raises:
            None

        Examples:
            >>> executor = ToolExecutor()
            >>> executor._process_task_result(future, tc)
            {'role': 'tool', 'name': 'get_env', 'content': '...'}
        """
        tc_id = tc.get("id")
        try:
            return future.result()
        except Exception as e:  # pylint: disable=broad-exception-caught
            tool_res = {
                "role": "tool",
                "content": f"Error: {e}",
                "name": tc["function"]["name"],
            }
            if tc_id:
                tool_res["tool_call_id"] = tc_id
            return tool_res

    def _create_tool_response_payload(
        self,
        name: str,
        args: Any,
        content: str,
        tool_call_id: Optional[str] = None,
    ) -> str:
        """Serializes a tool execution result as an NDJSON tool_response line.

        High level role: Tool result formatter.
        Description: Packages the tool name, arguments, result content, and optional
        call ID into a standard NDJSON tool_response payload.

        Args:
            name (str): The name of the tool that was executed.
            args (Any): The arguments passed to the tool.
            content (str): The execution result text.
            tool_call_id (Optional[str]): The corresponding tool call ID, if any.

        Returns:
            str: JSON string of the tool_response payload followed by a newline.

        Raises:
            None

        Examples:
            >>> executor = ToolExecutor()
            >>> executor._create_tool_response_payload("get_env", {}, "DB_URL=...")
            '{"tool_response": {"name": "get_env", ...}}\\n'
        """
        tr = {"name": name, "arguments": args, "content": content}
        if tool_call_id:
            tr["id"] = tool_call_id
        return json.dumps({"tool_response": tr}) + "\n"

    def _create_security_payload(self, target: str, content: str) -> str:
        """Calculates risk score and creates a standard security telemetry payload.

        High level role: Security telemetry packet builder.
        Description: Runs the given content through the safety preprocessor, rounds
        the risk score to two decimal places, and packages it as an NDJSON line.

        Args:
            target (str): Assessment target identifier (e.g. 'tool_execute_shell_command').
            content (str): The text content to evaluate.

        Returns:
            str: JSON string containing risk_score, target, and value, followed by a newline.

        Raises:
            Exception: Propagates internal preprocessor analysis errors.

        Examples:
            >>> executor = ToolExecutor()
            >>> executor._create_security_payload("tool_get_env", "output text")
            '{"security": {"risk_score": 0.12, ...}}\\n'
        """
        risk_score = self._security_engine.calculate_risk(content)
        return json.dumps({
            "security": {
                "risk_score": round(risk_score, 2),
                "target": target,
                "value": content,
            }
        }) + "\n"

    def _create_tool_security_payload(self, name: str, content: str) -> str:
        """Builds a security telemetry payload scoped to a named tool response.

        High level role: Tool-scoped security reporter.
        Description: Prefixes the tool name with 'tool_' and delegates to the
        centralized security payload builder.

        Args:
            name (str): The name of the tool being analyzed.
            content (str): The execution result text to evaluate.

        Returns:
            str: JSON string containing the security risk analysis, followed by a newline.

        Raises:
            Exception: Propagates internal preprocessor analysis errors.

        Examples:
            >>> executor = ToolExecutor()
            >>> executor._create_tool_security_payload("execute_shell_command", "output")
            '{"security": {"risk_score": 0.45, "target": "tool_execute_shell_command", ...}}\\n'
        """
        return self._create_security_payload(f"tool_{name}", content)
