def should_escalate(diagnostics):
    if not diagnostics:
        return False

    ping_result = diagnostics.get("ping")
    if ping_result and not ping_result.get("success", True):
        return True

    disk_result = diagnostics.get("disk")
    if disk_result and disk_result.get("free_gb", float("inf")) < 5:
        return True

    memory_result = diagnostics.get("memory")
    if memory_result and memory_result.get("used_percent", 0) > 90:
        return True

    return False


def create_diagnostic_summary(issue, diagnostics):
    return {
        "issue": issue,
        "diagnostics": diagnostics
    }


def create_support_ticket(issue, diagnostics):
    summary = create_diagnostic_summary(issue, diagnostics)

    return {
        "status": "created",
        "issue": issue,
        "diagnostic_summary": summary
    }