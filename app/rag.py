import re
import ollama

from app.semantic_search import (
    format_article_response,
    search_knowledge_top_k,
)


RAG_MODEL = "llama3.2:3b"


def build_context(query, top_k=3):
    results = search_knowledge_top_k(query, top_k=top_k)

    if not results:
        return None

    context_parts = []

    for article, score in results:
        article_context = (
            f"Knowledge Base Article ID: {article['id']}\n"
            f"Problem: {article['problem']}\n"
            f"Symptoms: {', '.join(article['symptoms'])}\n"
            f"Possible causes: {', '.join(article['possible_causes'])}\n"
            f"Troubleshooting steps:\n"
        )

        for i, step in enumerate(article["troubleshooting_steps"], start=1):
            article_context += f"{i}. {step}\n"

        article_context += "Escalate when:\n"

        for condition in article["escalate_when"]:
            article_context += f"- {condition}\n"

        context_parts.append(article_context)

    return "\n\n".join(context_parts)


def _clean_history(query, conversation_history):
    if not conversation_history:
        return []

    history = list(conversation_history)
    if (
        history
        and history[-1].get("role") == "user"
        and str(history[-1].get("content", "")).strip() == str(query).strip()
    ):
        history = history[:-1]

    return history


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
        "check",
        "check it",
        "i did",
        "i did it",
        "done",
        "that worked",
        "it worked",
        "no",
        "nope",
    }

    return normalized in short_replies


