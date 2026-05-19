"""
Mock test data chunks for Ollama Client E2E simulations.

High level role: Defines choreographed assistant responses, reasoning logs,
and mock parallel tool execution blocks for automated flow verification.
"""
from typing import Any, Dict, List

TEST_CHUNKS_FIRST_TURN: List[Dict[str, Any]] = [
    {
        "message": {
            "role": "assistant",
            "thinking": "Starting test reasoning..."
        }
    },
    {
        "message": {
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call_read_file",
                    "function": {
                        "name": "read_sensitive_file",
                        "arguments": '{"filename": ".env"}'
                    }
                },
                {
                    "id": "call_exec_cmd",
                    "function": {
                        "name": "execute_command",
                        "arguments": '{"command": "ls"}'
                    }
                }
            ]
        }
    },
    {"done": False}
]

TEST_CHUNKS_SECOND_TURN: List[Dict[str, Any]] = [
    {
        "message": {
            "role": "assistant",
            "content": "Here is the result of the test after tool execution."
        }
    },
    {"done": True}
]
