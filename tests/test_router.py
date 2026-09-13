from unittest.mock import patch
from app.router import route_issue, handle_query


def test_network_issue():
    assert route_issue("My Wi-Fi is not working") == "network"


def test_performance_issue():
    assert route_issue("My computer is very slow") == "performance"


def test_rag_issue():
    assert route_issue("How do I connect a Bluetooth device?") == "rag"


def test_handle_query_rag():
    with patch(
        "app.router.generate_answer",
        return_value="Bluetooth troubleshooting answer"
    ):
        from app.router import handle_query

        result = handle_query("How do I connect a Bluetooth device?")

    assert result["route"] == "rag"
    assert result["answer"] == "Bluetooth troubleshooting answer"


def test_handle_query_network():
    with patch(
        "app.router.run_diagnostics",
        return_value={
            "ping": {"success": True},
            "dns": {"success": True}
        }
    ):
        from app.router import handle_query

        result = handle_query("My Wi-Fi is not working")

    assert result["route"] == "network"
    assert result["diagnostics"]["ping"]["success"] is True
    assert result["diagnostics"]["dns"]["success"] is True


def test_handle_query_performance():
    with patch(
        "app.router.run_diagnostics",
        return_value={
            "disk": {"free_gb": 100},
            "memory": {"used_percent": 50}
        }
    ):
        from app.router import handle_query

        result = handle_query("My computer is very slow")

    assert result["route"] == "performance"
    assert result["diagnostics"]["disk"]["free_gb"] == 100
    assert result["diagnostics"]["memory"]["used_percent"] == 50
def test_handle_query_escalation():
    diagnostics = {
        "ping": {"success": False},
        "dns": {"success": True}
    }

    with patch(
        "app.router.run_diagnostics",
        return_value=diagnostics
    ):
        result = handle_query("My Wi-Fi is not working")

    assert result["route"] == "network"
    assert result["diagnostics"] == diagnostics
    assert result["escalation"]["status"] == "created"
    assert result["escalation"]["issue"] == "My Wi-Fi is not working"