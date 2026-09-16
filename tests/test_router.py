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