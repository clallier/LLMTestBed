import json

# Standard mock security chunks for tests
MOCK_SECURITY_SAFE = {
    "security": {
        "risk_score": 0.15,
        "target": "user_prompt",
        "value": "Safe"
    }
}

MOCK_SECURITY_HIGH_RISK = {
    "security": {
        "risk_score": 0.95,
        "target": "tool_read_file",
        "value": "High risk tool output"
    }
}

MOCK_CHUNKS_NORMAL = [
    json.dumps(MOCK_SECURITY_SAFE) + "\n",
    json.dumps({"message": {"role": "assistant", "content": "Hello"}}) + "\n",
    json.dumps({"message": {"role": "assistant", "content": " world!"}}) + "\n"
]

MOCK_CHUNKS_MALFORMED = [
    json.dumps(MOCK_SECURITY_SAFE) + "\n",
    json.dumps({"message": {"role": "assistant", "content": "Hello"}}) + "\n",
    "THIS IS NOT VALID JSON\n",
    json.dumps({"message": {"role": "assistant", "content": " world!"}}) + "\n"
]
