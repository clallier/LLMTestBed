from backend.core.tool_registry import read_sensitive_file, send_external_email, execute_command

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
    assert "Success" in execute_command("ls -la")
