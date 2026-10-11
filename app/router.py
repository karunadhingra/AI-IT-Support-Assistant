import re

from app.agent import decide_action
from app.rag import (
    _get_primary_problem,
    generate_answer,
    generate_diagnostic_answer,
    get_next_troubleshooting_batch,
)
from app.diagnostics.network import ping_host
from app.diagnostics.dns import dns_lookup
from app.diagnostics.disk import check_disk_space
from app.diagnostics.memory import check_memory
from app.diagnostics.processes import (
    build_process_recommendation,
    get_top_processes,
)
from app.diagnostics.system_health import (
    check_cpu_usage,
    check_swap_memory,
    check_system_uptime,
)
from app.escalation import create_support_ticket, should_escalate


MAX_PROCESS_CHECKS_BEFORE_STEPS = 2


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

AFFIRMATIVE_REPLIES = {
    "yes",
    "yeah",
    "yep",
    "yup",
    "yes i do",
    "yes i need it",
    "yeah i need it",
    "i do",
}

NEGATIVE_PROCESS_REPLIES = {
    "no",
    "nope",
    "no i don't",
    "no i dont",
    "i don't need it",
    "i dont need it",
    "i closed it",
    "closed it",
    "closed",
    "done",
}


def _normalize_process_name(name):
    if not name:
        return ""

    normalized = str(name).strip().lower()

    if normalized in PROCESS_ALIASES:
        return PROCESS_ALIASES[normalized]

    if not normalized.endswith(".exe"):
        normalized = f"{normalized}.exe"

    return normalized


def _extract_process_name_from_text(text):
    if not text:
        return None

    text = str(text)

    executable_matches = re.findall(
        r"\b[a-zA-Z0-9_.-]+\.exe\b",
        text,
        flags=re.IGNORECASE,
    )

    if executable_matches:
        return _normalize_process_name(executable_matches[-1])

    normalized = text.lower()
    known_applications = sorted(
        PROCESS_ALIASES.keys(),
        key=len,
        reverse=True,
    )

    for application in known_applications:
        if re.search(rf"\b{re.escape(application)}\b", normalized):
            return _normalize_process_name(application)

    return None


def _extract_process_from_previous_assistant(conversation_history):
    if not conversation_history:
        return None

    for message in reversed(conversation_history):
        if message.get("role") != "assistant":
            continue

        content = str(message.get("content", "")).strip()
        if not content:
            continue

        process_name = _extract_process_name_from_text(content)
        if process_name:
            return process_name

    return None


def _last_assistant_asked_about_process(conversation_history):
    if not conversation_history:
        return None

    for message in reversed(conversation_history):
        if message.get("role") != "assistant":
            continue

        content = str(message.get("content", "")).strip()
        content_lower = content.lower()

        if (
            "do you need" in content_lower
            or "consider closing" in content_lower
            or "save your work" in content_lower
            or "% of ram" in content_lower
        ):
            return _extract_process_name_from_text(content)
        return None

    return None


