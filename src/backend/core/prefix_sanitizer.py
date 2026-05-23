"""Garbage prefix detection and sanitization for raw model completions.

High level role: Strips stray JSON delimiters and leaked tool-call blocks
from the leading edge of assistant text. All functions are pure and synchronous.
"""

from typing import Any

import json_repair


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


def _check_list_tool_call(data: Any) -> bool:
    """Checks if a parsed list represents a tool call structure."""
    if not isinstance(data, list) or not data:
        return False
    item = data[0]
    return isinstance(item, dict) and (
        "function" in item or ("name" in item and "arguments" in item)
    )


def _check_dict_tool_call(data: Any) -> bool:
    """Checks if a parsed dict represents a tool call structure."""
    if not isinstance(data, dict):
        return False
    if "tool_calls" in data and isinstance(data["tool_calls"], list):
        if data["tool_calls"]:
            item = data["tool_calls"][0]
            return isinstance(item, dict) and ("function" in item or "name" in item)
        return True
    if "function" in data and isinstance(data["function"], dict) and "name" in data["function"]:
        return True
    return "name" in data and "arguments" in data


def _is_tool_call(block: str) -> bool:
    """Checks if a JSON block string represents a tool call structure.

    High level role: Identifies tool call patterns in JSON blocks.
    Description: Parses block using json-repair and checks if it matches agent tool signatures.
    How it works:
    - Attempts to parse the block using json_repair.loads.
    - Delegates checks to dedicated list/dict helper functions.

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
        data = json_repair.loads(block)
        return _check_list_tool_call(data) or _check_dict_tool_call(data)
    except Exception:
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
        text = text.lstrip('}"]:,; \n\r\t')
        if text.startswith("{") or text.startswith("["):
            end_idx = _find_matching_brace(text, 0)
            if end_idx != -1:
                block = text[: end_idx + 1]
                remaining = text[end_idx + 1 :].strip()
                if remaining or _is_tool_call(block):
                    text = text[end_idx + 1 :]
    return text
