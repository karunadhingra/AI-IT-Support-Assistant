import re

from app.agent import decide_action
from app.rag import generate_answer, generate_diagnostic_answer
from app.diagnostics.network import ping_host
from app.diagnostics.dns import dns_lookup
from app.diagnostics.disk import check_disk_space
from app.diagnostics.memory import check_memory
from app.diagnostics.processes import get_top_processes
from app.escalation import create_support_ticket, should_escalate


# ============================================================
# PROCESS / CONVERSATION STATE
# ============================================================


PROCESS_ALIASES = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "python": "python.exe",
    "python3": "python.exe",
    "code": "code.exe",
    "visual studio code": "code.exe",
    "canva": "canva.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "firefox": "firefox.exe",
    "discord": "discord.exe",
    "teams": "teams.exe",
    "spotify": "spotify.exe",
    "slack": "slack.exe",
    "zoom": "zoom.exe",
    "whatsapp": "whatsapp.exe",
    "dropbox": "dropbox.exe",
    "onedrive": "onedrive.exe",
}


def _normalize_process_name(name):
    """
    Normalize a process name so comparisons are consistent.

    Examples:

        Chrome       -> chrome.exe
        chrome.exe   -> chrome.exe
        Python       -> python.exe
        Code         -> code.exe
    """

    if not name:
        return ""

    normalized = str(name).strip().lower()

    if normalized in PROCESS_ALIASES:
        return PROCESS_ALIASES[normalized]

    if not normalized.endswith(".exe"):
        normalized = f"{normalized}.exe"

    return normalized


def _extract_process_name_from_text(text):
    """
    Try to extract a Windows executable/process name from
    conversational text.

    Examples:

        "I need Chrome"
        "I need python.exe"
        "I can't close Code.exe"
        "I closed chrome.exe and it worked"

    Returns a normalized executable name.
    """

    if not text:
        return None

    text = str(text)

    # --------------------------------------------------------
    # First look for explicit executable names.
    # --------------------------------------------------------

    executable_matches = re.findall(
        r"\b[a-zA-Z0-9_.-]+\.exe\b",
        text,
        flags=re.IGNORECASE,
    )

    if executable_matches:
        return _normalize_process_name(
            executable_matches[-1]
        )

    # --------------------------------------------------------
    # Then look for common application names.
    # --------------------------------------------------------

    normalized = text.lower()

    # Longer names first so that
    # "google chrome" is checked before "chrome".
    known_applications = sorted(
        PROCESS_ALIASES.keys(),
        key=len,
        reverse=True,
    )

    for application in known_applications:
        if re.search(
            rf"\b{re.escape(application)}\b",
            normalized,
        ):
            return _normalize_process_name(
                application
            )

    return None


def _extract_process_from_previous_assistant(
    conversation_history,
):
    """
    Find the process most recently recommended by the assistant.

    This is used for replies such as:

        "I need it"
        "I need that"
        "I need that also"
        "I can't close it"

    Example:

        Assistant:
        "chrome.exe is using 5.1% RAM..."

        User:
        "I need it"

    The function resolves "it" to chrome.exe.
    """

    if not conversation_history:
        return None

    for message in reversed(conversation_history):
        role = message.get("role")

        if role != "assistant":
            continue

        content = str(
            message.get("content", "")
        ).strip()

        if not content:
            continue

        process_name = _extract_process_name_from_text(
            content
        )

        if process_name:
            return process_name

    return None


def _is_process_state_message(text):
    """
    Detect whether a user message is simply describing
    what they want to do with a previously recommended
    application/process.

    These messages update conversation state rather than
    requesting another diagnostic.
    """

    if not text:
        return False

    normalized = re.sub(
        r"\s+",
        " ",
        str(text).lower().strip(),
    )

    exact_messages = {
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
        "keep this open",
        "keep that open",
        "not now",
        "not yet",
    }

    if normalized in exact_messages:
        return True

    patterns = [
        r"^i need (it|that|this)\b",
        r"^i still need (it|that|this)\b",
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
        re.search(
            pattern,
            normalized,
        )
        for pattern in patterns
    )