def _is_process_state_message(text, conversation_history=None):
    if not text:
        return False

    normalized = re.sub(r"[^\w\s'.-]", " ", str(text).lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()

    stripped = re.sub(
        r"^(yes|yeah|yep|yup|no|nope|ok|okay|sure|well|actually|uh|um)\s+",
        "",
        normalized,
    ).strip()

    if _last_assistant_asked_about_process(conversation_history):
        if (
            normalized in AFFIRMATIVE_REPLIES
            or normalized in NEGATIVE_PROCESS_REPLIES
            or stripped in AFFIRMATIVE_REPLIES
            or stripped in NEGATIVE_PROCESS_REPLIES
        ):
            return True

    state_phrases = [
        "i need it",
        "i need that",
        "i need this",
        "need it",
        "need that",
        "need this",
        "i still need",
        "i want it",
        "i still want",
        "i am using",
        "i'm using",
        "im using",
        "using it",
        "using that",
        "using this",
        "using the",
        "actively using",
        "right now",
        "i can't close",
        "i cannot close",
        "can't close",
        "cannot close",
        "don't want to close",
        "do not want to close",
        "keep it open",
        "keep that open",
        "keep this open",
        "need to keep",
        "i closed it",
        "already closed",
    ]

    if any(phrase in normalized or phrase in stripped for phrase in state_phrases):
        return True

    patterns = [
        r"\bi (still )?need (it|that|this|the app|the application|chrome|python|code|vscode|edge|firefox|discord|teams|spotify|slack|zoom)\b",
        r"\b(can't|cannot|don't want to|do not want to) close\b",
        r"\bkeep (it|that|this|[a-z0-9_.-]+) open\b",
    ]

    return any(re.search(pattern, normalized) for pattern in patterns)


def _extract_process_state(conversation_history):
    required_processes = set()
    excluded_processes = set()

    if not conversation_history:
        return {
            "required_processes": [],
            "excluded_processes": [],
        }

    for index, message in enumerate(conversation_history):
        role = message.get("role")
        content = str(message.get("content", "")).strip()

        if not content or role != "user":
            continue

        normalized = re.sub(r"\s+", " ", content.lower().strip())
        previous_messages = conversation_history[:index]
        process_name = _extract_process_name_from_text(content)

        if not process_name and _is_process_state_message(
            content, previous_messages
        ):
            process_name = _extract_process_from_previous_assistant(
                previous_messages
            )

        if not process_name:
            continue

        normalized_process = _normalize_process_name(process_name)

        needs_patterns = [
            r"\bi need\b",
            r"\bi still need\b",
            r"\bi want\b",
            r"\bi still want\b",
            r"\bi use\b",
            r"\bi am using\b",
            r"\bi'm using\b",
            r"\bim using\b",
            r"\busing it\b",
            r"\busing that\b",
            r"\bright now\b",
            r"\bkeep .* open\b",
            r"\bneed to keep\b",
        ]

        cannot_close_patterns = [
            r"\bi can't close\b",
            r"\bi cannot close\b",
            r"\bdon't want to close\b",
            r"\bdo not want to close\b",
            r"\bcan't close\b",
            r"\bcannot close\b",
        ]

        closed_patterns = [
            r"\bi closed\b",
            r"\bi have closed\b",
            r"\bi already closed\b",
            r"\bclosed it\b",
            r"\bclosed the app\b",
            r"\bclosed the application\b",
        ]

        if (
            normalized in AFFIRMATIVE_REPLIES
            or any(re.search(p, normalized) for p in needs_patterns)
            or any(re.search(p, normalized) for p in cannot_close_patterns)
        ):
            required_processes.add(normalized_process)
            excluded_processes.add(normalized_process)

        if normalized in NEGATIVE_PROCESS_REPLIES or any(
            re.search(p, normalized) for p in closed_patterns
        ):
            excluded_processes.add(normalized_process)

    return {
        "required_processes": sorted(required_processes),
        "excluded_processes": sorted(excluded_processes),
    }


def _count_assistant_turns(conversation_history):
    if not conversation_history:
        return 0
    return sum(
        1 for msg in conversation_history if msg.get("role") == "assistant"
    )


def _count_step_batches_shown(conversation_history):
    if not conversation_history:
        return 0

    count = 0
    for msg in conversation_history:
        if msg.get("role") != "assistant":
            continue
        content = str(msg.get("content", "")).lower()
        if (
            "troubleshooting steps to try" in content
            or "alternative troubleshooting steps" in content
            or "next troubleshooting steps" in content
        ):
            count += 1
    return count


def _get_original_issue(query, conversation_history):
    """
    Use `_get_primary_problem` (which scans backwards from the latest message)
    so if the user starts a new topic in the same chat, we always track
    the MOST RECENT substantive problem rather than message #1!
    """
    return _get_primary_problem(query, conversation_history)


def _is_how_to_or_clarification_question(query):
    """
    Detect when the user is asking HOW to perform a suggested step
    (e.g., "how to disable startup applications", "where is that setting?").
    """
    normalized = re.sub(r"\s+", " ", str(query).lower().strip())
    how_to_patterns = [
        r"^how (to|do i|can i)\b",
        r"^where (is|do i|can i)\b",
        r"^what (is|does|are)\b",
        r"^can you (explain|show|tell me how)\b",
        r"\bhow to\b",
        r"\bsteps to\b",
    ]
    return any(re.search(p, normalized) for p in how_to_patterns)


def _answer_common_how_to(query):
    """
    Provide instant, crystal-clear Windows instructions for common how-to
    questions about troubleshooting steps, or return None to let the LLM answer.
    """
    q = str(query).lower()

    if "startup" in q:
        return (
            "### How to Disable Startup Applications on Windows\n"
            "1. Press **`Ctrl + Shift + Esc`** on your keyboard to open **Task Manager** (or right-click the Start button and select **Task Manager**).\n"
            "2. Click on the **Startup apps** tab on the left sidebar (it looks like a speedometer icon).\n"
            "3. Look at the **Status** and **Startup impact** columns.\n"
            "4. Right-click any non-essential application with **High** or **Medium** impact (such as Spotify, Steam, Teams, or OneDrive) and click **Disable**.\n"
            "*(Note: Disabling a startup app only stops it from launching automatically when you turn on your PC — you can still open the app normally whenever you need it.)*\n\n"
            "Did that help, or would you like to try the next troubleshooting step?"
        )

    if "adapter" in q or "wi-fi" in q or "wifi" in q:
        return (
            "### How to Check & Reset Your Wi-Fi Adapter on Windows\n"
            "1. Press **`Win + I`** to open **Windows Settings**, then go to **Network & internet → Wi-Fi**.\n"
            "2. Toggle the **Wi-Fi switch Off**, wait **10 seconds**, and toggle it back **On**.\n"
            "3. If websites still won't load, go to **Settings → Network & internet → Advanced network settings**.\n"
            "4. Click **Network reset** (or run the **Network Adapter Troubleshooter**) to refresh your wireless driver.\n\n"
            "Did refreshing your Wi-Fi connection resolve the issue?"
        )

    if "battery saver" in q or "power mode" in q or "energy saver" in q:
        return (
            "### How to Change Windows Power Mode\n"
            "1. Press **`Win + I`** to open **Settings** and click **System → Power & battery**.\n"
            "2. Make sure **Energy Saver / Battery Saver** is turned **Off**.\n"
            "3. Find **Power mode** and change the dropdown from *Best power efficiency* to **Balanced** or **Best performance**.\n\n"
            "Did adjusting the power mode help improve your computer's responsiveness?"
        )

    if "temp" in q or "cache" in q or "disk cleanup" in q:
        return (
            "### How to Clear Temporary Cache Files on Windows\n"
            "1. Press **`Win + I`** to open **Settings** and go to **System → Storage**.\n"
            "2. Click on **Temporary files**.\n"
            "3. Check the boxes for **Temporary files**, **Windows Update Cleanup**, and **Thumbnails** (make sure *Downloads* is unchecked if you want to keep your downloaded files).\n"
            "4. Click **Remove files** at the top.\n\n"
            "Let me know once you've tried this or if the issue is still happening!"
        )

    return None


def _is_uncomfortable_or_alternative_request(query):
    normalized = str(query).lower().strip()
    phrases = [
        "not comfortable",
        "uncomfortable",
        "don't want to change",
        "do not want to change",
        "can't change",
        "cannot change",
        "don't want to restart",
        "can't restart",
        "cannot restart",
        "something else",
        "suggest something else",
        "other step",
        "other steps",
        "another step",
        "different step",
        "alternative",
        "skip this",
    ]
    return any(p in normalized for p in phrases)


def _is_problem_resolved_message(query):
    normalized = str(query).lower().strip()
    resolved_phrases = [
        "it worked",
        "that worked",
        "fixed",
        "resolved",
        "solved",
        "working now",
        "works now",
        "much better",
        "thank you",
        "thanks",
    ]
    return any(phrase in normalized for phrase in resolved_phrases)


def _is_unresolved_message(query):
    normalized = re.sub(r"[^\w\s'-]", " ", str(query).lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()

    if _is_problem_resolved_message(normalized):
        return False

    unresolved_phrases = [
        "still",
        "didn't work",
        "did not work",
        "doesn't work",
        "does not work",
        "not working",
        "not working out",
        "won't work",
        "wont work",
        "not resolved",
        "not fixed",
        "not solved",
        "nothing changed",
        "no improvement",
        "same problem",
        "same issue",
        "i tried",
        "already tried",
        "none of these",
        "nothing works",
        "no luck",
        "escalate",
        "support ticket",
        "human support",
    ]

    if any(phrase in normalized for phrase in unresolved_phrases):
        return True

    if normalized in {
        "no",
        "nope",
        "not yet",
        "still no",
        "no it didn't",
        "no it did not",
        "check",
        "check it",
        "next",
    }:
        return True

    return False


def _build_tailored_performance_batches(conversation_history):
    mem = check_memory()
    uptime = check_system_uptime()
    swap = check_swap_memory()

    ram_pct = mem.get("used_percent", 0.0)
    up_days = uptime.get("uptime_days", 0.0)
    up_hours = uptime.get("uptime_hours", 0.0)
    swap_pct = swap.get("used_percent", 0.0)

    batch_1 = []
    if ram_pct >= 80:
        batch_1.append(
            f"**Free up browser & tab memory (RAM is at {ram_pct:.1f}%):** Since you need your main applications open, close any unused browser tabs or enable your browser's *Sleeping Tabs / Memory Saver* feature so inactive tabs release RAM immediately."
        )
    else:
        batch_1.append(
            "**Close unused browser tabs and background tray apps:** Exit background apps sitting in your bottom-right system tray (such as Steam, Discord, or media players) that you aren't actively using."
        )

    if up_hours >= 48:
        batch_1.append(
            f"**Perform a clean Windows Restart ({up_days} days / {up_hours} hours of continuous uptime detected):** Your PC has been running for {up_days} days without a full reboot, which causes Windows kernel caches and driver memory leaks to build up. Save your open work and choose **Start → Power → Restart**."
        )
    else:
        batch_1.append(
            "**Pause active cloud syncing temporarily:** If OneDrive, Google Drive, or Dropbox is actively syncing large folders in the background, pause syncing for 1 hour to stop disk and CPU contention."
        )

    batch_2 = [
        "**Pause background cloud sync & updates:** Click the **OneDrive / Dropbox** icon in your taskbar tray and select *Pause syncing*, and check if Windows Update is downloading patches in the background.",
        "**Check power cable & Battery Saver throttling:** Ensure your laptop charger is firmly plugged in and **Battery Saver / Energy Saver** is turned off in the quick-settings menu (Windows throttles CPU speed by up to 50% in energy-saver mode).",
    ]
    if swap_pct >= 50:
        batch_2.append(
            f"**Clear temporary cache files (Pagefile usage is {swap_pct:.1f}%):** Open **Settings → System → Storage → Temporary files** and remove cached temporary files so Windows Virtual Memory can page smoothly."
        )

    return [batch_1, batch_2]


def _collect_attempted_steps_summary(conversation_history, current_query=None):
    if not conversation_history:
        return [
            "Initial automated diagnostics and first-level troubleshooting were executed."
        ]

    steps_summary = []
    proc_state = _extract_process_state(conversation_history)
    if proc_state["required_processes"]:
        steps_summary.append(
            f"Inspected active processes; user confirmed they are actively using {', '.join(proc_state['required_processes'])} and need them kept open."
        )

    suggested_steps = []
    for msg in conversation_history:
        if msg.get("role") != "assistant":
            continue
        content = str(msg.get("content", ""))
        matches = re.findall(r"^\d+\.\s+(.+)$", content, flags=re.MULTILINE)
        for m in matches:
            clean_step = re.sub(r"\*\*|\`", "", m).strip()
            if clean_step and clean_step not in suggested_steps:
                suggested_steps.append(clean_step)

    for step in suggested_steps[:6]:
        steps_summary.append(f"Troubleshooting step provided: {step}")

    if current_query:
        steps_summary.append(f"User final status report: \"{current_query}\"")

    if not steps_summary:
        steps_summary.append(
            "User completed multiple rounds of guided troubleshooting, and the issue persisted."
        )

    return steps_summary


def _gather_full_diagnostics_for_ticket(original_issue, conversation_history):
    issue_lower = str(original_issue).lower()
    if any(
        k in issue_lower
        for k in ["wifi", "wi-fi", "internet", "network", "dns", "website"]
    ):
        return run_diagnostics("network", conversation_history)
    if any(
        k in issue_lower
        for k in [
            "slow",
            "lag",
            "freeze",
            "memory",
            "ram",
            "disk",
            "performance",
        ]
    ):
        return run_diagnostics("performance", conversation_history)
    return {}


def _format_escalation_response(intro_text, ticket):
    findings_list = "\n".join(f"- {f}" for f in ticket.get("findings", []))
    steps_list = "\n".join(
        f"{i}. {s}"
        for i, s in enumerate(ticket.get("steps_attempted", []), start=1)
    )
    recs_list = "\n".join(
        f"- {r}"
        for r in ticket.get(
            "recommendations", [ticket.get("action_needed", "")]
        )
    )

    prefix = f"{intro_text}\n\n---\n" if intro_text else ""

    return (
        f"{prefix}"
        f"### ⚠️ Support Ticket Created (Priority: {ticket.get('priority', 'High')})\n"
        f"**Title:** {ticket.get('title', 'IT Support Assistance Required')}  \n"
        f"**Reported Issue:** {ticket.get('issue', '')}  \n"
        f"**Status:** `{ticket.get('status', 'created').upper()}`\n\n"
        f"#### 1. Diagnostics Performed\n{findings_list}\n\n"
        f"#### 2. Troubleshooting Steps Followed\n{steps_list}\n\n"
        f"#### 3. Recommended Next Action for IT Support\n{recs_list}"
    )


def _format_progressive_steps_response(
    article_id,
    article_problem,
    next_steps,
    intro_note="",
    heading="Troubleshooting Steps to Try Next",
):
    steps_md = "\n".join(
        f"{i}. {step}" for i, step in enumerate(next_steps, start=1)
    )
    intro_block = f"{intro_note}\n\n" if intro_note else ""

    return (
        f"{intro_block}"
        f"### {heading}\n"
        f"{steps_md}\n\n"
        "Let me know if trying these helps improve the issue, or if you'd like an alternative option.\n\n"
        f"**Source:** IT Knowledge Base — {article_id}: {article_problem}"
    )


def route_issue(query, conversation_history=None):
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

    return action_to_route.get(decision.get("action"), "rag")


def run_diagnostics(route, conversation_history=None):
    if route == "network":
        return {
            "ping": ping_host("8.8.8.8"),
            "dns": dns_lookup("google.com"),
        }

    if route == "performance":
        process_state = _extract_process_state(conversation_history)

        diagnostics = {
            "disk": check_disk_space(),
            "memory": check_memory(),
            "processes": get_top_processes(
                excluded_processes=process_state["excluded_processes"],
                required_processes=process_state["required_processes"],
            ),
        }

        diagnostics["cpu"] = check_cpu_usage(interval=0.2)
        diagnostics["uptime"] = check_system_uptime()
        diagnostics["swap"] = check_swap_memory()
        diagnostics["process_state"] = process_state
        return diagnostics

    return {}


def handle_query(query, conversation_history=None):
    # Stateless unit test compatibility (when conversation_history is None)
    if conversation_history is None:
        decision = decide_action(query, conversation_history=None)
        action = decision.get("action", "rag")

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

        if action == "rag":
            answer = generate_answer(query, conversation_history=None)
            return {
                "route": "rag",
                "answer": answer,
                "agent_decision": decision,
            }

        route = "network" if action == "network_diagnostics" else "performance"
        try:
            diagnostics = run_diagnostics(route, conversation_history=None)
        except Exception as exc:
            diagnostics = {"success": False, "error": str(exc)}

        if should_escalate(diagnostics):
            ticket = create_support_ticket(query, diagnostics)
            return {
                "route": route,
                "diagnostics": diagnostics,
                "escalation": ticket,
                "agent_decision": decision,
            }

        answer = generate_diagnostic_answer(
            query, diagnostics, conversation_history=None
        )
        return {
            "route": route,
            "diagnostics": diagnostics,
            "answer": answer,
            "agent_decision": decision,
        }

    # ============================================================
    # MULTI-TURN INTERACTIVE CONVERSATION FLOW
    # ============================================================
    original_issue = _get_original_issue(query, conversation_history)
    assistant_turns = _count_assistant_turns(conversation_history)
    step_batches_shown = _count_step_batches_shown(conversation_history)
    normalized_query = str(query).lower().strip()
    is_perf_issue = any(
        k in original_issue.lower()
        for k in ["slow", "lag", "freeze", "memory", "ram", "disk", "performance"]
    )

    # 0. Check if user says the problem is solved
    if assistant_turns >= 1 and _is_problem_resolved_message(query):
        return {
            "route": "rag",
            "answer": "Glad to hear that resolved the issue! Feel free to reach out if you need help with anything else.",
            "agent_decision": {
                "action": "rag",
                "reason": "Issue resolved.",
                "question": "",
            },
        }

    # 1. Explicit escalation request
    if "escalate" in normalized_query or "support ticket" in normalized_query:
        diag = _gather_full_diagnostics_for_ticket(
            original_issue, conversation_history
        )
        steps_done = _collect_attempted_steps_summary(
            conversation_history, query
        )
        ticket = create_support_ticket(
            original_issue, diag, steps_attempted=steps_done
        )
        return {
            "route": "rag",
            "diagnostics": diag,
            "escalation": ticket,
            "answer": _format_escalation_response(
                "I have escalated your issue to the IT Support team with a complete summary of our diagnostics and troubleshooting steps:",
                ticket,
            ),
            "agent_decision": {
                "action": "rag",
                "reason": "User requested escalation.",
                "question": "",
            },
        }

    # 1.5 Handle "How-To" / Clarification Questions (e.g., "how to disable startup applications")
    if assistant_turns >= 1 and _is_how_to_or_clarification_question(query):
        direct_how_to = _answer_common_how_to(query)
        if direct_how_to:
            return {
                "route": "rag",
                "answer": direct_how_to,
                "agent_decision": {
                    "action": "rag",
                    "reason": "Answered user how-to question directly.",
                    "question": "",
                },
            }
        # Otherwise let the LLM answer the specific how-to question
        answer = generate_answer(query, conversation_history=conversation_history)
        return {
            "route": "rag",
            "answer": answer,
            "agent_decision": {
                "action": "rag",
                "reason": "Answered user how-to question via LLM.",
                "question": "",
            },
        }

    # 2. Handle Process-State Replies ("i am using it right now", "i need it", "yes", "i closed it")
    if conversation_history and _is_process_state_message(
        query, conversation_history
    ):
        updated_history = list(conversation_history)
        if not updated_history or updated_history[-1].get("content") != query:
            updated_history.append({"role": "user", "content": query})

        process_state = _extract_process_state(updated_history)
        excluded = process_state["excluded_processes"]
        required = process_state["required_processes"]

        last_proc = (
            _last_assistant_asked_about_process(conversation_history)
            or (required[-1] if required else None)
            or (excluded[-1] if excluded else "that application")
        )

        # User closed the process
        if (
            normalized_query in NEGATIVE_PROCESS_REPLIES
            or "closed" in normalized_query
        ):
            mem = check_memory()
            mem_text = (
                f"Current memory usage is now **{mem['used_percent']:.1f}%**."
                if mem.get("used_percent") is not None
                else ""
            )
            return {
                "route": "rag",
                "answer": (
                    f"Thanks for closing `{last_proc}`. {mem_text}\n\n"
                    "Did closing that application improve your computer's speed, or is it still running slowly?"
                ),
                "agent_decision": {
                    "action": "rag",
                    "reason": "Process closed.",
                    "question": "",
                },
            }

        # Check if there is a 2nd user-controlled process using noticeable RAM (>= 1.5%)
        proc_diag = get_top_processes(
            excluded_processes=excluded,
            required_processes=required,
        )
        candidates = [
            p
            for p in proc_diag.get("recommendation_candidates", [])
            if p.get("memory_percent", 0.0) >= 1.5
        ]
        proc_diag["recommendation_candidates"] = candidates

        if candidates and len(required) < MAX_PROCESS_CHECKS_BEFORE_STEPS:
            rec = build_process_recommendation(proc_diag)
            return {
                "route": "rag",
                "answer": (
                    f"Got it — I'll keep `{last_proc}` excluded from closure recommendations.\n\n"
                    f"{rec['message']}"
                ),
                "agent_decision": {
                    "action": "rag",
                    "reason": "User needs the process; checking next running application.",
                    "question": "",
                },
            }

        # Provide Batch 1 of tailored, diagnostic-driven steps
        uptime = check_system_uptime()
        cpu = check_cpu_usage(interval=0.2)
        batches = _build_tailored_performance_batches(conversation_history)

        kept_list = (
            ", ".join(f"`{p}`" for p in required)
            if required
            else f"`{last_proc}`"
        )
        health_note = (
            f"Understood — I'll keep {kept_list} open.\n\n"
            f"**Deeper System Diagnostic:** Your CPU load is **{cpu.get('cpu_percent', 0.0):.1f}%**, "
            f"and your system has been running continuously for **{uptime.get('uptime_hours', 0.0)} hours "
            f"({uptime.get('uptime_days', 0.0)} days)** since its last full restart."
        )

        return {
            "route": "rag",
            "answer": _format_progressive_steps_response(
                "performance_001",
                "Computer is running very slowly",
                batches[0],
                intro_note=health_note,
                heading="Troubleshooting Steps to Try Next",
            ),
            "agent_decision": {
                "action": "rag",
                "reason": "Providing diagnostic-tailored Batch 1 troubleshooting steps.",
                "question": "",
            },
        }

    # 3. Follow-Up Turns When User Says "Not comfortable", "No", "Still slow", "Didn't work", "Check"
    if assistant_turns >= 1 and (
        _is_uncomfortable_or_alternative_request(query)
        or _is_unresolved_message(query)
    ):
        if is_perf_issue:
            batches = _build_tailored_performance_batches(conversation_history)
            if step_batches_shown == 0:
                next_steps = batches[0]
            elif step_batches_shown == 1:
                next_steps = batches[1]
            else:
                next_steps = []
            article_id = "performance_001"
            article_problem = "Computer is running very slowly"
        else:
            article, next_steps, _ = get_next_troubleshooting_batch(
                original_issue, conversation_history, batch_size=2
            )
            article_id = article["id"] if article else "it_kb"
            article_problem = article["problem"] if article else original_issue

        if step_batches_shown >= 2 or not next_steps:
            diag = _gather_full_diagnostics_for_ticket(
                original_issue, conversation_history
            )
            steps_done = _collect_attempted_steps_summary(
                conversation_history, query
            )
            ticket = create_support_ticket(
                original_issue, diag, steps_attempted=steps_done
            )
            return {
                "route": "rag",
                "diagnostics": diag,
                "escalation": ticket,
                "answer": _format_escalation_response(
                    "Since the issue is still not resolved after trying the guided troubleshooting steps, I have generated an **IT Support Escalation Ticket** with all diagnostics and steps we followed:",
                    ticket,
                ),
                "agent_decision": {
                    "action": "rag",
                    "reason": "Troubleshooting steps exhausted/unresolved; escalating to IT Support.",
                    "question": "",
                },
            }

        if _is_uncomfortable_or_alternative_request(query):
            intro = "No problem at all — we can skip that step. Here are safe, non-intrusive alternatives you can try without changing any system settings:"
            heading = "Alternative Troubleshooting Steps to Try"
        else:
            intro = "Here are the next troubleshooting steps to check:"
            heading = "Troubleshooting Steps to Try Next"

        return {
            "route": "rag",
            "answer": _format_progressive_steps_response(
                article_id,
                article_problem,
                next_steps,
                intro_note=intro,
                heading=heading,
            ),
            "agent_decision": {
                "action": "rag",
                "reason": "Providing next progressive batch of troubleshooting steps.",
                "question": "",
            },
        }

    # 4. Standard First-Turn Routing (or New Topic)
    decision = decide_action(
        query,
        conversation_history=conversation_history,
    )

    action = decision.get("action", "rag")

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

    route = "network" if action == "network_diagnostics" else "performance"

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

    diagnostic_answer = generate_diagnostic_answer(
        query,
        diagnostics,
        conversation_history=conversation_history,
    )

    return {
        "route": route,
        "diagnostics": diagnostics,
        "answer": diagnostic_answer,
        "agent_decision": decision,
    }