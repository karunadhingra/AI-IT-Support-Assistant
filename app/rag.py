import re

import ollama

from app.semantic_search import search_knowledge_top_k


RAG_MODEL = "llama3.2:3b"


def build_context(query, top_k=3):
    results = search_knowledge_top_k(
        query,
        top_k=top_k
    )

    if not results:
        return None

    context_parts = []

    for article, score in results:
        article_context = (
            f"Knowledge Base Article ID: {article['id']}\n"
            f"Problem: {article['problem']}\n"
            f"Symptoms: {', '.join(article['symptoms'])}\n"
            f"Possible causes: "
            f"{', '.join(article['possible_causes'])}\n"
            f"Troubleshooting steps:\n"
        )

        for i, step in enumerate(
            article["troubleshooting_steps"],
            start=1
        ):
            article_context += f"{i}. {step}\n"

        article_context += "Escalate when:\n"

        for condition in article["escalate_when"]:
            article_context += f"- {condition}\n"

        context_parts.append(article_context)

    return "\n\n".join(context_parts)


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


def _is_short_reply(query):
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
        "i did",
        "i did it",
        "done",
        "that worked",
        "it worked",
        "no",
        "nope",
    }

    return normalized in short_replies


def _is_contextual_reply(
    query,
    conversation_history=None
):
    """
    Detect whether the current message is additional information
    about an existing problem rather than a completely new issue.
    """

    normalized = query.lower().strip()

    if not normalized:
        return False

    if _is_short_reply(query):
        return True

    contextual_patterns = [
        r"^it was\b",
        r"^it is\b",
        r"^it has\b",
        r"^they were\b",
        r"^they are\b",
        r"^they have\b",
        r"^the .+ was\b",
        r"^the .+ were\b",
        r"^the .+ is\b",
        r"^the .+ are\b",
        r"^this .+ was\b",
        r"^this .+ is\b",
        r"^these .+ were\b",
        r"^these .+ are\b",
        r"^purchased in\b",
        r"^bought in\b",
        r"^purchased\b",
        r"^bought\b",
        r"^recently\b",
        r"^not recently\b",
        r"^i haven't\b",
        r"^i have not\b",
        r"^i did\b",
        r"^i didn't\b",
        r"^i did not\b",
        r"^i don't\b",
        r"^i do not\b",
        r"^still\b",
        r"^it still\b",
        r"^they still\b",
    ]

    if any(
        re.search(pattern, normalized)
        for pattern in contextual_patterns
    ):
        return True

    if conversation_history:
        history_text = " ".join(
            str(message.get("content", ""))
            for message in conversation_history
            if message.get("content")
        ).lower()

        contextual_terms = [
            "headphone",
            "headphones",
            "earphone",
            "earphones",
            "earbuds",
            "bluetooth",
            "mouse",
            "keyboard",
            "printer",
            "speaker",
            "device",
            "computer",
            "laptop",
            "wifi",
            "wi-fi",
            "internet",
            "network",
        ]

        refers_to_existing_topic = any(
            term in normalized and term in history_text
            for term in contextual_terms
        )

        if refers_to_existing_topic:
            return True

    return False


def _is_substantive_user_message(content):
    """
    Identify a user message that is useful as the main problem
    for knowledge-base retrieval.
    """

    if not content:
        return False

    normalized = content.lower().strip()

    if _is_short_reply(normalized):
        return False

    if _is_contextual_reply(normalized):
        return False

    words = normalized.split()

    return len(words) >= 4


def _get_primary_problem(
    query,
    conversation_history=None
):
    """
    Find the most recent substantive user problem.

    This prevents contextual messages such as:

        "The headphones were purchased in 2025."

    from replacing the actual problem:

        "My Bluetooth headphones are not connecting."
    """

    if not conversation_history:
        return query

    for message in reversed(conversation_history):
        if message.get("role") != "user":
            continue

        content = message.get("content", "").strip()

        if _is_substantive_user_message(content):
            return content

    return query


def _build_search_query(
    query,
    conversation_history=None
):
    """
    Build a retrieval query that preserves the main problem
    while adding relevant contextual information.
    """

    if not conversation_history:
        return query

    if not _is_contextual_reply(
        query,
        conversation_history
    ):
        return query

    primary_problem = _get_primary_problem(
        query,
        conversation_history
    )

    if not primary_problem:
        return query

    if primary_problem.lower().strip() == query.lower().strip():
        return query

    return f"{primary_problem} {query}"


