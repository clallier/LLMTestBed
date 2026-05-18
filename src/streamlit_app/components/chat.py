"""
Chat bubble rendering component for the Streamlit Sandbox interface.

High level role: Handles Streamlit UI layouts, bubble styling, and real-time streaming displays.
All data processing and API coordinator structures are delegated to ChatProcessor.
"""

from typing import Any, Dict, List

import streamlit as st

from streamlit_app.components.processors.chat import ChatProcessor
from streamlit_app.components.processors.logs import add_log
from streamlit_app.constants import AVATAR_TOOLS, ROLE_ASSISTANT, ROLE_TOOLS, get_backend_url


def _get_processor() -> ChatProcessor:
    """Lazily instantiates the completions processor with the active backend URL."""
    return ChatProcessor(get_backend_url())

# ==========================================
# Public API (Rendering Logic)
# ==========================================

def render_message(message: Dict[str, Any]):
    """
    Renders a single message bubble inside the Streamlit Sandbox container.

    High level role: Delegates correct theme structures and avatar icons based on custom roles.

    Arguments:
        message (Dict[str, Any]): Message object containing 'role' and 'content'.

    Returns:
        None
    """
    role = message["role"]
    content = message["content"]
    
    if role == ROLE_TOOLS:
        with st.chat_message(ROLE_TOOLS, avatar=AVATAR_TOOLS):
            st.markdown(content)
    else:
        with st.chat_message(role):
            st.markdown(content)

def render_message_history():
    """
    Iterates and restores visual message history bubbles inside the chat sandbox.

    High level role: Iterates st.session_state.messages and draws bubbles in chronological sequence.

    Arguments:
        None

    Returns:
        None
    """
    for message in st.session_state.messages:
        render_message(message)

def _append_messages_to_history(tools_content: str, assistant_content: str):
    """Helper to append finalized assistant and tools blocks to message history."""
    if tools_content:
        st.session_state.messages.append({"role": ROLE_TOOLS, "content": tools_content})
    if assistant_content:
        st.session_state.messages.append({"role": ROLE_ASSISTANT, "content": assistant_content})

def render_streaming_response(processor: ChatProcessor, payload: Dict[str, Any]):
    """
    Executes raw HTTP response stream fetches and coordinates real-time visual updates.

    High level role: Renders parallel tool blocks and assistant messages dynamically to separate placeholders.

    Arguments:
        processor (ChatProcessor): Fully initialized completion processor coordinator.
        payload (Dict[str, Any]): completions request JSON payload.

    Returns:
        None
    """
    tools_container, assistant_container = None, None
    tools_placeholder, assistant_placeholder = None, None
    tools_content, assistant_content = "", ""
    
    with st.spinner("Thinking..."):
        for block_type, text in processor.stream_response(payload):
            if block_type == ROLE_TOOLS:
                if not tools_container:
                    tools_container = st.chat_message(ROLE_TOOLS, avatar=AVATAR_TOOLS)
                    tools_placeholder = tools_container.empty()
                tools_content = text
                if tools_placeholder:
                    tools_placeholder.markdown(tools_content)
            else:
                if not assistant_container:
                    assistant_container = st.chat_message(ROLE_ASSISTANT)
                    assistant_placeholder = assistant_container.empty()
                assistant_content += text
                if assistant_placeholder:
                    assistant_placeholder.markdown(assistant_content)
            
    _append_messages_to_history(tools_content, assistant_content)

def process_assistant_response(
    selected_model: str,
    system_prompt: str,
    selected_tool_names: List[str],
    available_tools: List[Dict[str, Any]]
):
    """
    Main completions trigger coordinating request payload compilation and visual rendering.

    High level role: Orchestrates building request payload and streams it to Sandbox placeholders.

    Arguments:
        selected_model (str): Name of the active LLM to query.
        system_prompt (str): Active system-level instructions.
        selected_tool_names (List[str]): List of tool names that are enabled.
        available_tools (List[Dict[str, Any]]): Complete configurations of all registered tools.

    Returns:
        None
    """
    processor = _get_processor()
    payload = processor.build_chat_payload(selected_model, system_prompt, selected_tool_names, available_tools)
    add_log("REQUEST", payload)

    render_streaming_response(processor, payload)
    
    st.session_state.is_processing = False
    st.rerun()