def _is_contextual_reply(query, conversation_history=None):
    normalized = re.sub(r"[^\w\s'.-]", " ", query.lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()

    if not normalized:
        return False

    if _is_short_reply(normalized):
        return True

    stripped = re.sub(
        r"^(yes|yeah|yep|yup|no|nope|ok|okay|sure|well|actually)\s+",
        "",
        normalized,
    ).strip()

    if _is_short_reply(stripped):
        return True

    contextual_phrases = [
        "how to",
        "how do i",
        "how can i",
        "where is",
        "where do i",
        "what is",
        "explain",
        "i need",
        "i still need",
        "need it",
        "need that",
        "need this",
        "i am using",
        "using it",
        "can't close",
        "cannot close",
        "keep it open",
        "keep that open",
        "i closed",
        "already closed",
        "i tried",
        "already tried",
        "i did",
        "i didn't",
        "i did not",
        "didn't work",
        "did not work",
        "doesn't work",
        "does not work",
        "not comfortable",
        "uncomfortable",
        "don't want to change",
        "do not want to change",
        "something else",
        "other steps",
        "another step",
        "still",
        "purchased",
        "bought",
        "not now",
        "not yet",
    ]

    if any(phrase in normalized for phrase in contextual_phrases):
        return True

    contextual_patterns = [
        r"^(it|they|this|that|these|those) (was|is|has|were|are|have|still)\b",
        r"^the .+ (was|were|is|are)\b",
        r"^(i|we) (have|haven't|have not|don't|do not|can't|cannot)\b",
    ]

    if any(
        re.search(pattern, normalized) or re.search(pattern, stripped)
        for pattern in contextual_patterns
    ):
        return True

    if conversation_history and len(normalized.split()) <= 6:
        return True

    return False


def _is_substantive_user_message(content):
    if not content:
        return False

    normalized = content.lower().strip()

    if _is_short_reply(normalized):
        return False

    if _is_contextual_reply(normalized):
        return False

    words = normalized.split()
    return len(words) >= 3


def _get_primary_problem(query, conversation_history=None):
    """
    Scan BACKWARDS from the most recent user message so if the user
    switched topics (e.g. from slow computer to Wi-Fi), we always
    retrieve the latest substantive IT problem!
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


def _build_search_query(query, conversation_history=None):
    if not conversation_history:
        return query

    if not _is_contextual_reply(query, conversation_history):
        return query

    primary_problem = _get_primary_problem(query, conversation_history)

    if not primary_problem:
        return query

    if primary_problem.lower().strip() == query.lower().strip():
        return query

    return f"{primary_problem} {query}"


def get_unshown_article_steps(article, conversation_history):
    """
    Return the troubleshooting steps from `article` that:
    1. Do NOT repeat automated diagnostics (Task Manager, RAM/CPU check, storage space check), AND
    2. Have NOT already been shown in previous assistant messages.
    """
    all_steps = article.get("troubleshooting_steps", [])

    redundant_diagnostic_phrases = [
        "open task manager",
        "system monitor",
        "check which applications are using high cpu",
        "enough free storage space",
        "close applications that are not currently being used",
        "disable unnecessary applications from starting automatically",
    ]

    filtered_steps = [
        step
        for step in all_steps
        if not any(p in step.lower() for p in redundant_diagnostic_phrases)
    ]

    if article.get("id") == "performance_001" or len(filtered_steps) < 3:
        if article.get("id") == "performance_001":
            filtered_steps = [
                "Close unused browser tabs or enable Sleeping Tabs in your browser to free up RAM immediately.",
                "Make sure Battery Saver / Energy Saver mode is turned off and Windows Power Mode is set to Balanced or Best Performance.",
                "Pause active cloud sync tools (such as OneDrive, Dropbox, or Google Drive) and wait for any background Windows Updates to finish.",
                "Clear temporary Windows cache files by opening Storage Settings or running Disk Cleanup.",
                "Turn off visual transparency and animation effects in Windows Accessibility > Visual Effects to reduce UI lag.",
                "Save your open work and perform a full Windows Restart (Start -> Power -> Restart) to clear cached system memory.",
            ]
        else:
            filtered_steps = list(all_steps)

    if not conversation_history:
        return filtered_steps, []

    assistant_text = " ".join(
        str(msg.get("content", "")).lower()
        for msg in conversation_history
        if msg.get("role") == "assistant"
    )

    unshown = []
    shown = []

    for step in filtered_steps:
        step_clean = step.lower().strip()
        prefix = step_clean[:35]
        if prefix in assistant_text:
            shown.append(step)
        else:
            unshown.append(step)

    return unshown, shown


def get_next_troubleshooting_batch(query, conversation_history=None, batch_size=2):
    clean_hist = _clean_history(query, conversation_history)
    primary = _get_primary_problem(query, clean_hist)

    results = search_knowledge_top_k(primary, top_k=1)
    if not results:
        search_query = _build_search_query(query, clean_hist)
        results = search_knowledge_top_k(search_query, top_k=1)

    if not results:
        return None, [], []

    article, _ = results[0]
    unshown_steps, shown_steps = get_unshown_article_steps(article, clean_hist)

    return article, unshown_steps[:batch_size], shown_steps


def _get_completed_steps(conversation_history):
    if not conversation_history:
        return []

    completed = []
    for message in conversation_history:
        if message.get("role") != "user":
            continue
        content = message.get("content", "").strip()
        if content:
            completed.append(content)

    return completed


def generate_answer(query, conversation_history=None):
    """
    Generate a grounded troubleshooting or how-to answer from the knowledge base.
    """
    clean_hist = _clean_history(query, conversation_history)
    search_query = _build_search_query(query, clean_hist)

    results = search_knowledge_top_k(search_query, top_k=2)

    if not results and clean_hist:
        primary_problem = _get_primary_problem(query, clean_hist)
        if primary_problem and primary_problem != search_query:
            results = search_knowledge_top_k(primary_problem, top_k=2)

    if not results:
        return (
            "I couldn't find a relevant troubleshooting guide "
            "for this problem yet."
        )

    article, score = results[0]
    context = build_context(article["problem"], top_k=1)
    history_text = _format_history(clean_hist)
    completed_steps = _get_completed_steps(clean_hist)

    completed_steps_text = (
        "\n".join(f"- {step}" for step in completed_steps)
        if completed_steps
        else "No troubleshooting steps have been explicitly confirmed as completed."
    )

    prompt = f"""
You are an AI IT Support Assistant helping a user solve an IT problem.

IMPORTANT RULES:
1. If the user is asking HOW to perform a specific step (e.g., "how to disable startup applications", "how to check Wi-Fi adapter settings", "how to flush DNS"), give clear, numbered step-by-step instructions on how to do that exact action on Windows, then ask if that helped.
2. Otherwise, briefly state the likely cause in 1 sentence and provide 2 to 3 actionable numbered troubleshooting steps from the knowledge base that have NOT already been suggested in the previous conversation.
3. NEVER repeat troubleshooting steps that were already given in the previous conversation.
4. NEVER ask "Are you comfortable adjusting system settings?".
5. End with ONE simple check-in question: "Did these steps help resolve the issue, or is it still happening?"

Knowledge-base context:
{context}

Previous conversation:
{history_text}

User updates so far:
{completed_steps_text}

Current user message:
{query}

Provide a concise, practical support response:
"""

    source = (
        "\n\n"
        f"**Source:** IT Knowledge Base — "
        f"{article['id']}: {article['problem']}"
    )

    try:
        response = ollama.chat(
            model=RAG_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        answer = response["message"]["content"].strip()
        return answer + source

    except Exception:
        fallback_guide = format_article_response(article)
        return (
            "I found a relevant troubleshooting guide, "
            "but the AI response service is currently unavailable.\n\n"
            f"{fallback_guide}{source}"
        )


def generate_diagnostic_answer(query, diagnostics, conversation_history=None):
    response_parts = ["### 1. Checks performed"]

    if "ping" in diagnostics:
        if diagnostics["ping"].get("success") is True:
            response_parts.append("- Ping test to 8.8.8.8 was successful.")
        else:
            response_parts.append("- Ping test to 8.8.8.8 was unsuccessful.")

    if "dns" in diagnostics:
        dns = diagnostics["dns"]
        host = dns.get("host", "the requested hostname")
        if dns.get("success") is True:
            response_parts.append(f"- DNS lookup for {host} was successful.")
        else:
            response_parts.append(f"- DNS lookup for {host} failed.")

    if "disk" in diagnostics:
        free_gb = diagnostics["disk"].get("free_gb")
        if free_gb is not None:
            response_parts.append(
                f"- Disk space check completed: {free_gb:.1f} GB available."
            )

    if "memory" in diagnostics:
        used_percent = diagnostics["memory"].get("used_percent")
        if used_percent is not None:
            response_parts.append(
                f"- Memory usage check completed: {used_percent:.1f}% currently in use."
            )

    if "processes" in diagnostics:
        proc_count = diagnostics["processes"].get("process_count")
        if proc_count is not None:
            response_parts.append(
                f"- Running processes inspected: {proc_count} active processes."
            )

    response_parts.append("")
    response_parts.append("### 2. What the results mean")

    if "ping" in diagnostics:
        if diagnostics["ping"].get("success") is True:
            response_parts.append(
                "- Your computer can reach external internet servers (8.8.8.8)."
            )
        else:
            response_parts.append(
                "- Your computer could not reach 8.8.8.8, indicating a connectivity outage."
            )

    if "dns" in diagnostics:
        if diagnostics["dns"].get("success") is True:
            response_parts.append(
                "- Domain names (like google.com) are resolving properly."
            )
        else:
            response_parts.append(
                "- DNS resolution failed, meaning websites cannot load by domain name."
            )

    if "disk" in diagnostics:
        free_gb = diagnostics["disk"].get("free_gb")
        if free_gb is not None:
            if free_gb < 20:
                response_parts.append(
                    f"- Available disk space ({free_gb:.1f} GB) is relatively low and may slow down the system."
                )
            else:
                response_parts.append(
                    f"- Available disk space ({free_gb:.1f} GB) is healthy and not the cause of slowness."
                )

    if "memory" in diagnostics:
        used_percent = diagnostics["memory"].get("used_percent")
        if used_percent is not None:
            if used_percent >= 85:
                response_parts.append(
                    f"- Memory usage ({used_percent:.1f}%) is high and likely contributing to system lag."
                )
            else:
                response_parts.append(
                    f"- Overall RAM usage ({used_percent:.1f}%) is within normal range."
                )

    response_parts.append("")
    response_parts.append("### 3. Recommended next step")

    if "ping" in diagnostics and "dns" in diagnostics:
        ping_ok = diagnostics["ping"].get("success")
        dns_ok = diagnostics["dns"].get("success")

        if ping_ok and dns_ok:
            response_parts.append(
                "Both live connectivity checks succeeded on your computer. Please try these two steps:\n"
                "1. Turn Wi-Fi **Off** and back **On** in your taskbar network menu to refresh your wireless adapter.\n"
                "2. Try opening the webpage in an Incognito/Private window or a different browser.\n\n"
                "Did that fix your connection, or are websites still failing to load?"
            )
        else:
            response_parts.append(
                "At least one connectivity check failed. Please check that Wi-Fi is enabled and restart your Wi-Fi router. Let me know if the connection comes back."
            )
    elif "memory" in diagnostics or "disk" in diagnostics:
        used_percent = diagnostics.get("memory", {}).get("used_percent")
        free_gb = diagnostics.get("disk", {}).get("free_gb")

        if used_percent is not None and used_percent >= 85:
            response_parts.append(
                "Memory usage is currently high. Close unnecessary applications, or let me know if you need your current applications open so I can suggest alternative fixes."
            )
        elif free_gb is not None and free_gb < 20:
            response_parts.append(
                "Free up unnecessary disk space and check whether system performance improves."
            )
        else:
            response_parts.append(
                "Continue with the guided troubleshooting steps for the reported performance problem."
            )
    else:
        response_parts.append(
            "Continue with the relevant troubleshooting steps."
        )

    return "\n\n".join(response_parts).strip()