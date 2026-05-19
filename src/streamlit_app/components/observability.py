"""
Trace Explorer visualizer component for the Observability Hub.

High level role: Renders telemetry lists, JSON inspectors, and custom trace formats.
Delegates active navigation and metric formatting calculations to ObservabilityProcessor.
"""

from typing import Any, Dict, List

import streamlit as st

from streamlit_app.components.processors.observability import ObservabilityProcessor

# Component-level ObservabilityProcessor Instance (Dependency Injection)
_processor = ObservabilityProcessor()

# ==========================================
# Public API (Rendering Logic)
# ==========================================


def render_observability_hub():
    """
    Renders the Langfuse-inspired master-detail trace interface.

    High level role: Coordinates dynamic sidebar columns and detail inspectors.

    Arguments:
        None

    Returns:
        None
    """
    st.title("🕵️ Trace Explorer")
    st.markdown("Analyze system logs, tool interactions, and model reasoning in real-time.")

    logs = st.session_state.get("logs", [])
    if not logs:
        st.info("No system traces found. Send a message in the Sandbox to generate logs.")
        return

    _processor.initialize_selection_state(len(logs))

    master_col, detail_col = st.columns([1.2, 2.8], gap="large")
    with master_col:
        _render_trace_list(logs)
    with detail_col:
        _render_inspector(logs)


def render_formatted_detail(log: Dict[str, Any]):
    """
    Routes telemetry items to respective custom visual render templates.

    High level role: Selects corresponding components based on logged item types.

    Arguments:
        log (Dict[str, Any]): Telemetry log dictionary.

    Returns:
        None
    """
    data = log["data"]
    log_type = log["type"]

    if log_type == "REQUEST":
        _render_request_details(data)
    elif log_type == "RESPONSE":
        _render_response_details(data)
    elif log_type == "TOOL":
        _render_tool_details(data)
    elif log_type == "TOOL_RESPONSE":
        _render_tool_response_details(data)
    elif log_type == "SECURITY":
        _render_security_details(data)
    elif log_type == "ERROR":
        _render_error_details(data)
    else:
        st.info("No specific visualizer for this log type.")
        st.write(data)


# ==========================================
# Private Internal Helpers (Rendering Only)
# ==========================================


