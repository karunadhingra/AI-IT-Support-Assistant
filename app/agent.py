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
    "connectivity",
]


PERFORMANCE_KEYWORDS = [
    "slow",
    "lag",
    "lagging",
    "memory",
    "ram",
    "disk",
    "storage",
    "space",
    "freezing",
    "freeze",
    "frozen",
    "performance",
    "process",
    "processes",
    "application",
    "applications",
    "background",
    "cpu",
]


DEVICE_KEYWORDS = [
    "bluetooth",
    "headphone",
    "headphones",
    "earphone",
    "earphones",
    "earbuds",
    "mouse",
    "keyboard",
    "speaker",
    "printer",
    "usb",
    "webcam",
    "device",
]


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
            history_parts.append(
                f"{role}: {content}"
            )

    return "\n".join(history_parts) or "No previous conversation."


def _is_short_follow_up(query):
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


def _is_process_state_reply(query):
    """
    Detect replies where the user is simply telling the assistant
    whether a previously recommended application/process can be
    closed.

    These messages should NOT trigger another full performance
    diagnostic by themselves.
    """

    normalized = re.sub(
        r"\s+",
        " ",
        query.lower().strip(),
    )

    if not normalized:
        return False

    state_replies = {
        "i need it",
        "i need that",
        "i need this",
        "need it",
        "need that",
        "need this",
        "i still need it",
        "i still need that",
        "i still need this",
        "i want it",
        "i still want it",
        "i need that also",
        "i need this also",
        "i need it also",
        "i want that",
        "i want this",
        "i can't close it",
        "i cannot close it",
        "can't close it",
        "cannot close it",
        "i don't want to close it",
        "i do not want to close it",
        "i need to keep it open",
        "i need to keep this open",
        "i need to keep that open",
        "keep it open",
        "keep that open",
        "keep this open",
        "not now",
        "not yet",
    }

    if normalized in state_replies:
        return True

    state_patterns = [
        r"^i need (it|that|this|the application)\b",
        r"^i still need (it|that|this|the application)\b",
        r"^i want (it|that|this)\b",
        r"^i still want (it|that|this)\b",
        r"^i can't close (it|that|this)\b",
        r"^i cannot close (it|that|this)\b",
        r"^i don't want to close (it|that|this)\b",
        r"^i do not want to close (it|that|this)\b",
        r"^i need to keep (it|that|this) open\b",
        r"^keep (it|that|this) open\b",
    ]

    return any(
        re.search(pattern, normalized)
        for pattern in state_patterns
    )


def _is_contextual_follow_up(
    query,
    conversation_history=None,
):
    """
    Detect whether the current message is a response to
    the previous troubleshooting conversation rather than
    a completely new IT problem.
    """

    if not conversation_history:
        return False

    normalized = query.lower().strip()

    if not normalized:
        return False

    if _is_process_state_reply(query):
        return True

    if _is_short_follow_up(query):
        return True

    action_response_patterns = [
        r"^i need\b",
        r"^i still need\b",
        r"^i want\b",
        r"^i still want\b",
        r"^i can't\b",
        r"^i cannot\b",
        r"^i don't want\b",
        r"^i do not want\b",
        r"^i already\b",
        r"^i did\b",
        r"^i didn't\b",
        r"^i did not\b",
        r"^i haven't\b",
        r"^i have not\b",
        r"^not yet\b",
        r"^not now\b",
        r"^still\b",
        r"^already\b",
    ]

    if any(
        re.search(pattern, normalized)
        for pattern in action_response_patterns
    ):
        return True

    contextual_patterns = [
        r"^it was\b",
        r"^they were\b",
        r"^they are\b",
        r"^it is\b",
        r"^it was purchased\b",
        r"^they were purchased\b",
        r"^purchased in\b",
        r"^bought in\b",
        r"^i haven't\b",
        r"^i have not\b",
        r"^i did\b",
        r"^i didn't\b",
        r"^i did not\b",
        r"^i don't\b",
        r"^i do not\b",
        r"^not recently\b",
        r"^recently\b",
    ]

    if any(
        re.search(pattern, normalized)
        for pattern in contextual_patterns
    ):
        return True

    word_count = len(normalized.split())

    if word_count <= 10:
        return True

    return False


def _is_informational_query(query):
    normalized = re.sub(
        r"\s+",
        " ",
        query.lower().strip(),
    )

    return any(
        phrase in normalized
        for phrase in INFORMATIONAL_PHRASES
    )


def _is_device_problem(query):
    normalized = query.lower()

    return any(
        keyword in normalized
        for keyword in DEVICE_KEYWORDS
    )


