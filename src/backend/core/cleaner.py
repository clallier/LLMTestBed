"""Stream output cleaning and syntax parsing operations.

High level role: Handles garbage prefix parsing and syntax sanitization for assistant stream blocks.
"""
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional

logger = logging.getLogger(__name__)


def _find_matching_brace(text: str, start_idx: int) -> int:
    """Finds the index of the matching closing bracket/brace for nested structures.

    High level role: Tracks parentheses depth.
    Description: Scans the input text from start_idx tracking nesting depth.
    How it works: Iterates through characters and handles double quotes and
    escaped characters to correctly find the matching closing bracket or brace.

    Args:
        text (str): The target string to search.
        start_idx (int): The 0-based index of the opening bracket or brace.

    Returns:
        int: The index of the matching closing bracket or brace, or -1 if none.

    Raises:
        IndexError: If start_idx is out of range.

    Examples:
        >>> _find_matching_brace("[{}]", 0)
        3
    """
    open_c = text[start_idx]
    close_c = "}" if open_c == "{" else "]"
    depth, in_str, escaped = 0, False, False
    for idx, char in enumerate(text[start_idx:], start_idx):
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            in_str = not in_str
        elif not in_str:
            depth += 1 if char == open_c else -1 if char == close_c else 0
            if depth == 0:
                return idx
    return -1


def _is_tool_call(block: str) -> bool:
    """Checks if a JSON block string represents a tool call structure.

    High level role: Identifies tool call patterns in JSON blocks.
    Description: Parses block and checks if it matches agent tool signatures.
    How it works:
    - Attempts to parse the block as JSON.
    - If it's a list, checks if the first element contains "function", "name", and "arguments".
    - If it's a dict, checks for keys like "tool_calls", "function", or "arguments".

    Args:
        block (str): The raw JSON block to inspect.

    Returns:
        bool: True if block represents a tool call, False otherwise.

    Raises:
        None

    Examples:
        >>> _is_tool_call('[{"function": {"name": "get_env"}}]')
        True
    """
    try:
        data = json.loads(block)
        if isinstance(data, list) and data:
            item = data[0]
            return isinstance(item, dict) and (
                "function" in item or ("name" in item and "arguments" in item)
            )
        if isinstance(data, dict):
            if "tool_calls" in data:
                return True
            if "function" in data and isinstance(data["function"], dict) and "name" in data["function"]:
                return True
            return "name" in data and "arguments" in data
    except json.JSONDecodeError:
        pass
    return False


def clean_garbage_prefix(text: str) -> str:
    """Strips stray unclosed JSON delimiters and mock tool calls from the assistant response.

    High level role: Sanitizes model completions by cleaning raw syntax leaks.
    Description: Recursively removes leading garbage characters and nested JSON
    blocks corresponding to unclosed tool calls.
    How it works:
    - Strips leading syntax characters like "}", "]", ";", ",", ":", etc.
    - If the remaining text starts with "{" or "[", locates the matching closing brace.
    - Recursively slices the matched prefix until no further tool calls are found.

    Args:
        text (str): The raw string to sanitize.

    Returns:
        str: The cleaned conversation output.

    Raises:
        None

    Examples:
        >>> clean_garbage_prefix('"}; [{"name": "get_env"}]Here is the key')
        'Here is the key'
    """
    last_len = -1
    while text and len(text) != last_len:
        last_len = len(text)
        text = text.lstrip("}\"]:,; \n\r\t")
        if text.startswith("{") or text.startswith("["):
            end_idx = _find_matching_brace(text, 0)
            if end_idx != -1:
                block = text[:end_idx + 1]
                remaining = text[end_idx + 1:].strip()
                if remaining or _is_tool_call(block):
                    text = text[end_idx + 1:]
    return text


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


def parse_chunk(chunk_str: str) -> Optional[Dict[str, Any]]:
    """Parses a raw NDJSON chunk from Ollama.

    High level role: Safe NDJSON parser.
    Description: Parses single JSON chunk line, logging errors on failure.
    How it works: Decodes JSON string, catching decode exceptions.

    Args:
        chunk_str (str): The raw chunk string.

    Returns:
        Optional[Dict[str, Any]]: Parsed dictionary if successful, None otherwise.

    Raises:
        None

    Examples:
        >>> parse_chunk('{"message": {"role": "user"}}')
        {'message': {'role': 'user'}}
    """
    try:
        return json.loads(chunk_str)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON chunk: %s", chunk_str)
        return None


async def clean_chunks_stream(
    raw_stream: AsyncGenerator[str, None],
    assistant_msg: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """Filters out malformed JSON prefixes and garbage tool calls from text chunks.

    High level role: Stateful stream cleaning generator.
    Description: Buffers raw completion text chunks, strips stray prefixes and
    unclosed delimiters, and streams clean text chunks.
    How it works:
    - Buffers up to 200 characters of content.
    - Cleans the buffer using clean_garbage_prefix.
    - Streams the cleaned prefix followed by subsequent raw chunks immediately.

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
    buf, ok = "", False
    async for chunk in raw_stream:
        data = parse_chunk(chunk)
        val = data.get("message", {}).get("content", "") if data else ""
        if val:
            buf += val
            if ok:
                yield chunk
            elif ((cln := clean_garbage_prefix(buf)) and not cln[0].isspace() and cln[0] not in "{}[];,:") or len(buf) >= 200:
                yield format_clean_chunk(cln)
                ok = True
        else:
            if not ok and buf:
                yield format_clean_chunk(clean_garbage_prefix(buf))
                ok = True
            yield chunk
    if not ok and buf:
        yield format_clean_chunk(clean_garbage_prefix(buf))
    assistant_msg["content"] = clean_garbage_prefix(assistant_msg["content"])
