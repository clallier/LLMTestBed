"""Unit tests for the prefix_sanitizer module.

High level role: Validates brace matching, tool-call detection, and
garbage-prefix stripping for raw assistant completions.
"""

from backend.core.prefix_sanitizer import (
    _find_matching_brace,
    _is_tool_call,
    clean_garbage_prefix,
)


def test_find_matching_brace():
    """Validates locate matching bracket/brace index in nested text strings.

    Description: Exercises the _find_matching_brace function under various bounds
    and escaping conditions to verify correct boundary index detection.
    """
    assert _find_matching_brace("[{}]", 0) == 3
    assert _find_matching_brace("{a: {b: 2}}", 0) == 10
    assert _find_matching_brace('{"a": "he said \\"hi\\""}', 0) == 22
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

    # Partial structures without a valid list or structure are not classified as tool calls
    partial_tool_call = '{"tool_calls": '
    assert _is_tool_call(partial_tool_call) is False

    # Malformed tool calls with trailing commas or single quotes are robustly supported if they form a list
    malformed_tool_call = "{'tool_calls': [{'name': 'get_env',}],"
    assert _is_tool_call(malformed_tool_call) is True

    # But non-tool-call partial/malformed JSON is correctly classified as False
    partial_normal = '{"user": '
    assert _is_tool_call(partial_normal) is False


def test_clean_garbage_prefix():
    """Validates the clean_garbage_prefix utility under different stray variants.

    Description: Assures correct removal of JSON debris and mock tool blocks
    while leaving genuine response texts untouched.
    """
    assert clean_garbage_prefix('"}; [{"name": "get_env"}]Here') == "Here"
    assert clean_garbage_prefix('; }, {"name": "test"}Hello') == "Hello"
    assert clean_garbage_prefix("No prefix at all") == "No prefix at all"
    assert clean_garbage_prefix('{"env_vars": "..."}') == '{"env_vars": "..."}'
    assert clean_garbage_prefix('[{"key": "value"}]') == '[{"key": "value"}]'

    # Malformed garbage tool calls (e.g. trailing comma) are now successfully stripped
    assert clean_garbage_prefix('; }, {"name": "get_env",}Hello') == "Hello"
    assert clean_garbage_prefix('; }, {"name": "get_env", "arguments": {"a": 1,},}Hello') == "Hello"
