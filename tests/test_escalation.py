from app.escalation import (
    create_diagnostic_summary,
    create_support_ticket,
    should_escalate,
)


def test_create_diagnostic_summary():

    issue = "My computer is very slow"

    diagnostics = {
        "disk": {"free_gb": 2},
        "memory": {"used_percent": 95},
    }

    result = create_diagnostic_summary(
        issue,
        diagnostics
    )

    assert result["issue"] == issue
    assert result["diagnostics"] == diagnostics


def test_create_support_ticket():

    issue = "My computer is very slow"

    diagnostics = {
        "disk": {"free_gb": 2},
        "memory": {"used_percent": 95},
    }

    result = create_support_ticket(
        issue,
        diagnostics
    )

    assert result["status"] == "created"
    assert result["issue"] == issue
    assert result["diagnostic_summary"]["diagnostics"] == diagnostics
    assert result["title"]
    assert result["summary"]
    assert result["findings"]
    assert result["action_needed"]
    assert result["priority"] == "High"


def test_escalate_when_ping_fails():

    diagnostics = {
        "ping": {
            "success": False
        }
    }

    assert should_escalate(
        diagnostics
    ) is True


def test_escalate_when_disk_is_low():

    diagnostics = {
        "disk": {
            "free_gb": 2
        }
    }

    assert should_escalate(
        diagnostics
    ) is True


def test_escalate_when_memory_is_high():

    diagnostics = {
        "memory": {
            "used_percent": 95
        }
    }

    assert should_escalate(
        diagnostics
    ) is True


def test_no_escalation_for_normal_diagnostics():

    diagnostics = {
        "disk": {
            "free_gb": 100
        },
        "memory": {
            "used_percent": 50
        },
        "ping": {
            "success": True
        }
    }

    assert should_escalate(
        diagnostics
    ) is False

def test_no_escalation_for_empty_diagnostics():

    assert should_escalate({}) is False


def test_no_escalation_for_successful_ping_only():

    diagnostics = {
        "ping": {
            "success": True
        }
    }

    assert should_escalate(
        diagnostics
    ) is False


def test_support_ticket_includes_failed_ping_finding():

    issue = "My internet is not working"

    diagnostics = {
        "ping": {
            "success": False
        }
    }

    result = create_support_ticket(
        issue,
        diagnostics
    )

    assert result["status"] == "created"
    assert result["issue"] == issue
    assert "Internet connectivity check failed." in result["findings"]