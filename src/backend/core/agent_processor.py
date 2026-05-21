"""
Multi-turn Agent Loop Stream Processor.

High level role: Orchestrates Ollama streaming sessions, safety pipelines,
and parallel tool triggers.
"""
import concurrent.futures
import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

from backend.core.cleaner import clean_chunks_stream, parse_chunk
from backend.core.ollama_client import OllamaClient, ollama_client
from backend.core.payload_builder import build_ollama_payload
from backend.core.tool_registry import TOOL_MAP
from backend.schemas.chat import ChatRequest
from backend.security.preprocessor import SecurityPreprocessor

logger = logging.getLogger(__name__)


class AgentStreamProcessor:
    """
    Manages the multi-turn agent loop, execution of parallel tools, and streaming responses.

    High level role: Acts as the execution and safety pipeline manager for agent chats.
    It encapsulates state and behavior surrounding tool dispatching, security assessments,
    and NDJSON chunk generation.
    """

    def __init__(
        self,
        client: OllamaClient = ollama_client,
        security_engine: Optional[SecurityPreprocessor] = None
    ):
        """
        Initializes the AgentStreamProcessor with optional dependency injection.

        Args:
            client (OllamaClient): Client to communicate with Ollama.
                Default is global ollama_client.
            security_engine (SecurityPreprocessor): Safety preprocessor.
                Default is a new instance.
        """
        self._client = client
        self._security_engine = security_engine or SecurityPreprocessor()

    # ==========================================
    # Public API
    # ==========================================

    async def process_stream(
        self,
        request: ChatRequest,
        messages: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """
        Primary entry point of the pipeline checking prompt risk and starting the stream.

        High level role: Coordinates input security preprocessing and Ollama chunk generation.
        Description: Assesses the risk score of the last user prompt, yields the security assessment,
        and streams the model's reply including recursive tool executions.
        How it works:
        - Gets the last user prompt from conversation history.
        - Evaluates risk score using SecurityPreprocessor, rounded to 2 digits.
        - Streams NDJSON format chunks consisting of security analysis and message completions.

        Args:
            request (ChatRequest): The incoming request payload.
            messages (List[Dict[str, Any]]): The active conversation messages history.

        Yields:
            str: NDJSON line chunks of initial security and assistant responses.

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
        depth: int = 0
    ) -> AsyncGenerator[str, None]:
        """Manages the recursive agent loop streaming cleaned chunks and running tools.

        High level role: Coordinates multi-turn model interactions and tool runs.
        Description: Prepares payload history, executes cleaned stream filter, and
        recursively fires parallel tool routines if needed.
        How it works:
        - Builds Ollama request payload including system settings and messages.
        - Pipes the raw streaming response into _clean_chunks_stream filter.
        - Triggers tool loops if tool calls are requested.

        Args:
            request (ChatRequest): Incoming chat request parameters.
            messages (List[Dict[str, Any]]): Active conversation history.
            depth (int): Current recursion depth of the tool loop.

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
        tool_calls = []
        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": ""}
        raw_stream = self._raw_model_stream(payload, assistant_msg, tool_calls)
        async for chunk in clean_chunks_stream(raw_stream, assistant_msg):
            yield chunk
        if tool_calls:
            if depth >= 5:
                logger.warning("Max tool recursion depth reached: %d", depth)
                async for chunk in self._handle_recursion_limit(messages, assistant_msg, tool_calls):
                    yield chunk
                return
            async for chunk in self._recurse_tools(request, messages, assistant_msg, tool_calls, depth + 1):
                yield chunk

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
            >>> processor = AgentStreamProcessor()
            >>> call = {"function": {"name": "get_env", "arguments": {}}}
            >>> processor.run_tool(call)
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

    async def _raw_model_stream(
        self,
        payload: Dict[str, Any],
        assistant_msg: Dict[str, Any],
        tool_calls: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """Generates raw NDJSON stream chunks from the client chat connection.

        High level role: Connects directly to the streaming client.
        Description: Streams client completions and safety events chunk by chunk.
        How it works: Iterates through client stream, parses NDJSON, and delegates
        to process_message_chunk to gather text and tool call structures.

        Args:
            payload (Dict[str, Any]): The Ollama payload configuration.
            assistant_msg (Dict[str, Any]): Mutable dict tracking assistant role text.
            tool_calls (List[Dict[str, Any]]): Mutable list gathering tool calls.

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



    # ==========================================
    # Private Internal Helpers
    # ==========================================

    async def _execute_tools_and_stream_results(
        self,
        tool_calls: List[Dict[str, Any]],
        messages: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """
        Executes a list of tool calls in parallel and yields response chunks.

        Args:
            tool_calls (List[Dict[str, Any]]): Tool calls to run in parallel.
            messages (List[Dict[str, Any]]): Active conversation history.

        Yields:
            str: NDJSON line chunks of execution results and security analysis.
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
                    tc.get("id")
                )
                yield self._create_tool_security_payload(
                    tc["function"]["name"],
                    tool_res["content"]
                )

    async def _recurse_tools(
        self,
        request: ChatRequest,
        messages: List[Dict[str, Any]],
        assistant_msg: Dict[str, Any],
        tool_calls: List[Dict[str, Any]],
        depth: int
    ) -> AsyncGenerator[str, None]:
        """
        Appends the tool-call assistant message and recurses with tool execution.

        Arguments:
            request (ChatRequest): Original request options.
            messages (List[Dict[str, Any]]): Active conversation history.
            assistant_msg (Dict[str, Any]): The current step's assistant message.
            tool_calls (List[Dict[str, Any]]): Unexecuted tool calls.
            depth (int): Current recursion depth of the tool loop.

        Yields:
            str: Stream chunks from recursion steps.
        """
        assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)

        async for chunk in self._execute_tools_and_stream_results(tool_calls, messages):
            yield chunk

        async for next_chunk in self.handle_model_stream(request, messages, depth):
            yield next_chunk

    async def _handle_recursion_limit(
        self,
        messages: List[Dict[str, Any]],
        assistant_msg: Dict[str, Any],
        tool_calls: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """Appends recursion failure responses to message history and yields tool stream chunks.

        High level role: Recursion failure notifier.
        Description: Marks tool calls as failed due to recursion depth bounds,
        appending structured error messages to history and yielding payloads to the stream.
        How it works:
        - Appends assistant's tool-calling message to active history.
        - Iterates over each requested tool call, appending a recursion limit error tool message.
        - Yields standardized tool response and safety evaluation chunks back to the client.

        Args:
            messages (List[Dict[str, Any]]): Active conversation history.
            assistant_msg (Dict[str, Any]): Mutable dict representing assistant's message.
            tool_calls (List[Dict[str, Any]]): List of pending tool calls to fail.

        Yields:
            str: Tool response and security risk evaluation chunks.

        Raises:
            None

        Examples:
            >>> processor = AgentStreamProcessor()
            >>> async for chunk in processor._handle_recursion_limit(msgs, amsg, tcalls):
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

    def _process_message_chunk(
        self,
        data: Dict[str, Any],
        assistant_msg: Dict[str, Any],
        tool_calls: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Extracts content chunks and gathers tool calls from a message chunk.

        Args:
            data (Dict[str, Any]): Parsed message chunk.
            assistant_msg (Dict[str, Any]): Mutable assistant message.
            tool_calls (List[Dict[str, Any]]): Mutable accumulated tool calls list.

        Returns:
            List[str]: Serialized outputs to yield.
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

    def _process_task_result(
        self,
        future: concurrent.futures.Future,
        tc: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Obtains a future result and safely formats the tool output payload.

        Arguments:
            future (concurrent.futures.Future): Active task future.
            tc (Dict[str, Any]): The original tool call description.

        Returns:
            Dict[str, Any]: Formatted tool response message.
        """
        tc_id = tc.get("id")
        try:
            tool_res = future.result()
        except Exception as e:  # pylint: disable=broad-exception-caught
            tool_res = {
                "role": "tool",
                "content": f"Error: {e}",
                "name": tc["function"]["name"]
            }
            if tc_id:
                tool_res["tool_call_id"] = tc_id
        return tool_res

    def _create_tool_response_payload(
        self,
        name: str,
        args: Any,
        content: str,
        tool_call_id: Optional[str] = None
    ) -> str:
        """
        Helper to create a tool response payload JSON string.

        Arguments:
            name (str): The name of the tool.
            args (Any): The tools arguments.
            content (str): The execution text content.
            tool_call_id (Optional[str]): The corresponding tool call ID.

        Returns:
            str: JSON string ready for output streaming.
        """
        tr = {
            "name": name,
            "arguments": args,
            "content": content,
        }
        if tool_call_id:
            tr["id"] = tool_call_id
        return json.dumps({"tool_response": tr}) + "\n"

    def _create_security_payload(self, target: str, content: str) -> str:
        """
        Calculates risk score and creates a standard security telemetry log payload.

        High level role: Standardizes the security telemetry packet creation.
        Description: Processes the given content through the safety preprocessor,
        rounds the resulting risk score to two decimal places, and packages it.
        How it works:
        - Calls the preprocessor to analyze safety risk.
        - Rounds risk to 2 digits.
        - Formats the resulting values into a security trace JSON string block.

        Args:
            target (str): The assessment target identifier (e.g. 'user_prompt', 'tool_execute_shell_command').
            content (str): The text content (user prompt or tool execution result) to evaluate.

        Returns:
            str: JSON string containing the security risk analysis with risk_score, target, and value.

        Raises:
            Exception: Propagates internal preprocessor analysis errors.

        Examples:
            >>> processor = AgentStreamProcessor()
            >>> processor._create_security_payload("user_prompt", "hello")
        """
        risk_score = self._security_engine.calculate_risk(content)
        rounded_risk_score = round(risk_score, 2)
        return json.dumps({
            "security": {
                "risk_score": rounded_risk_score,
                "target": target,
                "value": content
            }
        }) + "\n"

    def _create_tool_security_payload(self, name: str, content: str) -> str:
        """
        Helper to calculate and format a tool response security risk payload.

        High level role: Formats tool response safety assessments.
        Description: Calculates the Bayesian security risk score of the tool output content
        and packages it into a standard security trace payload.
        How it works:
        - Delegates execution to the centralized security payload builder.

        Args:
            name (str): The name of the tool being analyzed.
            content (str): The execution text content to analyze.

        Returns:
            str: JSON string containing the security risk analysis with risk_score, target, and value.

        Raises:
            Exception: Propagates internal preprocessor analysis errors.

        Examples:
            >>> processor = AgentStreamProcessor()
            >>> processor._create_tool_security_payload("execute_shell_command", "output text")
        """
        return self._create_security_payload(f"tool_{name}", content)

