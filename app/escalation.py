def should_escalate(diagnostics):
    """
    Decide whether diagnostic results require
    human IT support.
    """

    if not diagnostics:
        return False

    ping_result = diagnostics.get("ping")

    if ping_result and not ping_result.get(
        "success",
        True
    ):
        return True

    disk_result = diagnostics.get("disk")

    if disk_result and disk_result.get(
        "free_gb",
        float("inf")
    ) < 5:
        return True

    memory_result = diagnostics.get("memory")

    if memory_result and memory_result.get(
        "used_percent",
        0
    ) > 90:
        return True

    return False


def create_diagnostic_summary(issue, diagnostics):
    """
    Keep a structured diagnostic summary for programmatic
    use and backwards compatibility.
    """

    return {
        "issue": issue,
        "diagnostics": diagnostics,
    }


def _build_findings(diagnostics):
    findings = []

    ping_result = diagnostics.get("ping")

    if ping_result:
        if ping_result.get("success", False):
            findings.append(
                "Internet connectivity check completed successfully."
            )
        else:
            findings.append(
                "Internet connectivity check failed."
            )

    dns_result = diagnostics.get("dns")

    if dns_result:
        if dns_result.get("success", False):
            findings.append(
                "DNS lookup completed successfully."
            )
        else:
            findings.append(
                "DNS lookup failed."
            )

    disk_result = diagnostics.get("disk")

    if disk_result:
        free_gb = disk_result.get("free_gb")

        if free_gb is not None:

            if free_gb < 5:
                findings.append(
                    f"Only {free_gb:.2f} GB of disk space is available."
                )
            else:
                findings.append(
                    f"Approximately {free_gb:.2f} GB of disk space is available."
                )

    memory_result = diagnostics.get("memory")

    if memory_result:

        used_percent = memory_result.get(
            "used_percent"
        )

        if used_percent is not None:

            if used_percent > 90:
                findings.append(
                    f"Memory usage is high at {used_percent:.1f}%."
                )
            else:
                findings.append(
                    f"Memory usage is currently {used_percent:.1f}%."
                )

    return findings


def create_support_ticket(issue, diagnostics):
    """
    Create a clean support ticket while retaining the
    structured diagnostic summary for programmatic use.
    """

    diagnostic_summary = create_diagnostic_summary(
        issue,
        diagnostics
    )

    findings = _build_findings(
        diagnostics
    )

    if not findings:
        findings.append(
            "The available diagnostics did not provide enough information."
        )

    return {
        "status": "created",
        "title": "IT Support Assistance Required",
        "issue": issue,
        "summary": (
            "The assistant was unable to resolve the issue "
            "automatically and has prepared this case for IT support."
        ),
        "findings": findings,
        "action_needed": (
            "Please review the diagnostic findings and "
            "continue troubleshooting the user's issue."
        ),
        "priority": "High",
        "diagnostic_summary": diagnostic_summary,
    }