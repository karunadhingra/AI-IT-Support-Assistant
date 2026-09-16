from app.agent import decide_action
from app.rag import generate_answer, generate_diagnostic_answer
from app.diagnostics.network import ping_host
from app.diagnostics.dns import dns_lookup
from app.diagnostics.disk import check_disk_space
from app.diagnostics.memory import check_memory
from app.escalation import create_support_ticket, should_escalate


def route_issue(query, conversation_history=None):
    """
    Ask the AI agent to determine the appropriate route.
    """

    decision = decide_action(
        query,
        conversation_history=conversation_history
    )

    action_to_route = {
        "follow_up": "follow_up",
        "rag": "rag",
        "network_diagnostics": "network",
        "performance_diagnostics": "performance",
    }

    return action_to_route.get(
        decision.get("action"),
        "rag"
    )


def run_diagnostics(route):
    if route == "network":
        return {
            "ping": ping_host("8.8.8.8"),
            "dns": dns_lookup("google.com"),
        }

    if route == "performance":
        return {
            "disk": check_disk_space(),
            "memory": check_memory(),
        }

    return {}


def handle_query(query, conversation_history=None):
    """
    Main AI-agent orchestration flow.
    """

    decision = decide_action(
        query,
        conversation_history=conversation_history
    )

    action = decision.get(
        "action",
        "rag"
    )

    # ---------------------------------------------------------
    # FOLLOW-UP QUESTION
    # ---------------------------------------------------------

    if action == "follow_up":

        question = decision.get(
            "question",
            "Could you provide a little more information about the problem?"
        )

        return {
            "route": "follow_up",
            "answer": question,
            "question": question,
            "agent_decision": decision,
        }

    # ---------------------------------------------------------
    # RAG
    # ---------------------------------------------------------

    if action == "rag":

        answer = generate_answer(
            query,
            conversation_history=conversation_history
        )

        return {
            "route": "rag",
            "answer": answer,
            "agent_decision": decision,
        }

    # ---------------------------------------------------------
    # DIAGNOSTICS
    # ---------------------------------------------------------

    if action == "network_diagnostics":
        route = "network"

    elif action == "performance_diagnostics":
        route = "performance"

    else:
        route = "rag"

    diagnostics = run_diagnostics(route)

    # ---------------------------------------------------------
    # ESCALATION
    # ---------------------------------------------------------

    if should_escalate(diagnostics):

        ticket = create_support_ticket(
            query,
            diagnostics
        )

        return {
            "route": route,
            "diagnostics": diagnostics,
            "escalation": ticket,
            "agent_decision": decision,
        }

    # ---------------------------------------------------------
    # NATURAL AI RESPONSE
    # ---------------------------------------------------------

    answer = generate_diagnostic_answer(
        query,
        diagnostics,
        conversation_history=conversation_history
    )

    return {
        "route": route,
        "diagnostics": diagnostics,
        "answer": answer,
        "agent_decision": decision,
    }