def _history_contains_keyword(
    conversation_history,
    keywords,
):
    if not conversation_history:
        return False

    history_text = " ".join(
        str(message.get("content", ""))
        for message in conversation_history
    ).lower()

    return any(
        keyword in history_text
        for keyword in keywords
    )


def _get_recent_context_route(
    conversation_history,
):
    """
    Determine the most relevant diagnostic category from
    the recent troubleshooting conversation.

    This is used only when the current message actually
    requires continuing diagnostics.

    Simple process-state replies such as "I need it" are
    handled separately and must not automatically trigger
    another diagnostic run.
    """

    if not conversation_history:
        return None

    recent_messages = conversation_history[-8:]

    recent_text = " ".join(
        str(message.get("content", ""))
        for message in recent_messages
        if message.get("content")
    ).lower()

    performance_score = 0
    network_score = 0

    for keyword in PERFORMANCE_KEYWORDS:
        if keyword in recent_text:
            performance_score += 1

    for keyword in NETWORK_KEYWORDS:
        if keyword in recent_text:
            network_score += 1

    if performance_score > network_score:
        return "performance_diagnostics"

    if network_score > performance_score:
        return "network_diagnostics"

    return None


def _keyword_route(
    query,
    conversation_history=None,
):
    """
    Detect a diagnostic category using both the current
    message and relevant conversation history.
    """

    if _is_informational_query(query):
        return None

    if _is_device_problem(query):
        return None

    words = set(
        re.findall(
            r"\b[a-z0-9-]+\b",
            query.lower(),
        )
    )

    query_lower = query.lower()

    # --------------------------------------------------------
    # NETWORK
    # --------------------------------------------------------

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
        "still won't connect",
        "still wont connect",
        "still can't connect",
        "still cant connect",
        "still cannot connect",
    }

    has_network_keyword = any(
        keyword in words
        for keyword in NETWORK_KEYWORDS
    )

    has_network_problem = any(
        indicator in query_lower
        for indicator in network_problem_indicators
    )

    history_has_network_context = (
        _history_contains_keyword(
            conversation_history,
            NETWORK_KEYWORDS,
        )
    )

    if (
        has_network_keyword
        and has_network_problem
    ):
        return "network_diagnostics"

    if (
        has_network_problem
        and history_has_network_context
    ):
        return "network_diagnostics"

    # --------------------------------------------------------
    # PERFORMANCE
    # --------------------------------------------------------

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
        "performance issue",
        "performance problem",
        "computer is slow",
        "computer is running slowly",
    }

    has_performance_keyword = any(
        keyword in words
        for keyword in PERFORMANCE_KEYWORDS
    )

    has_performance_problem = any(
        indicator in query_lower
        for indicator in performance_problem_indicators
    )

    history_has_performance_context = (
        _history_contains_keyword(
            conversation_history,
            PERFORMANCE_KEYWORDS,
        )
    )

    if (
        has_performance_keyword
        and has_performance_problem
    ):
        return "performance_diagnostics"

    if (
        has_performance_problem
        and history_has_performance_context
    ):
        return "performance_diagnostics"

    return None