def _extract_process_state(conversation_history):
    """
    Build persistent process state from the conversation.

    The assistant remembers processes that the user explicitly
    said they need or have already dealt with.

    Pronoun-based replies such as "I need it" are resolved
    against the most recent process recommended by the assistant.

    Returns:

        {
            "required_processes": [...],
            "excluded_processes": [...]
        }
    """

    required_processes = set()
    excluded_processes = set()

    if not conversation_history:
        return {
            "required_processes": [],
            "excluded_processes": [],
        }

    for index, message in enumerate(
        conversation_history
    ):

        role = message.get("role")

        content = str(
            message.get("content", "")
        ).strip()

        if not content:
            continue

        normalized = content.lower()

        # ----------------------------------------------------
        # USER MESSAGES
        # ----------------------------------------------------

        if role != "user":
            continue

        process_name = _extract_process_name_from_text(
            content
        )

        # ----------------------------------------------------
        # If the user did not mention a process explicitly,
        # resolve "it / that / this" from the latest assistant
        # recommendation before this user message.
        # ----------------------------------------------------

        if not process_name and _is_process_state_message(
            content
        ):
            previous_messages = conversation_history[
                :index
            ]

            process_name = (
                _extract_process_from_previous_assistant(
                    previous_messages
                )
            )

        if not process_name:
            continue

        normalized_process = _normalize_process_name(
            process_name
        )

        # ----------------------------------------------------
        # User explicitly says they need the process.
        # ----------------------------------------------------

        needs_patterns = [
            r"\bi need\b",
            r"\bi still need\b",
            r"\bi want\b",
            r"\bi still want\b",
            r"\bi use\b",
            r"\bi am using\b",
            r"\bi'm using\b",
            r"\bkeep it open\b",
            r"\bneed to keep\b",
        ]

        user_needs_process = any(
            re.search(
                pattern,
                normalized,
            )
            for pattern in needs_patterns
        )

        if user_needs_process:

            required_processes.add(
                normalized_process
            )

            excluded_processes.add(
                normalized_process
            )

        # ----------------------------------------------------
        # User says they cannot / don't want to close it.
        # ----------------------------------------------------

        cannot_close_patterns = [
            r"\bi can't close\b",
            r"\bi cannot close\b",
            r"\bdon't want to close\b",
            r"\bdo not want to close\b",
            r"\bcan't close\b",
            r"\bcannot close\b",
        ]

        user_will_keep_process = any(
            re.search(
                pattern,
                normalized,
            )
            for pattern in cannot_close_patterns
        )

        if user_will_keep_process:

            required_processes.add(
                normalized_process
            )

            excluded_processes.add(
                normalized_process
            )

        # ----------------------------------------------------
        # User says they closed it.
        # ----------------------------------------------------

        closed_patterns = [
            r"\bi closed\b",
            r"\bi have closed\b",
            r"\bi already closed\b",
            r"\bclosed it\b",
            r"\bclosed the app\b",
            r"\bclosed the application\b",
        ]

        user_closed_process = any(
            re.search(
                pattern,
                normalized,
            )
            for pattern in closed_patterns
        )

        if user_closed_process:

            excluded_processes.add(
                normalized_process
            )

    return {
        "required_processes": sorted(
            required_processes
        ),
        "excluded_processes": sorted(
            excluded_processes
        ),
    }


# ============================================================
# ROUTING
# ============================================================


def route_issue(
    query,
    conversation_history=None,
):

    decision = decide_action(
        query,
        conversation_history=conversation_history,
    )

    action_to_route = {
        "follow_up": "follow_up",
        "rag": "rag",
        "network_diagnostics": "network",
        "performance_diagnostics": "performance",
    }

    return action_to_route.get(
        decision.get("action"),
        "rag",
    )


# ============================================================
# DIAGNOSTICS
# ============================================================


def run_diagnostics(
    route,
    conversation_history=None,
):
    """
    Run the appropriate live diagnostic checks.

    Performance diagnostics are conversation-aware so that
    processes the user explicitly needs or has already dealt
    with are not repeatedly recommended.
    """

    if route == "network":

        return {
            "ping": ping_host("8.8.8.8"),
            "dns": dns_lookup("google.com"),
        }

    if route == "performance":

        process_state = _extract_process_state(
            conversation_history
        )

        diagnostics = {
            "disk": check_disk_space(),
            "memory": check_memory(),
            "processes": get_top_processes(
                excluded_processes=(
                    process_state[
                        "excluded_processes"
                    ]
                ),
                required_processes=(
                    process_state[
                        "required_processes"
                    ]
                ),
            ),
        }

        diagnostics["process_state"] = process_state

        return diagnostics

    return {}


# ============================================================
# MAIN QUERY HANDLER
# ============================================================


def handle_query(
    query,
    conversation_history=None,
):

    decision = decide_action(
        query,
        conversation_history=conversation_history,
    )

    action = decision.get(
        "action",
        "rag",
    )

    # --------------------------------------------------------
    # FOLLOW-UP
    # --------------------------------------------------------

    if action == "follow_up":

        question = decision.get(
            "question",
            "Could you provide a little more information about the problem?",
        )

        return {
            "route": "follow_up",
            "answer": question,
            "question": question,
            "agent_decision": decision,
        }

    # --------------------------------------------------------
    # RAG
    # --------------------------------------------------------

    if action == "rag":

        answer = generate_answer(
            query,
            conversation_history=conversation_history,
        )

        return {
            "route": "rag",
            "answer": answer,
            "agent_decision": decision,
        }

    # --------------------------------------------------------
    # DIAGNOSTIC ROUTE
    # --------------------------------------------------------

    if action == "network_diagnostics":

        route = "network"

    elif action == "performance_diagnostics":

        route = "performance"

    else:

        route = "rag"

    # --------------------------------------------------------
    # RUN DIAGNOSTICS
    # --------------------------------------------------------

    try:

        diagnostics = run_diagnostics(
            route,
            conversation_history=conversation_history,
        )

    except Exception as exc:

        diagnostics = {
            "success": False,
            "error": str(exc),
        }

    # --------------------------------------------------------
    # ESCALATION
    # --------------------------------------------------------

    if should_escalate(diagnostics):

        ticket = create_support_ticket(
            query,
            diagnostics,
        )

        return {
            "route": route,
            "diagnostics": diagnostics,
            "escalation": ticket,
            "agent_decision": decision,
        }

    # --------------------------------------------------------
    # DIAGNOSTIC ANSWER
    # --------------------------------------------------------

    answer = generate_diagnostic_answer(
        query,
        diagnostics,
        conversation_history=conversation_history,
    )

    return {
        "route": route,
        "diagnostics": diagnostics,
        "answer": answer,
        "agent_decision": decision,
    }