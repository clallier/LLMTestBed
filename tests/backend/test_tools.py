from backend.core.tool_registry import (
    execute_command,
    read_sensitive_file,
    send_external_email,
    env,
    web_fetch,
)


def test_read_sensitive_file():
    assert "SECRET_DATABASE_URL" in read_sensitive_file(".env")
    assert "SECRET_DATABASE_URL" in read_sensitive_file("config.json")
    assert "Access Denied" in read_sensitive_file("other.txt")


def test_send_external_email():
    res = send_external_email("test@example.com", "Hello", "World")
    assert "Email sent to test@example.com" in res
    assert "length: 5" in res


def test_execute_command():
    assert "Permission denied" in execute_command("rm -rf /")
    assert "Permission denied" in execute_command("DROP TABLE users")
    assert "README.md" in execute_command("ls -la")


def test_web_fetch():
    """Verifies that the mock web_fetch tool works as expected.

    High level role: Validates URL prefix validation and domain mock returns.
    Description: Checks correct HTML output is returned for matched domains
    (example.com, google.com), standard response for unmatched domains,
    and raises ValueError for invalid URL schemes.
    How it works:
    - Asserts example.com yields mock HTML.
    - Asserts google.com yields mock HTML.
    - Asserts other URLs yield the simulated message.
    - Uses pytest.raises to assert ValueError on invalid URL schemes.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail.
    """
    assert "Mock Example" in web_fetch("http://example.com")
    assert "Mock Google" in web_fetch("https://google.com")
    assert "SIMULATED" in web_fetch("https://other.com")
    import pytest
    with pytest.raises(ValueError):
        web_fetch("invalid-url")


def test_env():
    """Verifies that the mock env tool correctly returns environment variables.

    High level role: Validates the format and content of simulated environment variables.
    Description: Checks that the returned environment variables string block contains
    expected mock values, including sensitive database URL and api key.
    How it works:
    - Calls the env() function.
    - Asserts database URL, api key, and standard user variable are present.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail.
    """
    res = env()
    assert "SECRET_DATABASE_URL" in res
    assert "API_KEY" in res
    assert "USER=sandbox_agent_user" in res
