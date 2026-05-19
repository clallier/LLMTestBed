import os
import subprocess
import sys
import time

import httpx
import pytest
from streamlit.testing.v1 import AppTest

# Internal Constants
TEST_PORT = 8001
TEST_BACKEND_URL = f"http://127.0.0.1:{TEST_PORT}"
TEST_HEALTH_URL = f"{TEST_BACKEND_URL}/health"


def _is_backend_healthy() -> bool:
    """
    Checks if the backend health endpoint is active and returning 200 OK.

    High level role: Serves as a fast status checker for the FastAPI server.

    Args:
        url (str): The absolute URL of the health check endpoint.

    Returns:
        bool: True if the backend is responsive and healthy, False otherwise.
    """
    try:
        resp = httpx.get(TEST_HEALTH_URL, timeout=1.0)
        return resp.status_code == 200
    except Exception:
        return False


def _launch_backend_subprocess(port: int) -> subprocess.Popen:
    """
    Spawns a background FastAPI server on the specified port.

    High level role: Handles the subprocess creation and environment configuration.

    Args:
        port (int): The local port number to bind the uvicorn server to.

    Returns:
        subprocess.Popen: The spawned uvicorn subprocess object.
    """
    env = os.environ.copy()
    env["E2E_TEST_MODE"] = "true"
    env["PYTHONPATH"] = os.path.pathsep.join(filter(None, ["src", env.get("PYTHONPATH", "")]))

    return subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--port",
            str(port),
            "--host",
            "127.0.0.1",
        ],
        env=env,
        cwd=os.getcwd(),
    )


@pytest.fixture(scope="module")
def live_backend():
    """Starts the FastAPI backend on port 8001 in E2E test mode if not already running."""
    if _is_backend_healthy():
        yield TEST_BACKEND_URL
        return

    proc = _launch_backend_subprocess(TEST_PORT)

    # Wait for the backend to be healthy
    start_time = time.time()
    timeout = 15
    while time.time() - start_time < timeout:
        if _is_backend_healthy():
            break
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("Failed to start live backend for E2E tests within timeout.")

    yield TEST_BACKEND_URL

    proc.terminate()
    proc.wait()


