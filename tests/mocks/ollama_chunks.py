import json

MOCK_CHUNKS_NORMAL = [
    json.dumps({"message": {"role": "assistant", "content": "Hello"}}) + "\n",
    json.dumps({"message": {"role": "assistant", "content": " world!"}}) + "\n"
]

MOCK_CHUNKS_MALFORMED = [
    json.dumps({"message": {"role": "assistant", "content": "Hello"}}) + "\n",
    "THIS IS NOT VALID JSON\n",
    json.dumps({"message": {"role": "assistant", "content": " world!"}}) + "\n"
]