def _render_trace_list(logs: List[Dict[str, Any]]):
    """Renders the master list of all recorded system telemetry actions."""
    st.markdown("### 📜 Activity")
    for i, log in enumerate(reversed(logs)):
        idx = len(logs) - 1 - i
        is_selected = st.session_state.selected_log_index == idx

        if st.button(
            f"{log['time']} | {log['type']}",
            key=f"trace_btn_{idx}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            _processor.select_log(idx)


def _render_inspector(logs: List[Dict[str, Any]]):
    """Renders formatted and raw tab controls targeting selected indexes."""
    selected_log = logs[st.session_state.selected_log_index]

    _render_inspector_header(selected_log)
    st.markdown("---")

    viz_tab, json_tab = st.tabs(["✨ Formatted View", "📄 Raw JSON"])
    with viz_tab:
        render_formatted_detail(selected_log)
    with json_tab:
        st.json(selected_log["data"])


def _render_inspector_header(selected_log: Dict[str, Any]):
    """Renders metadata headers and export action buttons."""
    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.markdown(f"### 🔍 Inspector: `{selected_log['type']}`")
        st.caption(f"Logged at {selected_log['time']}")
    with head_col2:
        export_str = _processor.format_export_payload(st.session_state.get("raw_messages", []))
        st.download_button(
            "📥 Export JSON",
            data=export_str,
            file_name=f"conversation_export_{selected_log['time'].replace(':', '-')}.json",
            mime="application/json",
            use_container_width=True,
        )


def _render_user_message(content: str):
    """Renders the user message bubble in the trace history."""
    st.chat_message("user").write(content)


def _render_assistant_message(content: str, tool_calls: Any):
    """Renders assistant bubble including tool calls."""
    if tool_calls:
        with st.chat_message("assistant", avatar="⚙️"):
            st.markdown("**Generated Tool Calls:**")
            for tc in tool_calls:
                func = tc.get("function", {})
                name = func.get("name", "unknown")
                args = func.get("arguments", {})
                args_str = _processor.format_tool_arguments(args)
                st.code(f"{name}({args_str})", language="python")
            if content:
                st.markdown(content)
    else:
        st.chat_message("assistant").write(content)


def _render_tool_message(name: str, content: str):
    """Renders the tool response bubble in the trace history."""
    with st.chat_message("tool", avatar="🛠️"):
        st.markdown(f"**Tool Response (`{name}`):**")
        st.code(content, language="text")


def _render_history_message(msg: Dict[str, Any]):
    """Renders history items preventing empty text rendering blocks."""
    role = str(msg.get("role") or "unknown")
    content = msg.get("content", "")

    if role == "user":
        _render_user_message(content)
    elif role == "assistant":
        _render_assistant_message(content, msg.get("tool_calls"))
    elif role == "tool":
        _render_tool_message(str(msg.get("name") or "unknown"), content)
    else:
        st.chat_message(role).write(content)


def _render_request_details(data: Dict[str, Any]):
    """Displays user agent parameters and historical context."""
    st.markdown("#### 🚀 User Request")
    st.markdown(f"**Target Model:** `{data.get('model', 'unknown')}`")

    if "messages" in data:
        st.markdown("#### 💬 Last User Message")
        last_message = next(
            (msg for msg in reversed(data["messages"]) if msg["role"] == "user"), None
        )
        if last_message:
            st.chat_message(last_message["role"]).write(last_message["content"])

    if "system" in data:
        with st.expander("📝 System Instructions", expanded=False):
            st.code(data["system"], language="markdown")

    if "tools" in data and data["tools"]:
        with st.expander(f"🛠️ Available Tools ({len(data['tools'])})", expanded=False):
            for tool in data["tools"]:
                st.markdown(f"- **{tool['function']['name']}**: {tool['function']['description']}")

    with st.expander("💬 Conversation History", expanded=False):
        for msg in data.get("messages", []):
            _render_history_message(msg)


def _render_response_details(data: Dict[str, Any]):
    """Renders final model completion reply output structures."""
    st.markdown("#### ✨ Model Response")

    thinking = data.get("thinking") or (data.get("message", {}).get("thinking"))
    if thinking:
        st.markdown("#### 🧠 Reasoning Chain")
        st.info(thinking)

    content = data.get("content") or (data.get("message", {}).get("content"))
    if content:
        st.markdown(content)

    tool_calls = data.get("message", {}).get("tool_calls")
    if tool_calls:
        st.markdown("#### 🛠️ Generated Tool Calls")
        for tc in tool_calls:
            st.warning(f"Call: `{tc['function']['name']}`")
            st.code(tc["function"]["arguments"], language="json")


def _render_tool_details(data: Any):
    """Displays structured parallel tool execution calls."""
    st.markdown("#### 🛠️ Tool Execution")
    if isinstance(data, list):
        for call in data:
            st.warning(f"Executing: `{call['function']['name']}`")
            st.code(call["function"]["arguments"], language="json")
    else:
        st.json(data)


def _render_tool_response_details(data: Dict[str, Any]):
    """Displays outputs and parameter bounds of completed execution results."""
    st.markdown("#### ⚙️ Tool Execution Response")
    st.markdown(f"**Tool Name:** `{data.get('name', 'unknown')}`")

    arguments = data.get("arguments")
    if arguments:
        st.markdown("**Arguments:**")
        args_str = _processor.format_tool_arguments(arguments)
        st.code(args_str, language="json")

    st.markdown("**Execution Output:**")
    st.code(data.get("content", ""), language="text")


def _render_error_details(data: Dict[str, Any]):
    """Renders visual layout frames containing stack traces."""
    st.error("#### ❌ System Error")
    st.write(data.get("message", "Unknown error occurred"))
    if "traceback" in data:
        st.code(data["traceback"], language="python")


def _render_security_details(data: Dict[str, Any]):
    """Renders visual metric layouts representing guardrail scores."""
    st.markdown("#### 🛡️ Security Analysis")
    score_percent, summary, badge_color = _processor.get_security_status(data)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Risk Score", f"{score_percent:.1f}%")
    with col2:
        st.markdown(f"**Status**\n### :{badge_color}[{summary}]")

    st.markdown(f"**Target:** `{data.get('target', 'unknown')}`")

    if score_percent > 50.0:
        st.warning("⚠️ High risk of prompt injection detected in this segment.")
    else:
        st.success("✅ Content passed the Bayesian security filter.")
