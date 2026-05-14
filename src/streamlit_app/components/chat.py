from _pytest import cacheprovider
import streamlit as st
import httpx
import json
import time
from typing import Dict, Any, List

from streamlit_app.config import BACKEND_URL

def add_log(log_type: str, data: Any):
    """Adds a trace log to the session state."""
    st.session_state.logs.append({
        "time": time.strftime("%H:%M:%S"),
        "type": log_type,
        "data": data
    })

def _render_message_history():
    """Iterates through session state and renders previous messages."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def _build_chat_payload(selected_model: str, system_prompt: str, selected_tool_names: List[str], available_tools: List[Dict]) -> Dict:
    """Constructs the JSON payload for the backend /chat endpoint."""
    tools = [t for t in available_tools if t["function"]["name"] in selected_tool_names] if available_tools else []
    return {
        "model": selected_model,
        "messages": st.session_state.messages,
        "system": system_prompt,
        "stream": True,
        "tools": tools if tools else None
    }

def process_assistant_response(selected_model: str, system_prompt: str, selected_tool_names: List[str], available_tools: List[Dict]):
    """Main orchestrator for fetching and rendering the assistant's streaming response."""
    with st.chat_message("assistant"):
        # Fix ghost message bug by wrapping in a container as per official demo
        with st.container():
            payload = _build_chat_payload(selected_model, system_prompt, selected_tool_names, available_tools)
            add_log("REQUEST", payload)

            _execute_chat_request(payload)
        
        st.session_state.is_processing = False
        st.rerun()

def _execute_chat_request(payload: Dict):
    """Executes the HTTP request and uses st.write_stream for the response."""
    state = {"full_response": "", "thinking_content": ""}
    
    def response_generator():
        try:
            with httpx.stream("POST", f"{BACKEND_URL}/chat", json=payload, timeout=120.0) as r:
                for line in r.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        if "message" in chunk:
                            msg = chunk["message"]
                            if "content" in msg:
                                state["full_response"] += msg["content"]
                                yield msg["content"]
                            if "thinking" in msg:
                                state["thinking_content"] += msg["thinking"]
                            if "tool_calls" in msg:
                                add_log("TOOL", msg["tool_calls"])
                
                add_log("RESPONSE", {"content": state["full_response"], "thinking": state["thinking_content"]})
        except Exception as e:
            st.error(f"Error: {e}")
            add_log("ERROR", {"message": str(e)})

    # Use native write_stream for that premium feel
    with st.spinner("Thinking..."):
        full_response = st.write_stream(response_generator)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})

def _handle_json_response(data: Dict, state: Dict):
    """Handles a complete (non-streaming) JSON fallback response."""
    state["full_response"] = data["message"]["content"]
    state["thinking_content"] = data["message"].get("thinking", "")
    add_log("RESPONSE", data)

def _handle_stream_chunk(data: Dict, message_placeholder: Any, state: Dict):
    """Processes a single NDJSON chunk and updates the UI."""
    if "message" not in data:
        return
        
    if "content" in data["message"]:
        state["full_response"] += data["message"]["content"]
        message_placeholder.markdown(state["full_response"] + "▌")
    if "thinking" in data["message"]:
        state["thinking_content"] += data["message"]["thinking"]
    if "tool_calls" in data["message"]:
        add_log("TOOL", data["message"]["tool_calls"])
