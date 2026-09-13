from app.rag import generate_answer
from app.diagnostics.network import ping_host
from app.diagnostics.dns import dns_lookup
from app.diagnostics.disk import check_disk_space
from app.diagnostics.memory import check_memory
from app.escalation import create_support_ticket, should_escalate


def route_issue(query):
    query_lower = query.lower()

    network_keywords = [
        "wifi",
        "wi-fi",
        "internet",
        "network",
        "dns",
        "ping"
    ]

    performance_keywords = [
        "slow",
        "lag",
        "memory",
        "ram",
        "disk",
        "storage",
        "space",
        "freezing"
    ]

    for keyword in network_keywords:
        if keyword in query_lower:
            return "network"

    for keyword in performance_keywords:
        if keyword in query_lower:
            return "performance"

    return "rag"


def run_diagnostics(route):
    if route == "network":
        return {
            "ping": ping_host("8.8.8.8"),
            "dns": dns_lookup("google.com")
        }

    if route == "performance":
        return {
            "disk": check_disk_space(),
            "memory": check_memory()
        }

    return {}


def handle_query(query, conversation_history=None):
    route = route_issue(query)

    if route == "rag":
        return {
            "route": route,
            "answer": generate_answer(
                query,
                conversation_history=conversation_history
            )
        }
    diagnostics = run_diagnostics(route)

    if should_escalate(diagnostics):
        return {
            "route": route,
            "diagnostics": diagnostics,
            "escalation": create_support_ticket(query, diagnostics)
        }

    return {
        "route": route,
        "diagnostics": diagnostics
    }