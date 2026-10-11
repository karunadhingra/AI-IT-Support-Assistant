import json
import re
import ollama


AGENT_MODEL = "llama3.2:3b"

VALID_ACTIONS = {
    "follow_up",
    "rag",
    "network_diagnostics",
    "performance_diagnostics",
}


def _format_history(conversation_history):
    if not conversation_history:
        return "No previous conversation."

    lines = []

    for message in conversation_history:
        role = message.get("role", "unknown")
        content = message.get("content", "")

        if content:
            lines.append(f"{role}: {content}")

    return "\n".join(lines) if lines else "No previous conversation."


def _extract_json_object(raw_text):
    if not raw_text:
        return None

    raw_text = raw_text.strip()

    try:
        return json.loads(raw_text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _normalize_query(query):
    normalized = re.sub(r"[^\w\s'-]", " ", str(query).lower())
    return re.sub(r"\s+", " ", normalized).strip()


def _is_vague_problem_statement(query):
    """
    Deterministically detect vague problem statements like:
    - "my computer has a problem"
    - "something is wrong with my laptop"
    - "my pc is not working"
    - "i need help with my computer"
    that do NOT mention any specific symptom or component.
    """
    normalized = _normalize_query(query)
    if not normalized:
        return True

    specific_keywords = {
        "slow", "slowly", "lag", "lagging", "freeze", "freezing", "hang", "hanging",
        "ram", "memory", "cpu", "disk", "storage", "space", "full", "startup",
        "wifi", "wi-fi", "internet", "network", "dns", "website", "websites", "browser",
        "ethernet", "lan", "vpn", "connected", "disconnect", "disconnecting", "connection",
        "bluetooth", "headphone", "headphones", "earbuds", "speaker", "speakers",
        "sound", "audio", "mic", "microphone", "volume", "mute",
        "printer", "print", "printing", "scanner",
        "monitor", "screen", "display", "flicker", "black", "blue", "bsod", "crash", "hdmi",
        "keyboard", "keys", "typing", "mouse", "touchpad", "cursor", "click",
        "usb", "port", "drive", "flash",
        "battery", "charge", "charging", "charger", "power", "turn on", "boot",
        "hot", "overheat", "overheating", "fan", "loud", "thermal",
        "password", "login", "locked", "account", "sign in",
        "update", "windows update", "install", "software", "app", "application",
        "outlook", "email", "teams", "zoom", "chrome", "code", "python",
    }

    words = set(normalized.split())
    if words.intersection(specific_keywords):
        return False

    for kw in specific_keywords:
        if " " in kw and kw in normalized:
            return False

    vague_patterns = [
        r"^(my )?(computer|laptop|pc|system|device|machine) (has a |is having a )?(problem|issue|trouble|error|bug)s?$",
        r"^(my )?(computer|laptop|pc|system|device|machine) (is not|isn't|isnt|won't|wont) working$",
        r"^something is (wrong|broken|not working)( with my (computer|laptop|pc|system))?$",
        r"^(i have|there is) a (problem|issue)( with my (computer|laptop|pc|system))?$",
        r"^(help|need help|i need help|can you help|please help)( me)?( with my (computer|laptop|pc))?$",
        r"^(it|this) (is not|isn't|isnt) working$",
        r"^not working$",
    ]

    return any(re.search(pattern, normalized) for pattern in vague_patterns)


def _is_short_confirmation_or_update(query):
    normalized = _normalize_query(query)

    short_messages = {
        "yes",
        "yeah",
        "yep",
        "no",
        "nope",
        "ok",
        "okay",
        "sure",
        "done",
        "i did",
        "i did that",
        "i tried",
        "i tried that",
        "already tried",
        "tried that",
        "not yet",
        "not now",
        "i need it",
        "i need that",
        "i need this",
        "i still need it",
        "i still need that",
        "i still need this",
        "i can't close it",
        "i cannot close it",
        "keep it open",
        "keep this open",
        "keep that open",
        "i closed it",
        "already closed",
    }

    return normalized in short_messages


def _is_contextual_follow_up(query, conversation_history=None):
    if not conversation_history:
        return False

    if _is_vague_problem_statement(query):
        return False

    normalized = _normalize_query(query)

    if not normalized:
        return False

    if _is_short_confirmation_or_update(normalized):
        return True

    follow_up_patterns = [
        r"^i (still )?(need|want|use|am using|m using)\b",
        r"^i (can't|cannot|don't want to|do not want to) close\b",
        r"^i (already )?(closed|restarted|tried|checked|updated|disabled|disconnected|unplugged)\b",
        r"^(it|that|this|they) (is|was|are|were|still|didn't|did not|doesn't|does not)\b",
        r"^(the )?(app|application|process|program|device|headphones|speaker|printer|keyboard|mouse|monitor|usb)\b",
        r"^still (not|the same|having)\b",
        r"^(didn't|did not|doesn't|does not) work\b",
        r"^not comfortable\b",
    ]

    return any(re.search(pattern, normalized) for pattern in follow_up_patterns)


def _has_explicit_network_failure(query):
    normalized = _normalize_query(query)

    if _is_vague_problem_statement(normalized):
        return False

    network_keywords = [
        "wifi",
        "wi-fi",
        "internet",
        "network",
        "dns",
        "website",
        "websites",
        "browser",
        "ethernet",
        "lan",
        "connection",
        "disconnect",
        "disconnected",
        "disconnecting",
        "online",
    ]

    exclusion_keywords = [
        "bluetooth",
        "headphone",
        "headphones",
        "earbud",
        "earbuds",
        "airpods",
        "speaker",
        "speakers",
        "microphone",
        "mic",
        "audio",
        "sound",
        "usb",
        "mouse",
        "keyboard",
        "printer",
        "monitor",
        "hdmi",
        "charger",
        "battery",
    ]

    if any(word in normalized for word in exclusion_keywords):
        return False

    if any(word in normalized for word in network_keywords):
        return True

    network_patterns = [
        r"\bno internet\b",
        r"\bcannot connect to (the )?(internet|wifi|wi-fi|network)\b",
        r"\bcan't connect to (the )?(internet|wifi|wi-fi|network)\b",
        r"\bwebsites? (are not|aren't|won't|will not) (loading|opening)\b",
        r"\bpages? (are not|aren't|won't|will not) (loading|opening)\b",
        r"\binternet is (down|slow|not working|disconnected)\b",
        r"\bwifi is (down|slow|not working|disconnected)\b",
        r"\bwi-fi is (down|slow|not working|disconnected)\b",
    ]

    return any(re.search(pattern, normalized) for pattern in network_patterns)


def _has_explicit_performance_failure(query):
    normalized = _normalize_query(query)

    if _is_vague_problem_statement(normalized):
        return False

    exclusion_keywords = [
        "internet",
        "wifi",
        "wi-fi",
        "network",
        "website",
        "websites",
        "download",
        "upload",
        "bluetooth",
        "printer",
        "audio",
        "sound",
    ]

    if any(word in normalized for word in exclusion_keywords):
        return False

    performance_patterns = [
        r"\bslow\b",
        r"\bslowly\b",
        r"\btaking a long time\b",
        r"\btakes a long time\b",
        r"\bslow performance\b",
        r"\bsystem lag\b",
        r"\b(lagging|freezing|hanging|stuttering)\b",
        r"\bhigh (cpu|memory|ram|disk)\b",
        r"\b(memory|ram|cpu|disk) usage is high\b",
        r"\blow disk space\b",
        r"\bdisk is full\b",
        r"\bout of (memory|ram|disk space|storage)\b",
        r"\bstorage is full\b",
    ]

    return any(re.search(pattern, normalized) for pattern in performance_patterns)


def _validate_current_problem_route(query, decision, conversation_history=None):
    """
    Guardrail so deterministic rules prevent misrouting or endless
    follow-up questions from the small LLM.
    """
    if not isinstance(decision, dict):
        return {
            "action": "rag",
            "reason": "Fallback to knowledge-base retrieval.",
            "question": "",
        }

    # 1. FIRST: Check if the message explicitly describes a Performance or Network issue!
    # (e.g., "the computer is slow"[cite: 22], "my wifi is not working")
    if _has_explicit_performance_failure(query):
        return {
            "action": "performance_diagnostics",
            "reason": "The current message explicitly describes a system performance, memory, CPU, or disk issue.",
            "question": "",
        }

    if _has_explicit_network_failure(query):
        return {
            "action": "network_diagnostics",
            "reason": "The current message explicitly describes a network or internet connectivity issue.",
            "question": "",
        }

    # 2. SECOND: If we are already in an ongoing conversation (conversation_history is not empty),
    # NEVER allow another `follow_up` question! Route straight to RAG or diagnostics.
    if conversation_history:
        return {
            "action": "rag",
            "reason": (
                "The conversation is already in progress; proceeding directly "
                "to troubleshooting instead of asking another follow-up question."
            ),
            "question": "",
        }

    # 3. THIRD: Only on Turn 1, if the user's message is genuinely vague
    # (e.g., "my computer has a problem"[cite: 20, 21]), ask ONE clarifying question.
    if _is_vague_problem_statement(query):
        question = decision.get("question", "").strip()
        if not question:
            question = (
                "Could you tell me a bit more about what's happening with your computer? "
                "For example, is it running slowly, having trouble connecting to Wi-Fi, "
                "or having an issue with audio, display, or another device?"
            )
        return {
            "action": "follow_up",
            "reason": "The user reported a vague problem without specifying symptoms.",
            "question": question,
        }

    # 4. Allow LLM follow_up on Turn 1 if it provided a valid question
    if decision.get("action") == "follow_up" and decision.get("question"):
        return decision

    # 5. Otherwise, go straight to Knowledge Base (RAG) troubleshooting!
    return {
        "action": "rag",
        "reason": decision.get(
            "reason",
            "Knowledge-base guidance is the best fit for the current query.",
        ),
        "question": "",
    }


def decide_action(query, conversation_history=None):
    """
    Use the LLM agent to decide how the system should handle
    the user's request, then validate the decision so the
    active problem in the current message takes priority.
    """
    if not query or not str(query).strip():
        return {
            "action": "follow_up",
            "reason": "The query is empty or unclear.",
            "question": "Could you describe the IT issue you are experiencing?",
        }

    history_text = _format_history(conversation_history)

    prompt = f"""
You are the decision-making agent for an AI IT Support Assistant.

Your job is to inspect the user's CURRENT message and the recent conversation
history, then choose the single best action.

Available actions:

1. "follow_up"
Choose this ONLY when the user's problem is still too vague to diagnose or
search effectively (for example: "my computer has a problem"[cite: 20, 21], "something is broken").
If you choose "follow_up", provide ONE short, specific clarifying question.

2. "rag"
Choose this when the user is asking for troubleshooting steps, explanations,
or follow-up help that can be answered from the IT knowledge base, OR when the
current message is about devices/peripherals/audio/bluetooth/software/hardware
rather than internet connectivity or computer slowness.

3. "network_diagnostics"
Choose this ONLY when the user's CURRENT problem is specifically about internet,
Wi-Fi, DNS, network connectivity, or websites failing to load.

4. "performance_diagnostics"
Choose this ONLY when the user's CURRENT problem is specifically about slow
computer performance, freezing, high memory usage, high CPU usage, or low disk space.

Conversation history:
{history_text}

Current user message:
{query}

Return ONLY valid JSON in this exact format:
{{
  "action": "follow_up | rag | network_diagnostics | performance_diagnostics",
  "reason": "brief explanation",
  "question": "clarifying question if action is follow_up, otherwise empty string"
}}
"""

    try:
        response = ollama.chat(
            model=AGENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        raw_content = response["message"]["content"]
        parsed = _extract_json_object(raw_content)

        if not parsed:
            fallback = {
                "action": "rag",
                "reason": "Model output was not valid JSON; defaulting to RAG.",
                "question": "",
            }
            return _validate_current_problem_route(
                query,
                fallback,
                conversation_history=conversation_history,
            )

        action = str(parsed.get("action", "")).strip()
        reason = str(parsed.get("reason", "")).strip()
        question = str(parsed.get("question", "")).strip()

        if action not in VALID_ACTIONS:
            fallback = {
                "action": "rag",
                "reason": "Invalid action returned by model; defaulting to RAG.",
                "question": "",
            }
            return _validate_current_problem_route(
                query,
                fallback,
                conversation_history=conversation_history,
            )

        if action == "follow_up" and not question:
            question = (
                "Could you tell me a little more about what is happening "
                "and when the issue started?"
            )

        if action != "follow_up":
            question = ""

        decision = {
            "action": action,
            "reason": reason or "Action selected by agent.",
            "question": question,
        }

        return _validate_current_problem_route(
            query,
            decision,
            conversation_history=conversation_history,
        )

    except Exception as exc:
        fallback = {
            "action": "rag",
            "reason": f"Agent model unavailable ({exc}); defaulting to RAG.",
            "question": "",
        }
        return _validate_current_problem_route(
            query,
            fallback,
            conversation_history=conversation_history,
        )