def _fallback_decision(
    query,
    conversation_history=None,
):
    """
    Deterministic fallback when the LLM cannot make a
    valid decision.
    """

    # --------------------------------------------------------
    # IMPORTANT:
    # Process-state replies are NOT new diagnostic requests.
    # --------------------------------------------------------

    if _is_process_state_reply(query):
        return {
            "action": "rag",
            "reason": (
                "The user is responding to a previous process "
                "recommendation and does not appear to be "
                "reporting a new performance problem."
            ),
            "question": "",
        }

    keyword_route = _keyword_route(
        query,
        conversation_history,
    )

    if keyword_route == "network_diagnostics":
        return {
            "action": "network_diagnostics",
            "reason": (
                "The current problem appears to be "
                "a network connectivity issue."
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

    if _is_contextual_follow_up(
        query,
        conversation_history,
    ):
        contextual_route = _get_recent_context_route(
            conversation_history
        )

        if contextual_route == "performance_diagnostics":
            return {
                "action": "rag",
                "reason": (
                    "The latest message is a contextual response "
                    "to the ongoing troubleshooting conversation, "
                    "but it does not itself report a new performance "
                    "failure."
                ),
                "question": "",
            }

        if contextual_route == "network_diagnostics":
            return {
                "action": "rag",
                "reason": (
                    "The latest message is a contextual response "
                    "to the ongoing troubleshooting conversation, "
                    "but it does not itself report a new network "
                    "failure."
                ),
                "question": "",
            }

        return {
            "action": "rag",
            "reason": (
                "The latest message appears to continue "
                "the previous troubleshooting conversation."
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
    Validate the LLM decision against deterministic
    routing rules.
    """

    if _is_informational_query(query):
        return decision

    # --------------------------------------------------------
    # IMPORTANT:
    # Process-state replies must NEVER be forced into
    # performance diagnostics.
    # --------------------------------------------------------

    if _is_process_state_reply(query):
        return {
            "action": "rag",
            "reason": (
                "The user is responding to a previous process "
                "recommendation rather than reporting a new "
                "performance problem."
            ),
            "question": "",
        }

    # --------------------------------------------------------
    # Bluetooth and peripheral problems should use RAG.
    # --------------------------------------------------------

    if _is_device_problem(query):
        return {
            "action": "rag",
            "reason": (
                "The current problem involves a device or "
                "peripheral that is not covered by the "
                "available live network diagnostics."
            ),
            "question": "",
        }

    keyword_route = _keyword_route(
        query,
        conversation_history,
    )

    # --------------------------------------------------------
    # A clear current network problem takes priority.
    # --------------------------------------------------------

    if keyword_route == "network_diagnostics":
        return {
            "action": "network_diagnostics",
            "reason": (
                "The current message describes or continues "
                "a network connectivity problem, so live "
                "network diagnostics are appropriate."
            ),
            "question": "",
        }

    # --------------------------------------------------------
    # A clear current performance problem takes priority.
    # --------------------------------------------------------

    if keyword_route == "performance_diagnostics":
        return {
            "action": "performance_diagnostics",
            "reason": (
                "The current message describes or continues "
                "a performance problem, so live performance "
                "diagnostics are appropriate."
            ),
            "question": "",
        }

    # --------------------------------------------------------
    # Other contextual replies should not automatically
    # trigger another diagnostic.
    # --------------------------------------------------------

    if _is_contextual_follow_up(
        query,
        conversation_history,
    ):
        return {
            "action": "rag",
            "reason": (
                "The current message appears to continue "
                "the previous troubleshooting conversation "
                "without reporting a new diagnostic problem."
            ),
            "question": "",
        }

    return decision


def decide_action(
    query,
    conversation_history=None,
):
    """
    Ask the local LLM to choose the best action for the
    user's current IT problem.
    """

    # --------------------------------------------------------
    # Handle process-state replies before calling the LLM.
    #
    # This is deliberate. Messages such as "I need it" are
    # state updates, not diagnostic requests.
    # --------------------------------------------------------

    if _is_process_state_reply(query):
        return {
            "action": "rag",
            "reason": (
                "The user is responding to a previous process "
                "recommendation and does not report a new "
                "performance failure."
            ),
            "question": "",
        }

    history_text = _format_history(
        conversation_history
    )

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
   Run live disk-space, memory, and process checks for
   computer slowness, freezing, RAM problems, or
   performance issues.

Important routing rules:

- Prioritize the latest explicit user message.
- Use conversation history to understand contextual replies.
- Do not let an older problem override a new explicit problem.
- Distinguish asking for information from reporting a live failure.
- Questions about security concepts, best practices, or how
  to improve a system should normally use RAG.
- Bluetooth, headphones, earbuds, keyboards, mice, printers,
  USB devices, webcams, and other peripheral/device problems
  should use RAG unless a dedicated diagnostic action exists.
- Do NOT classify Bluetooth problems as network diagnostics.
- The available network diagnostics only test ping and DNS.
- The available performance diagnostics test disk space,
  memory, and running processes.
- Prefer diagnostics only when the available checks can
  actually investigate the reported failure.
- Do not invent diagnostic results.

IMPORTANT PROCESS-STATE RULE:

If the user is simply responding to a previous recommendation
about closing an application or process, do NOT start another
full performance diagnostic.

Examples:

Assistant:
"python.exe is using some RAM. If you do not need it,
consider closing it."

User:
"I need it."

Correct action:
rag

Assistant:
"Chrome is using some memory. Consider closing it if
you do not need it."

User:
"I need that also."

Correct action:
rag

Other process-state replies include:

- "I need it"
- "I need that"
- "I still need it"
- "I need that also"
- "I need this also"
- "I can't close it"
- "I cannot close it"
- "I don't want to close it"
- "I need to keep it open"
- "not yet"
- "not now"

These messages are NOT new performance failures.

However, if the user explicitly reports that the computer
is still slow, lagging, freezing, or having high memory usage,
then performance_diagnostics is appropriate.

For example:

User:
"I need Chrome."

This is a process preference, not a performance diagnostic.

User:
"My computer is still slow even after closing Chrome."

This IS a performance problem and should use
performance_diagnostics.

For network troubleshooting:

User:
"I need it."

If this is simply a response to a previous recommendation,
do not start another network diagnostic.

But:

User:
"My internet is still not working."

This IS a network problem and should use
network_diagnostics.

If choosing follow_up, provide one relevant, non-empty question.

Return valid JSON matching the supplied schema.

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