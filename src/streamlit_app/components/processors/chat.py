"""
Processing and API transmission handler for Streamlit chat completions.

High level role: Handles non-rendering tasks such as payload building, stream parsing,
state accumulation, and HTTP request coordination.
"""

import json
from typing import Any, Dict, Generator, List, Optional, Tuple

import httpx
import streamlit as st

from streamlit_app.components.processors.logs import add_log


class ChatProcessor:
    """
    Orchestrates completions payloads, streaming HTTP requests, and state parsing.

    High level role: Manages Ollama-compliant chat schemas and processes parallel tool outcomes.
    """

    # Internal Constants
    _TIMEOUT_SECONDS: float = 120.0
    _JSON_INDENT: int = 2

    def __init__(self, backend_url: str):
        """
        Initializes the ChatProcessor with backend configuration parameters.

        High level role: Configures target API servers via Dependency Injection.

        Arguments:
            backend_url (str): Complete HTTP URL of the completions backend.
        """
        self.backend_url = backend_url

    # ==========================================
    # Public API
    # ==========================================

    def build_chat_payload(
        self,
        selected_model: str,
        system_prompt: str,
        selected_tool_names: List[str],
        available_tools: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Constructs the JSON payload for the backend /chat completion endpoint.

        High level role: Aggregates raw history and maps custom roles to
        preserve protocol compliance.

        Arguments:
            selected_model (str): Name of the active LLM to query.
            system_prompt (str): Active system-level instructions.
            selected_tool_names (List[str]): List of tool names that are enabled.
            available_tools (List[Dict[str, Any]]): Configurations of registered tools.

        Returns:
            Dict[str, Any]: Fully formatted request payload.
        """
        tools = (
            [t for t in available_tools if t["function"]["name"] in selected_tool_names]
            if available_tools
            else []
        )

        return {
            "model": selected_model,
            "messages": [msg.copy() for msg in st.session_state.raw_messages],
            "system": system_prompt,
            "stream": True,
            "tools": tools if tools else None,
        }

    def stream_response(self, payload: Dict[str, Any]) -> Generator[Tuple[str, str], None, None]:
        """
        HTTP streaming generator fetching chunks from the backend.

        High level role: Connects to completions endpoint and yields rendering blocks.

        Arguments:
            payload (Dict[str, Any]): Fully formatted completions payload.

        Yields:
            Tuple[str, str]: A tuple of (block_type, text_block) indicating type and text.
        """
        state = {
            "full_response": "",
            "thinking_content": "",
            "assistant_content": "",
            "tool_runs": {},
        }

        try:
            with httpx.stream(
                "POST", f"{self.backend_url}/chat", json=payload, timeout=self._TIMEOUT_SECONDS
            ) as r:
                yield from self._consume_http_stream(r, state)

            self._finalize_stream_state(state)

        except Exception as e:  # pylint: disable=broad-exception-caught
            st.error(f"Error: {e}")
            add_log("ERROR", {"message": str(e)})

    # ==========================================
    # Private Internal Helpers
    # ==========================================

    def _consume_http_stream(
        self, r: httpx.Response, state: Dict[str, Any]
    ) -> Generator[Tuple[str, str], None, None]:
        """Iterates over the lines of the HTTP stream, updates state, and yields blocks."""
        for line in r.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)

            self._record_raw_history(chunk)
            block_type = self._classify_chunk_type(chunk)
            block = self._process_chunk(chunk, state)
            if block:
                yield (block_type, block)

    def _classify_chunk_type(self, chunk: Dict[str, Any]) -> str:
        """
        Determines if the chunk is an assistant completion or a tool execution step.

        Arguments:
            chunk (Dict[str, Any]): The incoming chunk data.

        Returns:
            str: "tools" or "assistant".
        """
        is_tool = (
            "message" in chunk
            and "tool_calls" in chunk["message"]
            and chunk["message"]["tool_calls"]
        )
        if is_tool or "tool_response" in chunk:
            return "tools"
        return "assistant"

    def _get_clean_content(self, state: Dict[str, Any]) -> str:
        """
        Extracts clean assistant content or falls back to full response.

        High level role: Handles fallback content identification for stream completions.

        Arguments:
            state (Dict[str, Any]): The accumulated stream state parameters.

        Returns:
            str: Clean text content.
        """
        if state["assistant_content"]:
            return state["assistant_content"]
        return state["full_response"]

    def _finalize_stream_state(self, state: Dict[str, Any]):
        """
        Records finalized assistant content to history and writes completion logs.

        Arguments:
            state (Dict[str, Any]): The accumulated stream state parameters.

        Returns:
            None
        """
        if state["assistant_content"]:
            st.session_state.raw_messages.append(
                {"role": "assistant", "content": state["assistant_content"]}
            )

        clean_content = self._get_clean_content(state)
        add_log("RESPONSE", {"content": clean_content, "thinking": state["thinking_content"]})

    def _record_raw_history(self, chunk: Dict[str, Any]):
        """Records raw messages dynamically to raw_messages to keep protocols intact."""
        is_tool = "message" in chunk and chunk["message"].get("tool_calls")
        if is_tool:
            new_c = chunk["message"]["tool_calls"]
            hist = st.session_state.raw_messages
            if hist and hist[-1].get("role") == "assistant" and "tool_calls" in hist[-1]:
                ids = {tc.get("id") for tc in hist[-1]["tool_calls"] if tc.get("id")}
                hist[-1]["tool_calls"].extend([tc for tc in new_c if tc.get("id") not in ids])
            else:
                hist.append({"role": "assistant", "content": "", "tool_calls": list(new_c)})
        elif "tool_response" in chunk:
            tr = chunk["tool_response"]
            msg = {"role": "tool", "name": tr["name"], "content": tr["content"]}
            if "id" in tr:
                msg["tool_call_id"] = tr["id"]
            st.session_state.raw_messages.append(msg)

    def _generate_tools_markdown(self, tool_runs: Dict[str, Any]) -> str:
        """Generates markdown representation of parallel tool calls and responses."""
        blocks = []
        for _, run in tool_runs.items():
            name = run["name"]
            content = run["content"]
            args = run["arguments"]
            args_str = (
                json.dumps(args, indent=self._JSON_INDENT) if isinstance(args, dict) else str(args)
            )

            block = [f"🛠️ **[Tool Call] {name}**", "**Arguments:**", f"```json\n{args_str}\n```"]

            resp_val = (
                f"```\n{content}\n```"
                if content is not None
                else "*⌛ Executing tool in parallel...*"
            )
            block.extend([f"⚙️ **[Tool Response] {name}**", resp_val])

            blocks.append("\n\n".join(block))

        return "\n\n---\n\n".join(blocks)

    def _process_chunk(self, chunk: Dict[str, Any], state: Dict[str, Any]) -> Optional[str]:
        """
        Processes a single response chunk and updates accumulated state dictionaries.

        High level role: Routes payload chunks to specific specialized processors.
        """
        if "message" in chunk:
            return self._process_message_chunk(chunk, state)
        if "tool_response" in chunk:
            return self._process_tool_response_chunk(chunk, state)
        if "security" in chunk:
            self._process_security_chunk(chunk)
        return None

    def _process_message_chunk(self, chunk: Dict[str, Any], state: Dict[str, Any]) -> Optional[str]:
        """Handles streaming message payloads, accumulated content, and tool calls."""
        msg = chunk["message"]
        if "content" in msg and msg["content"]:
            state["full_response"] += msg["content"]
            state["assistant_content"] = state.get("assistant_content", "") + msg["content"]
            return msg["content"]
        if "thinking" in msg and msg["thinking"]:
            state["thinking_content"] += msg["thinking"]
        if "tool_calls" in msg and msg["tool_calls"]:
            add_log("TOOL", msg["tool_calls"])
            self._register_tool_calls(msg["tool_calls"], state)
            block = self._generate_tools_markdown(state["tool_runs"])
            assistant_part = state.get("assistant_content", "")
            state["full_response"] = (assistant_part + "\n\n" + block) if assistant_part else block
            return block
        return None

    def _process_tool_response_chunk(
        self, chunk: Dict[str, Any], state: Dict[str, Any]
    ) -> Optional[str]:
        """Maps executing tool responses to previously pre-registered tool calls."""
        tr = chunk["tool_response"]
        add_log("TOOL_RESPONSE", tr)
        if "tool_runs" not in state:
            state["tool_runs"] = {}

        matched_id = self._match_tool_run_id(tr, state["tool_runs"])
        if matched_id:
            state["tool_runs"][matched_id]["content"] = tr["content"]
        else:
            tr_id = tr.get("id") or f"call_{len(state['tool_runs'])}"
            state["tool_runs"][tr_id] = {
                "name": tr["name"],
                "arguments": {},
                "content": tr["content"],
            }

        block = self._generate_tools_markdown(state["tool_runs"])
        assistant_part = state.get("assistant_content", "")
        state["full_response"] = (assistant_part + "\n\n" + block) if assistant_part else block
        return block

    def _process_security_chunk(self, chunk: Dict[str, Any]):
        """Records guardrail telemetry to logging systems."""
        add_log("SECURITY", chunk["security"])

    def _register_tool_calls(self, tool_calls: List[Dict[str, Any]], state: Dict[str, Any]):
        """Pre-registers parallel tool calls to tracking dictionary state."""
        if "tool_runs" not in state:
            state["tool_runs"] = {}
        for tc in tool_calls:
            tc_id = tc.get("id") or f"call_{len(state['tool_runs'])}"
            if tc_id not in state["tool_runs"]:
                st_run = {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"],
                    "content": None,
                }
                state["tool_runs"][tc_id] = st_run

    def _match_tool_run_id(self, tr: Dict[str, Any], tool_runs: Dict[str, Any]) -> Optional[str]:
        """Matches tool response ids or chronologically matches empty running slot ids."""
        tr_id = tr.get("id")
        if tr_id and tr_id in tool_runs:
            return tr_id
        for k, v in tool_runs.items():
            if v["name"] == tr["name"] and v["content"] is None:
                return k
        return None
