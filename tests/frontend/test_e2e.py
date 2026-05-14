import pytest
import subprocess
import time
import httpx
import os
from streamlit.testing.v1 import AppTest

@pytest.fixture(scope="module")
def live_backend():
    """Starts the FastAPI backend on port 8001 in E2E test mode."""
    env = os.environ.copy()
    env["E2E_TEST_MODE"] = "true"
    env["PYTHONPATH"] = "src" # Ensure src is in pythonpath for the subprocess
    
    # Start the server using uvicorn directly to ensure it works
    proc = subprocess.Popen(
        ["uv", "run", "uvicorn", "backend.main:app", "--port", "8001", "--host", "127.0.0.1"],
        env=env,
        cwd=os.getcwd()
    )
    
    # Wait for the backend to be healthy
    health_url = "http://localhost:8001/health"
    start_time = time.time()
    timeout = 15
    while time.time() - start_time < timeout:
        try:
            resp = httpx.get(health_url)
            if resp.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        proc.terminate()
        raise RuntimeError("Failed to start live backend for E2E tests within timeout.")
    
    yield "http://localhost:8001"
    
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
    
    # Verify Branding/Header
    assert any("🛡️ LLMTestbed" in md.value for md in at.markdown)
    assert at.header[0].value == "🕵️ Agent Attack Sandbox"
    
    # 1. Verify Model Selection (fetching from real backend in test mode)
    # The sidebar model selectbox should have the mock model
    assert at.sidebar.selectbox[0].value == "e2e-mock-model"
    
    # 2. Trigger a Chat Interaction
    chat_input = at.chat_input[0]
    chat_input.set_value("Test Message").run(timeout=30)
    
    # 3. Verify Response and Multi-turn state
    # We should have 2 messages: user and assistant
    assert len(at.session_state["messages"]) == 2
    assert at.session_state["messages"][0]["content"] == "Test Message"
    assert "result of the test" in at.session_state["messages"][1]["content"]
    
    # 4. Verify Observability Logs (including parallel tools)
    logs = at.session_state["logs"]
    
    # We expect: 1 REQUEST, 1 TOOL (with 2 calls), 1 RESPONSE
    log_types = [log["type"] for log in logs]
    assert "REQUEST" in log_types
    assert "TOOL" in log_types
    assert "RESPONSE" in log_types
    
    # Verify Parallel Tool Calls data
    tool_log = next(log for log in logs if log["type"] == "TOOL")
    assert len(tool_log["data"]) == 2
    assert tool_log["data"][0]["function"]["name"] == "read_sensitive_file"
    assert tool_log["data"][1]["function"]["name"] == "execute_command"
    
    # 5. Verify Hub rendering (Switch View via Top Nav Segmented Control)
    at.segmented_control(key="top_nav").set_value("Observability").run(timeout=30)
    
    # The Sandbox header should be gone
    assert not any("Attack Sandbox" in h.value for h in at.header)
    
    # The Observability title should be present
    all_text = [t.value for t in at.title] + [m.value for m in at.markdown]
    assert any("Observability" in val for val in all_text)