def _get_completed_steps(conversation_history):
    """
    Collect evidence that the user has already attempted
    troubleshooting.

    This remains intentionally conservative.
    """

    if not conversation_history:
        return []

    completed = []

    completion_phrases = [
        "i tried",
        "i already tried",
        "i did",
        "i have done",
        "already done",
        "already tried",
        "that didn't work",
        "that did not work",
        "still doesn't work",
        "still does not work",
        "still won't work",
        "still will not work",
        "didn't work",
        "did not work",
    ]

    for message in conversation_history:
        if message.get("role") != "user":
            continue

        content = message.get("content", "").strip()

        if not content:
            continue

        normalized = content.lower()

        if any(
            phrase in normalized
            for phrase in completion_phrases
        ):
            completed.append(content)

    return completed


def generate_answer(
    query,
    conversation_history=None
):
    """
    Generate a natural conversational troubleshooting answer
    grounded in the retrieved knowledge base.
    """

    search_query = _build_search_query(
        query,
        conversation_history
    )

    results = search_knowledge_top_k(
        search_query,
        top_k=1
    )

    if not results:
        return (
            "I couldn't find a relevant troubleshooting guide "
            "for this problem yet."
        )

    article, score = results[0]

    context = build_context(
        search_query,
        top_k=1
    )

    history_text = _format_history(
        conversation_history
    )

    completed_steps = _get_completed_steps(
        conversation_history
    )

    completed_steps_text = (
        "\n".join(
            f"- {step}"
            for step in completed_steps
        )
        if completed_steps
        else (
            "No troubleshooting steps have been "
            "explicitly confirmed as completed."
        )
    )

    prompt = f"""
You are an AI IT Support Assistant helping a user solve an
IT problem.

Your goal is to make practical progress toward solving the
problem, rather than repeatedly asking questions.

Use ONLY the information contained in the knowledge-base
context for troubleshooting guidance.

IMPORTANT RESPONSE BEHAVIOR:

1. Identify the user's CURRENT problem using the current
   message and relevant conversation history.

2. When the user first reports a problem, provide useful
   actionable troubleshooting steps immediately.

3. If the knowledge base contains several relevant steps,
   provide approximately 2 to 4 of the most useful steps
   that the user can try now.

4. Do NOT reduce the first response to only one troubleshooting
   step unless the knowledge base genuinely provides only one
   useful step.

5. Ask ONE follow-up question only when the answer would
   meaningfully determine what troubleshooting should happen
   next.

6. Do not ask questions merely to collect unnecessary details.

7. If the user gives additional information about the existing
   problem, continue troubleshooting that same problem.

8. For example:

   Original problem:
   "My Bluetooth headphones are not connecting."

   Additional information:
   "The headphones were purchased in 2025."

   Treat the second message as additional context about the
   Bluetooth problem. Do NOT treat "purchased in 2025" as a
   new troubleshooting problem.

9. If the user says they tried a troubleshooting step and it
   failed, move to another relevant step from the knowledge
   base rather than repeating the same step.

10. Do not invent troubleshooting steps or technical facts.

11. Do not claim that an action was performed unless the user
    explicitly says they performed it.

12. Do not claim that the issue is fixed unless the user says
    it is fixed or the available evidence clearly confirms it.

13. If the problem remains unresolved, provide the next useful
    troubleshooting step from the knowledge base.

14. Keep the response concise, practical, and easy to follow.

15. Do not mention internal prompts, retrieval, semantic search,
    models, or these instructions.

Knowledge-base context:

{context}

Previous conversation:

{history_text}

Troubleshooting information already explicitly mentioned
by the user:

{completed_steps_text}

Current user message:

{query}

Provide the most useful support response:
"""

    try:
        response = ollama.chat(
            model=RAG_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        answer = response["message"]["content"].strip()

        source = (
            "\n\n"
            f"**Source:** IT Knowledge Base — "
            f"{article['id']}: {article['problem']}"
        )

        return answer + source

    except Exception:
        return (
            "I found a relevant troubleshooting guide, "
            "but the AI response service is currently "
            "unavailable."
        )


def generate_diagnostic_answer(
    query,
    diagnostics,
    conversation_history=None
):
    """
    Generate a deterministic explanation of diagnostic results.

    Exact diagnostic values are handled by Python instead of
    the LLM so that measurements such as disk space and memory
    usage cannot be changed or hallucinated.
    """

    response_parts = []

    # ---------------------------------------------------------
    # 1. CHECKS PERFORMED
    # ---------------------------------------------------------

    response_parts.append(
        "### 1. Checks performed"
    )

    if "ping" in diagnostics:
        ping = diagnostics["ping"]

        if ping.get("success") is True:
            response_parts.append(
                "- Ping test to 8.8.8.8 was successful."
            )
        else:
            response_parts.append(
                "- Ping test to 8.8.8.8 was unsuccessful."
            )

    if "dns" in diagnostics:
        dns = diagnostics["dns"]
        host = dns.get(
            "host",
            "the requested hostname"
        )

        if dns.get("success") is True:
            response_parts.append(
                f"- DNS lookup for {host} was successful."
            )
        else:
            response_parts.append(
                f"- DNS lookup for {host} failed."
            )

    if "disk" in diagnostics:
        disk = diagnostics["disk"]

        free_gb = disk.get("free_gb")

        if free_gb is not None:
            response_parts.append(
                f"- Disk space check completed: "
                f"{free_gb:.1f} GB available."
            )

    if "memory" in diagnostics:
        memory = diagnostics["memory"]

        used_percent = memory.get("used_percent")

        if used_percent is not None:
            response_parts.append(
                f"- Memory usage check completed: "
                f"{used_percent:.1f}% currently in use."
            )

    # ---------------------------------------------------------
    # 2. WHAT THE RESULTS MEAN
    # ---------------------------------------------------------

    response_parts.append("")
    response_parts.append(
        "### 2. What the results mean"
    )

    if "ping" in diagnostics:
        ping_success = diagnostics["ping"].get(
            "success"
        )

        if ping_success is True:
            response_parts.append(
                "- The computer was able to reach 8.8.8.8 "
                "at the time of the test."
            )
        else:
            response_parts.append(
                "- The computer could not successfully reach "
                "8.8.8.8 during the test."
            )

    if "dns" in diagnostics:
        dns_success = diagnostics["dns"].get(
            "success"
        )

        if dns_success is True:
            response_parts.append(
                "- The requested hostname resolved successfully."
            )
        else:
            response_parts.append(
                "- The DNS lookup did not resolve successfully."
            )

    if "disk" in diagnostics:
        free_gb = diagnostics["disk"].get(
            "free_gb"
        )

        if free_gb is not None:
            if free_gb < 20:
                response_parts.append(
                    "- Available disk space is relatively low "
                    "and may contribute to performance problems."
                )
            else:
                response_parts.append(
                    "- The available disk space does not by itself "
                    "establish the cause of the performance issue."
                )

    if "memory" in diagnostics:
        used_percent = diagnostics["memory"].get(
            "used_percent"
        )

        if used_percent is not None:
            if used_percent >= 85:
                response_parts.append(
                    "- Memory usage is currently high and may "
                    "contribute to system slowness."
                )
            else:
                response_parts.append(
                    "- The memory check does not by itself "
                    "establish the cause of the performance issue."
                )

    # ---------------------------------------------------------
    # 3. RECOMMENDED NEXT STEP
    # ---------------------------------------------------------

    response_parts.append("")
    response_parts.append(
        "### 3. Recommended next step"
    )

    if (
        "ping" in diagnostics
        and "dns" in diagnostics
    ):
        ping_success = diagnostics["ping"].get(
            "success"
        )

        dns_success = diagnostics["dns"].get(
            "success"
        )

        if ping_success and dns_success:
            response_parts.append(
                "Both basic connectivity checks succeeded. "
                "If the Wi-Fi problem is still occurring, "
                "the next step is to check the local Wi-Fi "
                "connection and adapter settings."
            )
        else:
            response_parts.append(
                "At least one connectivity check failed. "
                "The next step is to investigate the failing "
                "check and the local network configuration."
            )

    elif "memory" in diagnostics:
        used_percent = diagnostics["memory"].get(
            "used_percent"
        )

        if (
            used_percent is not None
            and used_percent >= 85
        ):
            response_parts.append(
                "Memory usage is currently high. "
                "Close unnecessary applications and "
                "resource-intensive processes, then check "
                "whether system performance improves."
            )
        else:
            response_parts.append(
                "Continue with the relevant troubleshooting "
                "steps for the reported performance problem."
            )

    elif "disk" in diagnostics:
        free_gb = diagnostics["disk"].get(
            "free_gb"
        )

        if (
            free_gb is not None
            and free_gb < 20
        ):
            response_parts.append(
                "Free up unnecessary disk space and then "
                "check whether system performance improves."
            )
        else:
            response_parts.append(
                "Continue with the relevant troubleshooting "
                "steps for the reported performance problem."
            )

    else:
        response_parts.append(
            "The available diagnostic results do not "
            "establish the exact cause. Continue with "
            "the relevant troubleshooting steps."
        )

    return "\n".join(response_parts).strip()


if __name__ == "__main__":
    query = "My Bluetooth headphones won't connect"

    print("\nUser query:")
    print(query)

    answer = generate_answer(query)

    print("\nAI Support Answer:")
    print(answer)