from app.escalation import (
    should_escalate,
    create_diagnostic_summary,
    create_support_ticket
)


def test_create_diagnostic_summary():
    issue = "My Wi-Fi is not working"
    diagnostics = {
        "ping": {"success": False},
        "dns": {"success": True}
    }

    result = create_diagnostic_summary(issue, diagnostics)

    assert result["issue"] == issue
    assert result["diagnostics"] == diagnostics


def test_create_support_ticket():
    issue = "My computer is very slow"
    diagnostics = {
        "disk": {"free_gb": 2},
        "memory": {"used_percent": 95}
    }

    result = create_support_ticket(issue, diagnostics)

    assert result["status"] == "created"
    assert result["issue"] == issue
    assert result["diagnostic_summary"]["diagnostics"] == diagnostics
def test_escalate_when_ping_fails():
    diagnostics = {
        "ping": {"success": False},
        "dns": {"success": True}
    }

    assert should_escalate(diagnostics) is True


def test_escalate_when_disk_is_low():
    diagnostics = {
        "disk": {"free_gb": 2},
        "memory": {"used_percent": 50}
    }

    assert should_escalate(diagnostics) is True


def test_escalate_when_memory_is_high():
    diagnostics = {
        "disk": {"free_gb": 100},
        "memory": {"used_percent": 95}
    }

    assert should_escalate(diagnostics) is True


def test_no_escalation_for_normal_diagnostics():
    diagnostics = {
        "disk": {"free_gb": 100},
        "memory": {"used_percent": 50}
    }

    assert should_escalate(diagnostics) is False