import streamlit as st
import json
from typing import Dict, Any, List

def render_observability_hub():
    """Renders a Langfuse-inspired Observability Hub for deep trace analysis."""
    st.title("🕵️ Trace Explorer")
    st.markdown("Analyze system logs, tool interactions, and model reasoning in real-time.")
    
    logs = st.session_state.get("logs", [])
    if not logs:
        st.info("No system traces found. Send a message in the Sandbox to generate logs.")
        return

    _initialize_selection_state(len(logs))

    master_col, detail_col = st.columns([1.2, 2.8], gap="large")
    with master_col:
        _render_trace_list(logs)
    with detail_col:
        _render_inspector(logs)

def _initialize_selection_state(logs_length: int):
    """Initializes or resets the selected log index."""
    if "selected_log_index" not in st.session_state:
        st.session_state.selected_log_index = logs_length - 1
    elif st.session_state.selected_log_index >= logs_length:
        st.session_state.selected_log_index = logs_length - 1

def _render_trace_list(logs: List[Dict[str, Any]]):
    """Renders the master list of all traces."""
    st.markdown("### 📜 Activity")
    for i, log in enumerate(reversed(logs)):
        idx = len(logs) - 1 - i
        is_selected = st.session_state.selected_log_index == idx
        
        if st.button(
            f"{log['time']} | {log['type']}", 
            key=f"trace_btn_{idx}", 
            use_container_width=True, 
            type="primary" if is_selected else "secondary"
        ):
            st.session_state.selected_log_index = idx
            st.rerun()

def _render_inspector(logs: List[Dict[str, Any]]):
    """Renders the detailed inspector for the selected trace."""
    selected_log = logs[st.session_state.selected_log_index]
    
    _render_inspector_header(selected_log)
    st.markdown("---")

    viz_tab, json_tab = st.tabs(["✨ Formatted View", "📄 Raw JSON"])
    with viz_tab:
        render_formatted_detail(selected_log)
    with json_tab:
        st.json(selected_log['data'])

def _render_inspector_header(selected_log: Dict[str, Any]):
    """Renders the title and export button for the inspector."""
    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.markdown(f"### 🔍 Inspector: `{selected_log['type']}`")
        st.caption(f"Logged at {selected_log['time']}")
    with head_col2:
        export_payload = {
            "timestamp": selected_log['time'],
            "type": selected_log['type'],
            "data": selected_log['data']
        }
        st.download_button(
            "📥 Export JSON",
            data=json.dumps(export_payload, indent=2),
            file_name=f"trace_{selected_log['time'].replace(':', '-')}.json",
            mime="application/json",
            use_container_width=True
        )

def render_formatted_detail(log: Dict[str, Any]):
    """Routes the log data to the appropriate visualizer based on type."""
    data = log['data']
    log_type = log['type']

    if log_type == "REQUEST":
        _render_request_details(data)
    elif log_type == "RESPONSE":
        _render_response_details(data)
    elif log_type == "TOOL":
        _render_tool_details(data)
    elif log_type == "SECURITY":
        _render_security_details(data)
    elif log_type == "ERROR":
        _render_error_details(data)
    else:
        st.info("No specific visualizer for this log type.")
        st.write(data)

def _render_request_details(data: Dict[str, Any]):
    """Renders formatted request payload details."""
    st.markdown("#### 🚀 User Request")
    st.markdown(f"**Target Model:** `{data.get('model', 'unknown')}`")

    if "messages" in data:
        st.markdown("#### 💬 Last User Message")
        last_message = next((msg for msg in reversed(data["messages"]) if msg["role"] == "user"), None)
        if last_message:
            st.chat_message(last_message["role"]).write(last_message["content"])

    if "system" in data:
        with st.expander("📝 System Instructions", expanded=False):
            st.code(data['system'], language="markdown")
            
    if "tools" in data and data['tools']:
        with st.expander(f"🛠️ Available Tools ({len(data['tools'])})", expanded=False):
            for tool in data['tools']:
                st.markdown(f"- **{tool['function']['name']}**: {tool['function']['description']}")
                
    st.markdown("#### 💬 Conversation History")
    for msg in data.get("messages", []):
        st.chat_message(msg['role']).write(msg['content'])

def _render_response_details(data: Dict[str, Any]):
    """Renders formatted response payload details."""
    st.markdown("#### ✨ Model Response")
    
    thinking = data.get('thinking') or (data.get('message', {}).get('thinking'))
    if thinking:
        st.markdown("#### 🧠 Reasoning Chain")
        st.info(thinking)
        
    content = data.get('content') or (data.get('message', {}).get('content'))
    if content:
        st.markdown("#### 💬 Final Output")
        st.markdown(content)
        
    tool_calls = data.get('message', {}).get('tool_calls')
    if tool_calls:
        st.markdown("#### 🛠️ Generated Tool Calls")
        for tc in tool_calls:
            st.warning(f"Call: `{tc['function']['name']}`")
            st.code(tc['function']['arguments'], language="json")

def _render_tool_details(data: Any):
    """Renders formatted tool execution details."""
    st.markdown("#### 🛠️ Tool Execution")
    if isinstance(data, list):
        for call in data:
            st.warning(f"Executing: `{call['function']['name']}`")
            st.code(call['function']['arguments'], language="json")
    else:
        st.json(data)

def _render_error_details(data: Dict[str, Any]):
    """Renders formatted error details."""
    st.error("#### ❌ System Error")
    st.write(data.get('message', 'Unknown error occurred'))
    if 'traceback' in data:
        st.code(data['traceback'], language="python")

def _render_security_details(data: Dict[str, Any]):
    """Renders formatted security analysis details."""
    st.markdown("#### 🛡️ Security Analysis")
    score = data.get("risk_score", 0.0)
    target = data.get("target", "unknown")
    summary = data.get("summary", "No details")
    
    color = "red" if score > 0.8 else "orange" if score > 0.4 else "green"
    
    st.metric("Risk Score", f"{score*100:.1f}%", delta=summary, delta_color="inverse")
    st.markdown(f"**Target:** `{target}`")
    
    if score > 0.5:
        st.warning("⚠️ High risk of prompt injection detected in this segment.")
    else:
        st.success("✅ Content passed the Bayesian security filter.")
