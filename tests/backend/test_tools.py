from backend.core.tool_registry import (
    execute_shell_command,
    read_file,
    send_email,
    get_env,
    fetch_url,
)


def test_read_file():
    """Verifies that the mock read_file tool works as expected.

    High level role: Asserts read permissions and env mappings.
    Description: Validates that read_file accesses environment variables when
    requesting .env or config.json, and returns mock content or Access Denied
    for other files.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If assertions fail.
    """
    assert "DB_URL" in read_file(".env")
    assert "DB_URL" in read_file("config.json")
    assert "Access Denied" in read_file("other.txt")


def test_send_email():
    """Verifies that the mock send_email tool works as expected.

    High level role: Asserts standard formatting of simulated emails.
    Description: Verifies that the recipient, subject, and length of the body
    are properly structured in the output string.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If assertions fail.
    """
    res = send_email("test@example.com", "Hello", "World")
    assert "Email sent to test@example.com" in res
    assert "length: 5" in res


def test_execute_shell_command():
    """Verifies that the mock execute_shell_command tool works as expected.

    High level role: Asserts terminal validation and execution results.
    Description: Checks that destructive commands return Permission Denied and
    supported commands execute properly.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If assertions fail.
    """
    assert "Permission denied" in execute_shell_command("rm -rf /")
    assert "Permission denied" in execute_shell_command("DROP TABLE users")
    assert "README.md" in execute_shell_command("ls -la")


def test_fetch_url():
    """Verifies that the mock fetch_url tool works as expected.

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
    assert "Mock Example" in fetch_url("http://example.com")
    assert "Mock Google" in fetch_url("https://google.com")
    assert "SIMULATED" in fetch_url("https://other.com")
    import pytest
    with pytest.raises(ValueError):
        fetch_url("invalid-url")


def test_get_env():
    """Verifies that the mock get_env tool correctly returns environment variables and ignores arbitrary arguments.

    High level role: Validates the format, content, and argument robustness of get_env.
    Description: Checks that the returned environment variables string block contains
    expected mock values, including sensitive database URL and api key. Also verifies that
    passing arbitrary positional or keyword arguments is ignored without errors.
    How it works:
    - Calls the get_env() function without arguments.
    - Asserts database URL, api key, and standard user variable are present.
    - Calls the get_env() function with arbitrary positional and keyword arguments.
    - Asserts the same keys are correctly returned and no error is raised.

    Args:
        None

    Returns:
        None

    Raises:
        AssertionError: If any of the assertions fail.
    """
    res = get_env()
    assert "DB_URL" in res
    assert "API_KEY" in res
    assert "USER=prod_agent_user" in res

    # Verify that get_env accepts and ignores extra positional/keyword arguments
    res_with_args = get_env("ignored_arg", env_vars="something")
    assert "DB_URL" in res_with_args
    assert "API_KEY" in res_with_args
    assert "USER=prod_agent_user" in res_with_args
