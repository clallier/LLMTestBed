"""Unit tests for the standalone cleaner utility functions.

High level role: Validates syntax parsing, prefix sanitation, and NDJSON streaming filters.
"""
import json
from typing import Any, AsyncGenerator, Dict

import pytest

from backend.core.cleaner import (
    _find_matching_brace,
    _is_tool_call,
    clean_chunks_stream,
    clean_garbage_prefix,
    format_clean_chunk,
    parse_chunk,
)


def test_find_matching_brace():
    """Validates locate matching bracket/brace index in nested text strings.

    Description: Exercises the _find_matching_brace function under various bounds
    and escaping conditions to verify correct boundary index detection.
    """
    assert _find_matching_brace("[{}]", 0) == 3
    assert _find_matching_brace("{a: {b: 2}}", 0) == 10
    assert _find_matching_brace('{"a": "\\""}', 0) == 10
    assert _find_matching_brace("{a", 0) == -1
    assert _find_matching_brace("[a", 0) == -1


def test_is_tool_call():
    """Validates detecting agent structured tool signatures from JSON blocks.

    Description: Tests _is_tool_call helper against actual tool structures
    and normal user conversational JSON blocks.
    """
    tc_list = '[{"function": {"name": "get_env", "arguments": {}}}]'
    assert _is_tool_call(tc_list) is True

    tc_dict = '{"tool_calls": [{"name": "read_file"}]}'
    assert _is_tool_call(tc_dict) is True

    tc_direct = '{"function": {"name": "read_file"}}'
    assert _is_tool_call(tc_direct) is True

    tc_args = '{"name": "get_env", "arguments": {}}'
    assert _is_tool_call(tc_args) is True

    normal_json = '{"user": "Roger", "content": "Hello"}'
    assert _is_tool_call(normal_json) is False

    invalid_json = '{"tool_calls": '
    assert _is_tool_call(invalid_json) is False


def test_clean_garbage_prefix():
    """Validates the clean_garbage_prefix utility under different stray variants.

    Description: Assures correct removal of JSON debris and mock tool blocks
    while leaving genuine response texts untouched.
    """
    assert clean_garbage_prefix('"}; [{"name": "get_env"}]Here') == "Here"
    assert clean_garbage_prefix('; }, {"name": "test"}Hello') == "Hello"
    assert clean_garbage_prefix('No prefix at all') == "No prefix at all"
    assert clean_garbage_prefix('{"env_vars": "..."}') == '{"env_vars": "..."}'
    assert clean_garbage_prefix('[{"key": "value"}]') == '[{"key": "value"}]'


def test_format_clean_chunk():
    """Validates formatting clean assistant content as NDJSON message lines.

    Description: Ensures formatting outputs are standard NDJSON compliant strings.
    """
    chunk = format_clean_chunk("hello")
    data = json.loads(chunk.strip())
    assert data["message"]["role"] == "assistant"
    assert data["message"]["content"] == "hello"


def test_parse_chunk():
    """Validates parsing NDJSON line chunks from Ollama chat stream.

    Description: Verifies decoding nominal payloads and handling decode failures.
    """
    assert parse_chunk('{"a": 1}') == {"a": 1}
    assert parse_chunk("INVALID JSON") is None


@pytest.mark.asyncio
async def test_clean_chunks_stream():
    """Validates streaming output filtering and text prefix sanitation.

    Description: Pumps raw lines into the async clean_chunks_stream filter
    and asserts cleaned outputs are generated.
    """
    async def raw_stream() -> AsyncGenerator[str, None]:
        chunks = [
            json.dumps({"message": {"role": "assistant", "content": '"}; [{"name": '}}),
            json.dumps({"message": {"role": "assistant", "content": '"get_env"}]Hello '}}),
            json.dumps({"message": {"role": "assistant", "content": "world"}}),
        ]
        for chunk in chunks:
            yield chunk

    assistant_msg: Dict[str, Any] = {"role": "assistant", "content": '"}; [{"name": "get_env"}]Hello world'}
    output_chunks = []
    async for chunk in clean_chunks_stream(raw_stream(), assistant_msg):
        output_chunks.append(json.loads(chunk.strip()))

    content = "".join(c["message"]["content"] for c in output_chunks if "message" in c)
    assert "Hello world" in content
    assert "get_env" not in content
    assert assistant_msg["content"] == "Hello world"
