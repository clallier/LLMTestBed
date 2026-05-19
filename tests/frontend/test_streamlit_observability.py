import json

from streamlit.testing.v1 import AppTest

from streamlit_app.components.observability import render_formatted_detail


def run_observability_safe():
    """
    Wrapper function to test isolated observability safe security trace rendering.

    High level role: Simulates rendering of a safe security trace in Streamlit.

    Arguments:
        None

    Returns:
        None
    """
    from streamlit_app.components.observability import render_formatted_detail

    log = {
        "time": "12:00:00",
        "type": "SECURITY",
        "data": {"risk_score": 0.45, "target": "tool_execute_command", "summary": "Safe"},
    }
    render_formatted_detail(log)


def run_observability_unsafe():
    """
    Wrapper function to test isolated observability high-risk security trace rendering.

    High level role: Simulates rendering of a high-risk security trace in Streamlit.

    Arguments:
        None

    Returns:
        None
    """
    from streamlit_app.components.observability import render_formatted_detail

    log = {
        "time": "12:00:00",
        "type": "SECURITY",
        "data": {"risk_score": 0.95, "target": "user_prompt", "summary": "High risk prompt"},
    }
    render_formatted_detail(log)


def test_observability_safe_rendering():
    """
    Verifies that the safe security trace renders correctly.

    High level role: Guarantees correct rendering of the safety metrics and status badge
    for low-risk security traces without metric delta arrows.

    Arguments:
        None

    Returns:
        None

    Raises:
        AssertionError: If any UI element fails to render or has incorrect values.
    """
    at = AppTest.from_function(run_observability_safe).run()
    assert not at.exception

    # Assert metric risk score is 45.0%
    assert at.metric[0].value == "45.0%"
    assert at.metric[0].label == "Risk Score"
    assert not at.metric[0].delta  # Support both None and "" (empty string)

    # Assert Markdown contains Security Analysis header
    assert any("🛡️ Security Analysis" in md.value for md in at.markdown)

    # Assert Status markdown contains green Safe badge
    assert any(":green[Safe]" in md.value for md in at.markdown)

    # Assert success callout is rendered
    assert len(at.success) == 1
    assert "Content passed the Bayesian security filter" in at.success[0].value


def test_observability_unsafe_rendering():
    """
    Verifies that the high-risk security trace renders correctly.

    High level role: Guarantees correct rendering of the safety metrics and status badge
    for high-risk security traces without metric delta arrows.

    Arguments:
        None

    Returns:
        None

    Raises:
        AssertionError: If any UI element fails to render or has incorrect values.
    """
    at = AppTest.from_function(run_observability_unsafe).run()
    assert not at.exception

    # Assert metric risk score is 95.0%
    assert at.metric[0].value == "95.0%"
    assert at.metric[0].label == "Risk Score"
    assert not at.metric[0].delta  # Support both None and "" (empty string)

    # Assert Status markdown contains red High Risk badge
    assert any(":red[High risk prompt]" in md.value for md in at.markdown)

    # Assert warning callout is rendered
    assert len(at.warning) == 1
    assert "High risk of prompt injection detected" in at.warning[0].value


def run_observability_conversation_history():
    """
    Wrapper function to test rendering of a request log containing structured conversation history.
    """
    from streamlit_app.components.observability import render_formatted_detail

    log = {
        "time": "12:00:00",
        "type": "REQUEST",
        "data": {
            "model": "gemma",
            "messages": [
                {"role": "user", "content": "execute command ls"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"function": {"name": "execute_command", "arguments": {"command": "ls"}}}
                    ],
                },
                {"role": "tool", "name": "execute_command", "content": "file1.txt\nfile2.txt"},
                {"role": "assistant", "content": "Here is the list of files."},
            ],
        },
    }
    render_formatted_detail(log)


def test_observability_conversation_history_rendering():
    """
    Verifies that the conversation history under REQUEST traces renders tool calls,
    tool responses, and assistant content correctly without leaving empty blank bubbles.
    """
    at = AppTest.from_function(run_observability_conversation_history).run()
    assert not at.exception

    # Verify that 'Generated Tool Calls:' is rendered for tool calls
    assert any("Generated Tool Calls:" in md.value for md in at.markdown)

    # Verify that python representation of the tool call is inside a code block
    assert any("execute_command" in code.value for code in at.code)

    # Verify that tool response output is correctly formatted in a code block
    assert any("file1.txt" in code.value for code in at.code)

    # Verify that the final assistant output is displayed
    assert any("Here is the list of files." in md.value for md in at.markdown)


def test_observability_processor_export():
    """Verifies that format_export_payload serializes keys and pretty-prints JSON."""
    from streamlit_app.components.processors.observability import ObservabilityProcessor

    proc = ObservabilityProcessor()
    log = {"time": "10:15:00", "type": "TEST", "data": {"key": "val"}}

    export_str = proc.format_export_payload(log)
    parsed = json.loads(export_str)

    assert parsed["timestamp"] == "10:15:00"
    assert parsed["type"] == "TEST"
    assert parsed["data"]["key"] == "val"


def test_observability_processor_security_status():
    """Verifies that risk scores and labels yield appropriate badge categories."""

    from streamlit_app.components.processors.observability import ObservabilityProcessor

    proc = ObservabilityProcessor()

    # 1. Safe status
    score_p, summary, badge = proc.get_security_status(
        {"risk_score": 0.12, "summary": "Safe content"}
    )
    assert score_p == 12.0
    assert summary == "Safe content"
    assert badge == "green"

    # 2. Unsafe (High Risk) status
    score_p, summary, badge = proc.get_security_status(
        {"risk_score": 0.85, "summary": "Prompt Injection Attempt"}
    )
    assert score_p == 85.0
    assert badge == "red"

    # 3. Neutral status
    score_p, summary, badge = proc.get_security_status(
        {"risk_score": 0.40, "summary": "Neutral content"}
    )
    assert score_p == 40.0
    assert badge == "orange"


def test_observability_processor_arguments_formatting():
    """Verifies format_tool_arguments handles strings and nested dictionary serialization."""
    from streamlit_app.components.processors.observability import ObservabilityProcessor

    proc = ObservabilityProcessor()

    # Nested Dict arguments
    args_dict = {"param1": 100, "param2": "text"}
    formatted = proc.format_tool_arguments(args_dict)
    assert "param1" in formatted
    assert "100" in formatted

    # String arguments
    formatted_str = proc.format_tool_arguments("raw_string")
    assert formatted_str == "raw_string"
