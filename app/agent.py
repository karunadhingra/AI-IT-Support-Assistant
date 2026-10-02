
import json
import re

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
        "reason": {"type": "string"},
        "question": {"type": "string"},
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


# Informational queries should not automatically trigger diagnostics.
INFORMATIONAL_PHRASES = [
    "network security",
    "improve my network",
    "learn about network",
    "explain network",
    "what is network",
    "how does network",
    "how can i improve",
    "how do i improve",
    "best practices",
    "security tips",
]


def _format_history(conversation_history):
    if not conversation_history:
        return "No previous conversation."

    history_parts = []

    for message in conversation_history:
        role = message.get("role", "unknown")
        content = message.get("content", "")

        if content:
            history_parts.append(f"{role}: {content}")

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


def _is_informational_query(query):
    """Identify common informational questions about IT topics."""

    normalized = re.sub(
        r"\s+",
        " ",
        query.lower().strip(),
    )

    return any(
        phrase in normalized
        for phrase in INFORMATIONAL_PHRASES
    )


def _keyword_route(query):
    """
    Detect a known diagnostic category.

    Returns a diagnostic action or None.
    Informational questions are not automatically routed
    to live diagnostics.
    """

    if _is_informational_query(query):
        return None

    words = set(
        re.findall(r"\b[a-z0-9-]+\b", query.lower())
    )

    # Require stronger evidence of a current network problem.
    network_problem_indicators = {
        "not working",
        "doesn't work",
        "doesnt work",
        "cannot connect",
        "can't connect",
        "cant connect",
        "disconnected",
        "disconnecting",
        "unavailable",
        "failed",
        "failure",
        "no internet",
        "keeps dropping",
        "won't connect",
        "wont connect",
        "unable to connect",
    }

    query_lower = query.lower()

    has_network_keyword = any(
        keyword in words
        for keyword in NETWORK_KEYWORDS
    )

    has_network_problem = any(
        indicator in query_lower
        for indicator in network_problem_indicators
    )

    if has_network_keyword and has_network_problem:
        return "network_diagnostics"

    # Performance diagnostics require a performance keyword.
    performance_problem_indicators = {
        "slow",
        "lag",
        "lagging",
        "freezing",
        "freeze",
        "frozen",
        "running slowly",
        "runs slowly",
        "not responding",
        "high memory usage",
        "low disk space",
        "disk full",
        "running out of space",
    }

    has_performance_keyword = any(
        keyword in words
        for keyword in PERFORMANCE_KEYWORDS
    )

    has_performance_problem = any(
        indicator in query_lower
        for indicator in performance_problem_indicators
    )

    if has_performance_keyword and has_performance_problem:
        return "performance_diagnostics"

    return None


def _fallback_decision(query, conversation_history=None):
    """Provide a deterministic fallback if the agent fails."""

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
    Correct a RAG decision when the current message clearly
    describes a network or performance problem.
    """

    if _is_short_follow_up(query):
        return decision

    if _is_informational_query(query):
        return decision

    keyword_route = _keyword_route(query)

    if keyword_route is None:
        return decision

    if decision.get("action") == "rag":
        if keyword_route == "network_diagnostics":
            return {
                "action": "network_diagnostics",
                "reason": (
                    "The current message describes a network "
                    "problem, so live network diagnostics "
                    "are appropriate."
                ),
                "question": "",
            }

        if keyword_route == "performance_diagnostics":
            return {
                "action": "performance_diagnostics",
                "reason": (
                    "The current message describes a performance "
                    "problem, so live performance diagnostics "
                    "are appropriate."
                ),
                "question": "",
            }

    return decision


def decide_action(query, conversation_history=None):
    """
    Ask the local LLM to choose the best action for the
    user's current IT problem.
    """

    history_text = _format_history(conversation_history)

    prompt = f"""
You are the decision-making agent of an AI IT Support Assistant.

Choose the SINGLE best next action for the user's CURRENT message.

Available actions:

1. follow_up
   Ask one useful question when important information is missing.

2. rag
   Answer informational questions and use documented
   troubleshooting guidance from the knowledge base.

3. network_diagnostics
   Run live ping and DNS checks for current network failures,
   Wi-Fi connection failures, internet outages, DNS failures,
   or connectivity problems.

4. performance_diagnostics
   Run live disk-space and memory checks for computer slowness,
   freezing, RAM problems, or storage-related performance issues.

Decision rules:

- Prioritize the latest explicit user message.
- Use conversation history to understand contextual replies.
- Do not let an older problem override a new explicit problem.
- Distinguish asking for information from reporting a live failure.
- Questions about security concepts, best practices, or how
  to improve a system should normally use RAG.
- Prefer diagnostics when the user reports a current failure
  that the available checks can investigate.
- Do not invent diagnostic results.
- If choosing follow_up, provide one relevant, non-empty question.
- Return valid JSON matching the supplied schema.

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

        decision["reason"] = str(
            decision.get("reason", "")
        ).strip()

        decision["question"] = str(
            decision.get("question", "")
        ).strip()

        if decision["action"] == "follow_up":
            if not decision["question"]:
                decision["question"] = (
                    "Could you describe the problem "
                    "you are experiencing?"
                )

            if not decision["reason"]:
                decision["reason"] = (
                    "More information is needed to understand "
                    "the current problem."
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

