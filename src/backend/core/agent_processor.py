import json
import logging
import concurrent.futures
from typing import Any, Dict, List, AsyncGenerator, Optional

from backend.schemas.chat import ChatRequest
from backend.core.ollama_client import ollama_client, OllamaClient
from backend.core.tool_registry import TOOL_MAP
from backend.core.payload_builder import build_ollama_payload
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
            client (OllamaClient): Client to communicate with Ollama. Default is global ollama_client.
            security_engine (SecurityPreprocessor): Safety preprocessor. Default is a new instance.
        """
        self._client = client
        self._security_engine = security_engine or SecurityPreprocessor()

    def run_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a single tool call against the TOOL_MAP.

        Args:
            tool_call (Dict[str, Any]): The tool call object.

        Returns:
            Dict[str, Any]: Role 'tool' response message.
        """
        func_name = tool_call["function"]["name"]
        args = tool_call["function"]["arguments"]
        
        if isinstance(args, str):
            args = json.loads(args)
            
        if func_name in TOOL_MAP:
            logger.info(f"Executing tool: {func_name}")
            result = TOOL_MAP[func_name](**args)
            return {"role": "tool", "content": str(result), "name": func_name}
        
        return {"role": "tool", "content": f"Error: Tool {func_name} not found", "name": func_name}

    def _parse_chunk(self, chunk_str: str) -> Optional[Dict[str, Any]]:
        """
        Parses a raw NDJSON chunk from Ollama.

        Args:
            chunk_str (str): The raw chunk string.

        Returns:
            Optional[Dict[str, Any]]: Parsed dictionary if successful, None otherwise.
        """
        try:
            return json.loads(chunk_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON chunk: {chunk_str}")
            return None

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
            logger.info(f"Yielding content chunk: {msg['content'][:20]}...")
            assistant_msg["content"] += msg["content"]
            to_yield.append(json.dumps(data) + "\n")
            
        if "tool_calls" in msg:
            logger.info(f"Detected tool call in stream: {len(msg['tool_calls'])} calls")
            tool_calls.extend(msg["tool_calls"])
            to_yield.append(json.dumps(data) + "\n")
            
        return to_yield

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
                try:
                    tool_res = future.result()
                except Exception as e:
                    tool_res = {"role": "tool", "content": f"Error: {e}", "name": tc["function"]["name"]}
                
                messages.append(tool_res)
                
                yield json.dumps({
                    "tool_response": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"]["arguments"],
                        "content": tool_res["content"]
                    }
                }) + "\n"
                
                risk_score = self._security_engine.calculate_risk(tool_res["content"])
                yield json.dumps({
                    "security": {
                        "risk_score": risk_score,
                        "target": f"tool_{tc['function']['name']}",
                        "summary": "High risk tool output" if risk_score > 0.8 else "Safe"
                    }
                }) + "\n"

    async def handle_model_stream(
        self,
        request: ChatRequest,
        messages: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """
        Manages the recursive agent loop streaming chunks and initiating tool calls.

        Args:
            request (ChatRequest): Incoming chat request parameters.
            messages (List[Dict[str, Any]]): Conversation history.

        Yields:
            str: Stream chunks.
        """
        payload = build_ollama_payload(request, stream=True)
        payload["messages"] = messages
        
        tool_calls = []
        assistant_msg: Dict[str, Any] = {"role": "assistant", "content": ""}
        
        async for chunk_str in self._client.chat_stream(payload):
            logger.debug(f"Received chunk: {chunk_str}")
            data = self._parse_chunk(chunk_str)
            if not data:
                continue
                
            if "security" in data:
                yield json.dumps(data) + "\n"
            elif "message" in data:
                for line in self._process_message_chunk(data, assistant_msg, tool_calls):
                    yield line
            
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)
            
            async for chunk in self._execute_tools_and_stream_results(tool_calls, messages):
                yield chunk
                
            async for next_chunk in self.handle_model_stream(request, messages):
                yield next_chunk

    async def process_stream(
        self,
        request: ChatRequest,
        messages: List[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """
        Primary entry point of the pipeline checking prompt risk and starting the stream.

        Args:
            request (ChatRequest): The incoming request payload.
            messages (List[Dict[str, Any]]): The active conversation messages.

        Yields:
            str: NDJSON line chunks of initial security and assistant responses.
        """
        last_prompt = messages[-1]["content"] if messages else ""
        risk_score = self._security_engine.calculate_risk(last_prompt)
        yield json.dumps({
            "security": {
                "risk_score": risk_score,
                "target": "user_prompt",
                "summary": "High risk prompt" if risk_score > 0.8 else "Safe"
            }
        }) + "\n"
        
        async for chunk in self.handle_model_stream(request, messages):
            yield chunk
