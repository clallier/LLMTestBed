"""Unit tests for the stream_sanitizer module.

High level role: Validates NDJSON chunk parsing, chunk formatting, and the
async stream-cleaning generator that delegates prefix work to prefix_sanitizer.
"""

import json
from typing import Any, AsyncGenerator, Dict

import pytest

from backend.core.stream_sanitizer import (
    clean_chunks_stream,
    format_clean_chunk,
    parse_chunk,
)


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

    # Robustness against malformed or partial chunk JSON via json-repair
    assert parse_chunk('{"message": {"role": "assistant"') == {"message": {"role": "assistant"}}
    assert parse_chunk('{"message": {"content": "hello",}}') == {"message": {"content": "hello"}}
    assert parse_chunk('{message: {content: "hello"}}') == {"message": {"content": "hello"}}


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

    assistant_msg: Dict[str, Any] = {
        "role": "assistant",
        "content": '"}; [{"name": "get_env"}]Hello world',
    }
    output_chunks = []
    async for chunk in clean_chunks_stream(raw_stream(), assistant_msg):
        output_chunks.append(json.loads(chunk.strip()))

    content = "".join(c["message"]["content"] for c in output_chunks if "message" in c)
    assert "Hello world" in content
    assert "get_env" not in content
    assert assistant_msg["content"] == "Hello world"

