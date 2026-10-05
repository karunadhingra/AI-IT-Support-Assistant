import psutil


PROTECTED_PROCESSES = {
    "system idle process",
    "system",
    "registry",
    "memory compression",
    "memcompression",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "winlogon.exe",
    "dwm.exe",
    "llama-server.exe",
    "ollama.exe",
}


def _normalize_name(name):
    return str(name).strip().lower()


def _is_protected_process(name):
    normalized = _normalize_name(name)

    return normalized in PROTECTED_PROCESSES


def _collect_processes():
    """
    Collect current CPU and memory usage for running processes.

    This function only reads process information.
    It does not terminate or modify any process.
    """

    processes = []

    for process in psutil.process_iter(
        ["pid", "name", "cpu_percent", "memory_percent"]
    ):
        try:
            info = process.info

            name = info.get("name") or "Unknown"
            pid = info.get("pid")

            cpu_percent = info.get("cpu_percent") or 0.0
            memory_percent = info.get("memory_percent") or 0.0

            processes.append(
                {
                    "pid": pid,
                    "name": name,
                    "cpu_percent": round(
                        float(cpu_percent),
                        1,
                    ),
                    "memory_percent": round(
                        float(memory_percent),
                        1,
                    ),
                    "protected": _is_protected_process(name),
                }
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

    return processes


def get_top_processes(
    limit=5,
    excluded_processes=None,
    required_processes=None,
):
    """
    Collect current CPU and memory usage for running processes.

    Parameters
    ----------
    limit:
        Maximum number of processes returned in each category.

    excluded_processes:
        Processes that should not be recommended again because
        the user has already ruled them out or handled them.

    required_processes:
        Processes that the user explicitly said they need.
        These processes remain visible in diagnostics but are
        never selected as recommendation candidates.

    Protected Windows processes and Ollama are always excluded
    from recommendation candidates.

    This function only reads process information.
    It never terminates or modifies any process.
    """

    excluded_processes = {
        _normalize_name(name)
        for name in (excluded_processes or [])
    }

    required_processes = {
        _normalize_name(name)
        for name in (required_processes or [])
    }

    processes = _collect_processes()

    top_cpu = sorted(
        processes,
        key=lambda item: item["cpu_percent"],
        reverse=True,
    )[:limit]

    top_memory = sorted(
        processes,
        key=lambda item: item["memory_percent"],
        reverse=True,
    )[:limit]

    recommendation_candidates = []

    for process in sorted(
        processes,
        key=lambda item: (
            item["memory_percent"],
            item["cpu_percent"],
        ),
        reverse=True,
    ):
        normalized_name = _normalize_name(
            process["name"]
        )

        if process["protected"]:
            continue

        if normalized_name in excluded_processes:
            continue

        if normalized_name in required_processes:
            continue

        recommendation_candidates.append(process)

        if len(recommendation_candidates) >= limit:
            break

    return {
        "success": True,
        "process_count": len(processes),
        "top_cpu": top_cpu,
        "top_memory": top_memory,
        "recommendation_candidates": recommendation_candidates,
        "excluded_processes": sorted(
            excluded_processes
        ),
        "required_processes": sorted(
            required_processes
        ),
    }


def find_process(
    process_name,
):
    """
    Find currently running processes matching a name.

    Returns a list because the same executable can have
    multiple running instances.
    """

    normalized_target = _normalize_name(
        process_name
    )

    matches = []

    for process in _collect_processes():
        normalized_name = _normalize_name(
            process["name"]
        )

        if normalized_name == normalized_target:
            matches.append(process)

    return matches


def get_process_summary(
    process,
):
    """
    Create a simple human-readable description of a process.
    """

    if not process:
        return "Unknown process"

    name = process.get(
        "name",
        "Unknown",
    )

    memory_percent = process.get(
        "memory_percent",
        0.0,
    )

    cpu_percent = process.get(
        "cpu_percent",
        0.0,
    )

    return (
        f"{name} is using "
        f"{memory_percent:.1f}% RAM and "
        f"{cpu_percent:.1f}% CPU."
    )


def choose_recommendation(
    diagnostics,
):
    """
    Choose the best currently available process to discuss
    with the user.

    This does NOT mean the process should automatically be
    closed. The assistant must first explain the resource
    usage and ask whether the user needs the application.
    """

    candidates = diagnostics.get(
        "recommendation_candidates",
        [],
    )

    if not candidates:
        return None

    return candidates[0]


def build_process_recommendation(
    diagnostics,
):
    """
    Build a safe recommendation based on the current
    diagnostic results.

    The assistant never tells the user to blindly terminate
    a process. It asks whether the application is needed.
    """

    candidate = choose_recommendation(
        diagnostics
    )

    if candidate is None:
        return {
            "available": False,
            "process": None,
            "message": (
                "The diagnostic check did not find another "
                "user-controlled process that should be "
                "recommended for closing. We should continue "
                "with another performance troubleshooting step."
            ),
        }

    name = candidate.get(
        "name",
        "Unknown process",
    )

    memory_percent = candidate.get(
        "memory_percent",
        0.0,
    )

    cpu_percent = candidate.get(
        "cpu_percent",
        0.0,
    )

    return {
        "available": True,
        "process": candidate,
        "message": (
            f"{name} is currently using about "
            f"{memory_percent:.1f}% of RAM and "
            f"{cpu_percent:.1f}% CPU among the "
            f"processes detected. "
            f"Do you need {name} right now?"
        ),
    }