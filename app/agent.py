import json

import ollama


AGENT_MODEL = "llama3.2:3b"


AGENT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": [
                "follow_up",
                "rag",
                "network_diagnostics",
                "performance_diagnostics",
            ],
        },
        "reason": {
            "type": "string",
        },
        "question": {
            "type": "string",
        },
    },
    "required": ["action", "reason", "question"],
}


NETWORK_KEYWORDS = [
    "wifi",
    "wi-fi",
    "internet",
    "network",
    "dns",
    "ping",
    "router",
    "connection",
    "connectivity",
]


PERFORMANCE_KEYWORDS = [
    "slow",
    "lag",
    "memory",
    "ram",
    "disk",
    "storage",
    "space",
    "freezing",
    "freeze",
    "performance",
]


def _format_history(conversation_history):
    if not conversation_history:
        return "No previous conversation."

    history_parts = []

    for message in conversation_history:
        role = message.get("role", "unknown")
        content = message.get("content", "")

        if content:
            history_parts.append(
                f"{role}: {content}"
            )

    return "\n".join(history_parts) or "No previous conversation."


def _is_short_follow_up(query):
    """Detect replies that depend strongly on previous context."""

    normalized = query.lower().strip()

    short_replies = {
        "yes",
        "yeah",
        "yep",
        "okay",
        "ok",
        "sure",
        "do it",
        "go ahead",
        "try it",
        "please do",
        "continue",
        "that worked",
        "it worked",
        "no",
        "nope",
    }

    return normalized in short_replies


def _keyword_route(query):
    """
    Detect an explicit current problem that has a known
    diagnostic category.

    Returns:
        "network_diagnostics"
        "performance_diagnostics"
        None
    """

    query_lower = query.lower()

    for keyword in NETWORK_KEYWORDS:
        if keyword in query_lower:
            return "network_diagnostics"

    for keyword in PERFORMANCE_KEYWORDS:
        if keyword in query_lower:
            return "performance_diagnostics"

    return None


def _fallback_decision(query, conversation_history=None):
    """
    Safe deterministic fallback when the local AI agent
    is unavailable or returns invalid data.
    """

    keyword_route = _keyword_route(query)

    if keyword_route == "network_diagnostics":
        return {
            "action": "network_diagnostics",
            "reason": (
                "The current problem appears to be network related."
            ),
            "question": "",
        }

    if keyword_route == "performance_diagnostics":
        return {
            "action": "performance_diagnostics",
            "reason": (
                "The current problem appears to be related "
                "to system performance."
            ),
            "question": "",
        }

    if _is_short_follow_up(query) and conversation_history:
        return {
            "action": "rag",
            "reason": (
                "The latest message depends on the previous "
                "troubleshooting conversation."
            ),
            "question": "",
        }

    return {
        "action": "rag",
        "reason": (
            "The current problem can be investigated "
            "using the knowledge base."
        ),
        "question": "",
    }


def _validate_current_problem_route(
    query,
    decision,
    conversation_history=None,
):
    """
    Protect the agent from incorrectly choosing RAG for a
    clearly identifiable network or performance problem.

    A genuine LLM follow-up decision is preserved because
    follow-up behavior is tested and may be appropriate when
    the agent determines that more information is required.
    """

    # Short contextual replies should continue using the
    # previous conversation.
    if _is_short_follow_up(query):
        return decision

    keyword_route = _keyword_route(query)

    if keyword_route is None:
        return decision

    # Only correct an incorrect RAG decision here.
    #
    # This fixes cases such as:
    # "My computer is very slow" -> LLM says RAG
    #
    # while preserving a deliberate follow-up decision from
    # the agent.
    if decision.get("action") == "rag":

        if keyword_route == "network_diagnostics":
            return {
                "action": "network_diagnostics",
                "reason": (
                    "The current message explicitly describes "
                    "a network-related problem, so live network "
                    "diagnostics are appropriate."
                ),
                "question": "",
            }

        if keyword_route == "performance_diagnostics":
            return {
                "action": "performance_diagnostics",
                "reason": (
                    "The current message explicitly describes "
                    "a performance-related problem, so live "
                    "performance diagnostics are appropriate."
                ),
                "question": "",
            }

    return decision
def decide_action(query, conversation_history=None):
    """
    Ask the local LLM to decide the single best next action.

    The latest explicit user problem has priority over older
    conversation context.

    Short replies such as "yes", "okay", and "do it" are
    interpreted using the previous conversation.

    Clear network and performance problems are protected by
    a deterministic route-validation layer after the LLM
    decision.
    """

    history_text = _format_history(
        conversation_history
    )

    prompt = f"""
You are the decision-making agent of an AI IT Support Assistant.

Your job is to decide the SINGLE best next action for the
user's CURRENT IT problem.

Available actions:

1. follow_up
   Ask ONE useful question when important information is
   genuinely missing.

2. rag
   Use the troubleshooting knowledge base when the problem
   can be handled using documented troubleshooting guidance.

3. network_diagnostics
   Use live ping and DNS checks for network, Wi-Fi,
   internet, DNS, or connectivity problems.

4. performance_diagnostics
   Use live disk-space and memory checks for computer
   performance, slowness, freezing, RAM, storage, or
   resource problems.

IMPORTANT DECISION RULES:

- The latest explicit user message is the PRIMARY signal.
- A new explicit problem must NOT be overridden by an older
  problem in the conversation.
- Conversation history is mainly used to understand short
  contextual replies such as "yes", "okay", or "do it".
- If the latest message clearly describes a new problem,
  treat it as a new investigation.
- Do not choose follow_up merely because more information
  could theoretically be useful.
- Ask a follow-up only when an important piece of information
  is genuinely required before proceeding.
- Prefer live diagnostics when they can provide useful
  evidence about the current problem.
- For Wi-Fi, internet, network, DNS, router, or connectivity
  problems, prefer network_diagnostics.
- For slow computers, lag, freezing, RAM, memory, disk,
  storage, or performance problems, prefer
  performance_diagnostics.
- Never invent diagnostic results.
- Return only valid JSON matching the supplied schema.

Previous conversation:
{history_text}

CURRENT user message:
{query}
"""

    try:
        response = ollama.chat(
            model=AGENT_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            format=AGENT_SCHEMA,
        )

        content = response["message"]["content"]

        decision = json.loads(content)

        valid_actions = {
            "follow_up",
            "rag",
            "network_diagnostics",
            "performance_diagnostics",
        }

        if decision.get("action") not in valid_actions:
            return _fallback_decision(
                query,
                conversation_history,
            )

        decision["reason"] = decision.get(
            "reason",
            "",
        )

        decision["question"] = decision.get(
            "question",
            "",
        )

        decision = _validate_current_problem_route(
            query,
            decision,
            conversation_history,
        )

        return decision

    except Exception:
        return _fallback_decision(
            query,
            conversation_history,
        )


if __name__ == "__main__":
    query = "My Wi-Fi is not working"

    decision = decide_action(query)

    print("User problem:")
    print(query)

    print("\nAgent decision:")
    print(decision)