import socket
from unittest.mock import patch

from app.diagnostics.dns import dns_lookup


def test_dns_lookup_success():
    with patch(
        "app.diagnostics.dns.socket.gethostbyname",
        return_value="142.250.183.14"
    ):
        result = dns_lookup("google.com")

    assert result["success"] is True
    assert result["host"] == "google.com"
    assert result["address"] == "142.250.183.14"


def test_dns_lookup_failure():
    with patch(
        "app.diagnostics.dns.socket.gethostbyname",
        side_effect=socket.gaierror
    ):
        result = dns_lookup("invalid-host")

    assert result["success"] is False
    assert result["host"] == "invalid-host"
    assert result["address"] is None