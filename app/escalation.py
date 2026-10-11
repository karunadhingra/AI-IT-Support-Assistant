def should_escalate(diagnostics):
    """
    Decide whether diagnostic results require
    human IT support.
    """
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
            findings.append("Internet connectivity check (Ping 8.8.8.8) completed successfully.")
        else:
            findings.append("Internet connectivity check failed.")

    dns_result = diagnostics.get("dns")
    if dns_result:
        if dns_result.get("success", False):
            findings.append("DNS lookup (google.com) completed successfully.")
        else:
            findings.append("DNS lookup failed.")

    disk_result = diagnostics.get("disk")
    if disk_result:
        free_gb = disk_result.get("free_gb")
        total_gb = disk_result.get("total_gb")
        if free_gb is not None:
            total_str = f" out of {total_gb:.2f} GB" if total_gb else ""
            if free_gb < 5:
                findings.append(f"Only {free_gb:.2f} GB{total_str} of disk space is available (Critical).")
            else:
                findings.append(f"Approximately {free_gb:.2f} GB{total_str} of disk space is available.")

    memory_result = diagnostics.get("memory")
    if memory_result:
        used_percent = memory_result.get("used_percent")
        total_gb = memory_result.get("total_gb")
        if used_percent is not None:
            ram_str = f" (Total RAM: {total_gb} GB)" if total_gb else ""
            if used_percent > 90:
                findings.append(f"Memory usage is high at {used_percent:.1f}%{ram_str}.")
            else:
                findings.append(f"Memory usage is currently {used_percent:.1f}%{ram_str}.")

    cpu_result = diagnostics.get("cpu")
    if isinstance(cpu_result, dict) and cpu_result.get("success"):
        findings.append(
            f"CPU utilization measured at {cpu_result.get('cpu_percent', 0.0):.1f}% "
            f"across {cpu_result.get('logical_cores', 1)} logical cores."
        )

    swap_result = diagnostics.get("swap")
    if isinstance(swap_result, dict) and swap_result.get("success"):
        findings.append(
            f"Virtual Memory / Swap usage is at {swap_result.get('used_percent', 0.0):.1f}% "
            f"({swap_result.get('used_gb', 0.0)} GB / {swap_result.get('total_gb', 0.0)} GB)."
        )

    uptime_result = diagnostics.get("uptime")
    if isinstance(uptime_result, dict) and uptime_result.get("success"):
        findings.append(
            f"System uptime is {uptime_result.get('uptime_hours', 0.0)} hours "
            f"({uptime_result.get('uptime_days', 0.0)} days since last reboot)."
        )

    process_state = diagnostics.get("process_state")
    if isinstance(process_state, dict):
        req = process_state.get("required_processes", [])
        if req:
            findings.append(
                f"Active applications the user needs to keep open: {', '.join(req)}."
            )

    return findings


def _build_recommended_next_actions(issue, diagnostics):
    """
    Generate concrete L2 IT Support recommendations based on the issue and diagnostics.
    """
    issue_lower = str(issue).lower()
    recommendations = []

    mem_used = diagnostics.get("memory", {}).get("used_percent", 0)
    free_gb = diagnostics.get("disk", {}).get("free_gb", 100)
    ping_ok = diagnostics.get("ping", {}).get("success", True)
    dns_ok = diagnostics.get("dns", {}).get("success", True)

    if not ping_ok or not dns_ok or any(k in issue_lower for k in ["wifi", "wi-fi", "internet", "network", "vpn", "dns"]):
        recommendations.append("Inspect network adapter driver health, DHCP lease status, and firewall/VPN routing tables.")
        recommendations.append("Run network stack reset (`netsh winsock reset` & `ipconfig /flushdns`) with administrator privileges.")
        recommendations.append("Verify router/access-point signal strength or test with an Ethernet connection.")
    elif mem_used > 85 or free_gb < 10 or any(k in issue_lower for k in ["slow", "lag", "freeze", "performance", "memory"]):
        if mem_used > 85:
            recommendations.append(
                f"System RAM utilization is persistently high ({mem_used:.1f}%) while running required user workloads — evaluate for a physical RAM upgrade or check for kernel/driver memory leaks."
            )
        recommendations.append("Run Windows System File Checker (`sfc /scannow`) and DISM health check (`DISM /Online /Cleanup-Image /RestoreHealth`).")
        recommendations.append("Check SSD/HDD SMART health indicators and thermal throttling logs in Event Viewer.")
    else:
        recommendations.append("Review Windows Event Viewer (System and Application logs) for error codes matching the reported issue.")
        recommendations.append("Verify device drivers, OS build version, and hardware peripheral connections via remote desktop session.")

    return recommendations


def create_support_ticket(issue, diagnostics, steps_attempted=None):
    """
    Create a comprehensive support ticket detailing:
    1. Diagnostics performed
    2. Troubleshooting steps followed
    3. Recommended next actions for IT Support
    """
    diagnostic_summary = create_diagnostic_summary(issue, diagnostics)
    findings = _build_findings(diagnostics)

    if not findings:
        findings.append(
            "No automated live OS diagnostics were applicable; guided knowledge-base troubleshooting was performed."
        )

    steps_list = list(steps_attempted) if steps_attempted else [
        "Initial automated diagnostic analysis and first-level guided troubleshooting steps were presented to the user."
    ]

    recommendations = _build_recommended_next_actions(issue, diagnostics)
    action_needed_text = " ".join(recommendations)

    return {
        "status": "created",
        "title": f"IT Support Escalation — {issue[:60]}",
        "issue": issue,
        "summary": (
            "The user attempted guided troubleshooting with the AI IT Support Assistant, "
            "but the issue remains unresolved and requires L2 technician intervention."
        ),
        "findings": findings,
        "steps_attempted": steps_list,
        "recommendations": recommendations,
        "action_needed": action_needed_text,
        "priority": "High",
        "diagnostic_summary": diagnostic_summary,
    }