def test_full_e2e_flow(live_backend):
    """
    Verifies the full multi-turn chat, parallel tool calls, and logs integration
    using a live backend in E2E_TEST_MODE.
    """
    # Force the BACKEND_URL for the app to point to the test server
    os.environ["BACKEND_URL"] = live_backend

    # Initialize AppTest with a longer timeout for E2E
    at = AppTest.from_file("src/streamlit_app/app.py", default_timeout=30).run()

    # Verify Header
    assert at.header[0].value == "Agent Attack Sandbox"

    # 1. Verify Model Selection (fetching from real backend in test mode)
    # The sidebar model selectbox should have the mock model
    assert at.sidebar.selectbox[0].value == "e2e-mock-model"

    # 2. Trigger a Chat Interaction
    chat_input = at.chat_input[0]
    chat_input.set_value("Test Message").run(timeout=30)

    # 3. Verify Response and Multi-turn state
    # We should have 3 messages: user, tools, and assistant
    assert len(at.session_state["messages"]) == 3
    assert at.session_state["messages"][0]["content"] == "Test Message"
    assert at.session_state["messages"][1]["role"] == "tools"
    assert at.session_state["messages"][2]["role"] == "assistant"
    assert "result of the test" in at.session_state["messages"][2]["content"]

    # Verify raw standard protocol history tracking
    raw_msgs = at.session_state["raw_messages"]
    assert len(raw_msgs) == 5
    assert raw_msgs[0]["role"] == "user"
    assert raw_msgs[0]["content"] == "Test Message"
    assert raw_msgs[1]["role"] == "assistant"
    assert len(raw_msgs[1]["tool_calls"]) == 2
    assert raw_msgs[2]["role"] == "tool"
    assert raw_msgs[3]["role"] == "tool"
    assert {raw_msgs[2]["name"], raw_msgs[3]["name"]} == {"read_sensitive_file", "execute_command"}

    # Verify that each tool reply has the correct tool_call_id matching its tool call
    tool_calls = {tc["function"]["name"]: tc["id"] for tc in raw_msgs[1]["tool_calls"]}
    assert raw_msgs[2]["tool_call_id"] == tool_calls[raw_msgs[2]["name"]]
    assert raw_msgs[3]["tool_call_id"] == tool_calls[raw_msgs[3]["name"]]
    assert raw_msgs[4]["role"] == "assistant"
    assert "result of the test" in raw_msgs[4]["content"]

    # 4. Verify Observability Logs (including parallel tools)
    logs = at.session_state["logs"]

    # We expect: REQUEST, TOOL (with 2 calls), TOOL_RESPONSEs, and RESPONSE
    log_types = [log["type"] for log in logs]
    assert "REQUEST" in log_types
    assert "TOOL" in log_types
    assert "TOOL_RESPONSE" in log_types
    assert "RESPONSE" in log_types

    # Verify isolated RESPONSE log content (no intermediate tool executions)
    response_log = next(log for log in logs if log["type"] == "RESPONSE")
    response_content = response_log["data"]["content"]
    assert "result of the test" in response_content
    assert "Tool Call" not in response_content
    assert "Tool Response" not in response_content

    # Verify Parallel Tool Calls data
    tool_log = next(log for log in logs if log["type"] == "TOOL")
    assert len(tool_log["data"]) == 2
    assert tool_log["data"][0]["function"]["name"] == "read_sensitive_file"
    assert tool_log["data"][1]["function"]["name"] == "execute_command"

    # Verify Parallel Tool Response data
    tool_response_logs = [log for log in logs if log["type"] == "TOOL_RESPONSE"]
    assert len(tool_response_logs) == 2
    tool_response_names = {log["data"]["name"] for log in tool_response_logs}
    assert "read_sensitive_file" in tool_response_names
    assert "execute_command" in tool_response_names

    # 5. Verify Hub rendering (Switch View via Top Nav Segmented Control)
    at.segmented_control(key="top_nav").set_value("Observability").run(timeout=30)

    # The Sandbox header should be gone
    assert not any("Attack Sandbox" in h.value for h in at.header)

    # The Trace Explorer title should be present
    all_text = [t.value for t in at.title] + [m.value for m in at.markdown]
    assert any("Trace Explorer" in val for val in all_text)

    # 6. Verify Export Function and Dataset Completeness
    # Since a log is selected by default on load, the download button is rendered automatically.

    # Verify download button is rendered
    download_buttons = at.get("download_button")
    assert len(download_buttons) == 1

    # Use the ObservabilityProcessor format payload utility to verify export string completeness
    from streamlit_app.components.processors.observability import ObservabilityProcessor

    export_str = ObservabilityProcessor().format_export_payload(at.session_state["raw_messages"])

    import json

    export_data = json.loads(export_str)

    # Verify export dataset completeness (all turns, tools, and roles are fully logged)
    assert "conversation_history" in export_data
    messages = export_data["conversation_history"]

    # We must have all 5 history turns recorded: user, assistant tool calls, 2 tool replies, assistant final response
    assert len(messages) == 5
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Test Message"

    assert messages[1]["role"] == "assistant"
    assert len(messages[1]["tool_calls"]) == 2
    assert messages[1]["tool_calls"][0]["function"]["name"] == "read_sensitive_file"
    assert messages[1]["tool_calls"][1]["function"]["name"] == "execute_command"

    assert messages[2]["role"] == "tool"
    assert messages[3]["role"] == "tool"
    assert {messages[2]["name"], messages[3]["name"]} == {"read_sensitive_file", "execute_command"}

    # Verify that each exported tool reply has the correct tool_call_id matching its tool call
    exported_tool_calls = {tc["function"]["name"]: tc["id"] for tc in messages[1]["tool_calls"]}
    assert messages[2]["tool_call_id"] == exported_tool_calls[messages[2]["name"]]
    assert messages[3]["tool_call_id"] == exported_tool_calls[messages[3]["name"]]

    assert messages[4]["role"] == "assistant"
    assert "result of the test" in messages[4]["content"]
