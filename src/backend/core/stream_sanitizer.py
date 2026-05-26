"""Async NDJSON stream parsing and chunk sanitization.

High level role: Consumes raw Ollama NDJSON streams, parses individual chunks,
and delegates prefix cleaning to prefix_sanitizer before yielding clean output.
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

import json_repair

from backend.core.prefix_sanitizer import clean_garbage_prefix

logger = logging.getLogger(__name__)


def parse_chunk(chunk_str: str) -> Optional[Dict[str, Any]]:
    """Parses a raw NDJSON chunk from Ollama.

    High level role: Safe NDJSON parser.
    Description: Parses single JSON chunk line using json-repair, logging errors on failure.
    How it works: Decodes JSON string via json_repair.loads, returning a dictionary if successful.

    Args:
        chunk_str (str): The raw chunk string.

    Returns:
        Optional[Dict[str, Any]]: Parsed dictionary if successful, None otherwise.

    Raises:
        None

    Examples:
        >>> parse_chunk('{"message": {"role": "user"')
        {'message': {'role': 'user'}}
    """
    if not chunk_str or not chunk_str.strip():
        return None
    try:
        data = json_repair.loads(chunk_str)
        if isinstance(data, dict):
            return data
        logger.error("Failed to parse JSON chunk: %s", chunk_str)
        return None
    except Exception:
        logger.error("Failed to parse JSON chunk: %s", chunk_str)
        return None


def format_clean_chunk(content: str) -> str:
    """Formats a clean assistant message content string as an NDJSON stream line.

    High level role: Standardizes message chunk construction.
    Description: Packages a clean string into an Ollama-compliant message chunk.
    How it works: Serializes a dictionary with message role and content.

    Args:
        content (str): The cleaned text content.

    Returns:
        str: The serialized JSON chunk followed by a newline.

    Raises:
        None

    Examples:
        >>> format_clean_chunk("hello")
        '{"message": {"role": "assistant", "content": "hello"}}\\n'
    """
    return json.dumps({"message": {"role": "assistant", "content": content}}) + "\n"


class StreamBufferCleaner:
    """Stateful buffer cleaner for raw assistant stream prefixes.

    High level role: Manages stateful buffering and garbage prefix stripping.
    Description: Buffers incoming text chunks and determines when the prefix has
    been cleanly passed, stripping unclosed or malformed tool call syntax.
    How it works:
    - Appends text to an internal buffer.
    - Applies clean_garbage_prefix to determine if the text is clean.
    - Signals triggering when the text meets non-delimiter or size criteria.
    """

    def __init__(self) -> None:
        """Initializes the cleaner with empty buffer and inactive ok flag."""
        self.buf = ""
        self.ok = False

    def process_content(self, val: str) -> Optional[str]:
        """Appends new text content and checks if cleaning can be triggered.

        Args:
            val (str): The raw incoming text value.

        Returns:
            Optional[str]: Cleaned prefix string if triggered, None otherwise.
        """
        if self.ok:
            return None
        self.buf += val
        cln = clean_garbage_prefix(self.buf)
        if (
            (cln and not cln[0].isspace() and cln[0] not in "{}[];,:")
            or len(self.buf) >= 200
        ):
            self.ok = True
            return cln
        return None

    def finalize(self) -> Optional[str]:
        """Finalizes buffer cleaning if it was never triggered.

        Returns:
            Optional[str]: Cleaned remaining buffer text if any, None otherwise.
        """
        if not self.ok and self.buf:
            self.ok = True
            return clean_garbage_prefix(self.buf)
        return None


async def clean_chunks_stream(
    raw_stream: AsyncGenerator[str, None], assistant_msg: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """Filters out malformed JSON prefixes and garbage tool calls from text chunks.

    High level role: Stateful stream cleaning generator.
    Description: Buffers raw completion text chunks, strips stray prefixes and
    unclosed delimiters via prefix_sanitizer, and streams clean text chunks.
    How it works:
    - Delegates stateful buffering to StreamBufferCleaner.
    - Yields clean chunks as they stream immediately after prefix triggering.

    Args:
        raw_stream (AsyncGenerator[str, None]): The raw NDJSON stream.
        assistant_msg (Dict[str, Any]): Mutable assistant message.

    Yields:
        str: Cleaned stream chunks.

    Raises:
        None

    Examples:
        >>> async for chunk in clean_chunks_stream(raw, msg):
        ...     print(chunk)
    """
    cleaner = StreamBufferCleaner()
    async for chunk in raw_stream:
        data = parse_chunk(chunk)
        val = data.get("message", {}).get("content", "") if data else ""
        if val:
            if cleaner.ok:
                yield chunk
            elif (cln := cleaner.process_content(val)) is not None:
                yield format_clean_chunk(cln)
        else:
            if (fln := cleaner.finalize()) is not None:
                yield format_clean_chunk(fln)
            yield chunk

    if (fln := cleaner.finalize()) is not None:
        yield format_clean_chunk(fln)
    assistant_msg["content"] = clean_garbage_prefix(assistant_msg["content"])


