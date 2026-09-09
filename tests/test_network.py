from unittest.mock import patch
import subprocess

from app.diagnostics.network import ping_host

def test_ping_host_success():
    result = ping_host("127.0.0.1")

    assert result["host"] == "127.0.0.1"
    assert result["success"] is True
    assert result["output"] != ""


def test_ping_host_failure():
    result = ping_host("invalid-host-that-does-not-exist")

    assert result["host"] == "invalid-host-that-does-not-exist"
    assert result["success"] is False

def test_ping_host_timeout():
    with patch(
        "app.diagnostics.network.subprocess.run",
        side_effect=subprocess.TimeoutExpired(
            cmd=["ping", "example.com"],
            timeout=5
        )
    ):
        result = ping_host("example.com")

    assert result["host"] == "example.com"
    assert result["success"] is False
    assert result["output"] == "Ping request timed out."