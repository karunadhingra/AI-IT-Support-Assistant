from unittest.mock import patch


def test_network_issue():
    from app.router import route_issue

    with patch(
        "app.router.decide_action",
        return_value={
            "action": "network_diagnostics",
            "reason": "Network issue",
            "question": "",
        }
    ):
        assert route_issue(
            "My Wi-Fi is not working"
        ) == "network"


def test_performance_issue():
    from app.router import route_issue

    with patch(
        "app.router.decide_action",
        return_value={
            "action": "performance_diagnostics",
            "reason": "Performance issue",
            "question": "",
        }
    ):
        assert route_issue(
            "My computer is very slow"
        ) == "performance"


def test_rag_issue():
    from app.router import route_issue

    with patch(
        "app.router.decide_action",
        return_value={
            "action": "rag",
            "reason": "Knowledge base is appropriate",
            "question": "",
        }
    ):
        assert route_issue(
            "My Bluetooth headphones won't connect"
        ) == "rag"


def test_handle_query_rag():

    with patch(
        "app.router.decide_action",
        return_value={
            "action": "rag",
            "reason": "Known troubleshooting issue",
            "question": "",
        }
    ), patch(
        "app.router.generate_answer",
        return_value="Try restarting Bluetooth."
    ):

        from app.router import handle_query

        result = handle_query(
            "My Bluetooth headphones won't connect"
        )

        assert result["route"] == "rag"
        assert "Bluetooth" in result["answer"]


def test_handle_query_network():

    with patch(
        "app.router.decide_action",
        return_value={
            "action": "network_diagnostics",
            "reason": "Network diagnostics are useful",
            "question": "",
        }
    ), patch(
        "app.router.run_diagnostics",
        return_value={
            "ping": {"success": True},
            "dns": {"success": True},
        }
    ), patch(
        "app.router.generate_diagnostic_answer",
        return_value="Your network checks completed successfully."
    ):

        from app.router import handle_query

        result = handle_query(
            "My Wi-Fi is not working"
        )

        assert result["route"] == "network"
        assert result["diagnostics"]["ping"]["success"] is True
        assert result["diagnostics"]["dns"]["success"] is True


def test_handle_query_performance():

    with patch(
        "app.router.decide_action",
        return_value={
            "action": "performance_diagnostics",
            "reason": "Performance diagnostics are useful",
            "question": "",
        }
    ), patch(
        "app.router.run_diagnostics",
        return_value={
            "disk": {"free_gb": 100},
            "memory": {"used_percent": 50},
        }
    ), patch(
        "app.router.generate_diagnostic_answer",
        return_value="Your system resources look normal."
    ):

        from app.router import handle_query

        result = handle_query(
            "My computer is very slow"
        )

        assert result["route"] == "performance"
        assert result["diagnostics"]["disk"]["free_gb"] == 100
        assert result["diagnostics"]["memory"]["used_percent"] == 50


def test_handle_query_escalation():

    with patch(
        "app.router.decide_action",
        return_value={
            "action": "network_diagnostics",
            "reason": "Network diagnostics are required",
            "question": "",
        }
    ), patch(
        "app.router.run_diagnostics",
        return_value={
            "ping": {"success": False},
            "dns": {"success": False},
        }
    ):

        from app.router import handle_query

        result = handle_query(
            "My internet is completely down"
        )

        assert result["route"] == "network"
        assert "escalation" in result
        assert result["escalation"]["status"] == "created"
def test_handle_query_follow_up():
    from app.router import handle_query

    fake_decision = {
        "action": "follow_up",
        "reason": "More information is needed",
        "question": "When did the problem start?",
    }

    with patch(
        "app.router.decide_action",
        return_value=fake_decision,
    ), patch(
        "app.router.generate_answer",
    ) as mock_generate_answer:

        result = handle_query("My computer has a problem")

    assert result["route"] == "follow_up"
    assert result["answer"] == "When did the problem start?"
    assert result["question"] == "When did the problem start?"
    mock_generate_answer.assert_not_called()


def test_run_network_diagnostics():
    from app.router import run_diagnostics

    fake_ping = {"success": True}
    fake_dns = {"success": True}

    with patch(
        "app.router.ping_host",
        return_value=fake_ping,
    ) as mock_ping, patch(
        "app.router.dns_lookup",
        return_value=fake_dns,
    ) as mock_dns:

        result = run_diagnostics("network")

    assert result["ping"] == fake_ping
    assert result["dns"] == fake_dns
    mock_ping.assert_called_once_with("8.8.8.8")
    mock_dns.assert_called_once_with("google.com")


def test_run_performance_diagnostics():
    from app.router import run_diagnostics

    fake_disk = {"free_gb": 50}
    fake_memory = {"used_percent": 60}

    with patch(
        "app.router.check_disk_space",
        return_value=fake_disk,
    ) as mock_disk, patch(
        "app.router.check_memory",
        return_value=fake_memory,
    ) as mock_memory:

        result = run_diagnostics("performance")

    assert result["disk"] == fake_disk
    assert result["memory"] == fake_memory
    mock_disk.assert_called_once_with()
    mock_memory.assert_called_once_with()