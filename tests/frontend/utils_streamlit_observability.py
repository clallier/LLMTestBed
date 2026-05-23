"""
Isolated Streamlit AppTest helper wrappers for Observability component testing.

High level role: Contains isolated functions called by AppTest context to test rendering
of different security traces and conversation histories.
"""


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
        "data": {"risk_score": 0.45, "target": "tool_execute_shell_command", "value": "Safe"},
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
        "data": {"risk_score": 0.95, "target": "user_prompt", "value": "High risk prompt"},
    }
    render_formatted_detail(log)


def run_observability_conversation_history():
    """
    Wrapper function to test rendering of a request log containing structured conversation history.

    High level role: Simulates rendering of conversation history.

    Arguments:
        None

    Returns:
        None
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
                        {"function": {"name": "execute_shell_command", "arguments": {"command": "ls"}}}
                    ],
                },
                {"role": "tool", "name": "execute_shell_command", "content": "file1.txt\nfile2.txt"},
                {"role": "assistant", "content": "Here is the list of files."},
            ],
        },
    }
    render_formatted_detail(log)
