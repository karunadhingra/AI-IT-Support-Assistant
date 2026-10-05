import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import streamlit as st

from app.router import handle_query
from app.memory import ConversationMemory


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="IT Support Assistant",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================

if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()

if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# DARK THEME + CHAT STYLING
# ============================================================

st.markdown(
    """
<style>

@import url(
    'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap'
);

html,
body,
[class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
}

.stApp {
    background-color: #1e1e1e;
    color: #ececec;
}

.main .block-container {
    max-width: 820px;
    padding-top: 1.5rem;
    padding-bottom: 8rem;
}

[data-testid="stSidebar"] {
    background-color: #171717;
    border-right: none;
}

[data-testid="stSidebar"] .stButton button {
    background-color: transparent !important;
    color: #ececec !important;
    border: 1px solid #424242 !important;
    border-radius: 8px !important;
    padding: 0.5rem 1rem !important;
    justify-content: flex-start !important;
    width: 100% !important;
    font-weight: 500 !important;
}

[data-testid="stSidebar"] .stButton button:hover {
    background-color: #2f2f2f !important;
}

[data-testid="stHeader"] {
    background: transparent;
}

.landing-wrapper {
    text-align: center;
    padding-top: 7vh;
    padding-bottom: 1.5rem;
}

.landing-label {
    color: #60a5fa;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}

.landing-title {
    color: #ffffff;
    font-size: 2.8rem;
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: -0.04em;
    margin-bottom: 1rem;
}

.landing-title-highlight {
    background: linear-gradient(
        90deg,
        #60a5fa,
        #a78bfa
    );

    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.landing-description {
    color: #a1a1aa;
    font-size: 1rem;
    line-height: 1.7;
    max-width: 570px;
    margin: 0 auto;
}

.landing-hint {
    color: #71717a;
    font-size: 0.8rem;
    margin-top: 1rem;
}

[data-testid="stChatMessage"] {
    background-color: transparent !important;
    border: none !important;
    padding: 0.75rem 0 !important;
}

[data-testid="stChatMessage"]:has(.user-msg) {
    flex-direction: row-reverse !important;
}

[data-testid="stChatMessage"]:has(.user-msg)
[data-testid="stChatMessageAvatar"],

[data-testid="stChatMessage"]:has(.ai-msg)
[data-testid="stChatMessageAvatar"] {
    display: none !important;
    width: 0 !important;
    margin: 0 !important;
}

[data-testid="stChatMessage"]:has(.user-msg)
[data-testid="stChatMessageContent"] {
    background-color: #2b5278 !important;
    color: #ffffff !important;

    border-radius: 18px 4px 18px 18px !important;

    padding: 12px 16px !important;

    margin-left: auto !important;
    margin-right: 0 !important;

    max-width: 75% !important;

    font-size: 0.95rem !important;

    box-shadow:
        0 1px 2px rgba(0, 0, 0, 0.15) !important;
}

[data-testid="stChatMessage"]:has(.ai-msg)
[data-testid="stChatMessageContent"] {
    background-color: #2f2f2f !important;
    color: #ececec !important;

    border-radius: 4px 18px 18px 18px !important;

    padding: 12px 16px !important;

    max-width: 85% !important;

    font-size: 0.95rem !important;

    line-height: 1.6 !important;

    box-shadow:
        0 1px 2px rgba(0, 0, 0, 0.15) !important;

    margin-left: 0 !important;
}

.ai-tag {
    font-size: 0.72rem;
    color: #9ca3af;
    font-weight: 600;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
    display: block;
    letter-spacing: 0.05em;
}

[data-testid="stChatInput"] {
    background-color: #2f2f2f !important;

    border: 1px solid #424242 !important;

    border-radius: 1.5rem !important;

    padding: 0.2rem 0.5rem !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: #5b7ea8 !important;
}

[data-testid="stChatInput"] textarea {
    color: #ececec !important;
    font-size: 0.95rem !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #8e8e8e !important;
}

[data-testid="stExpander"] {
    border: 1px solid #3a3a3a !important;
    border-radius: 10px !important;
    background-color: #252525 !important;
}

@keyframes fadeIn {

    from {
        opacity: 0;
        transform: translateY(8px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }

}

#MainMenu,
footer {
    visibility: hidden;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("### IT Assistant")

    if st.button("➕ New chat"):

        st.session_state.memory.clear()
        st.session_state.messages = []

        if "pending_query" in st.session_state:
            del st.session_state.pending_query

        st.rerun()

    st.markdown(
        "<br><br>",
        unsafe_allow_html=True,
    )

    st.caption("SYSTEM STATUS")
    st.caption("🟢 All services operational")


# ============================================================
# PROCESS FILTERING
# ============================================================

def _is_irrelevant_process(process):
    """
    Identify Windows/system processes and other processes
    that should never be recommended for closure.
    """

    name = str(
        process.get("name", "")
    ).strip().lower()

    ignored_processes = {
        # Windows/system processes
        "system idle process",
        "system",
        "registry",
        "memory compression",
        "memcompression",
        "smss.exe",
        "csrss.exe",
        "wininit.exe",
        "services.exe",
        "lsass.exe",
        "winlogon.exe",
        "dwm.exe",
        "svchost.exe",
        "explorer.exe",
        "dllhost.exe",
        "runtimebroker.exe",

        # Ollama / AI runtime
        "llama-server.exe",
        "ollama.exe",
    }

    return name in ignored_processes


def _get_relevant_processes(
    processes,
    limit=5,
):
    """
    Return processes that are reasonable to discuss
    with the user.
    """

    relevant = [
        process
        for process in processes
        if not _is_irrelevant_process(process)
    ]

    return relevant[:limit]


# ============================================================
# DIAGNOSTIC RESPONSE BUILDER
# ============================================================

def build_diagnostic_response(diagnostics):
    """
    Build diagnostic explanations directly from Python
    diagnostic results.

    Exact values are never generated by the LLM.
    """

    sections = []

    # ========================================================
    # CHECKS PERFORMED
    # ========================================================

    checks = []

    if "ping" in diagnostics:

        ping = diagnostics["ping"]

        if ping.get("success") is True:

            checks.append(
                "- Ping test to 8.8.8.8 was successful."
            )

        else:

            checks.append(
                "- Ping test to 8.8.8.8 was unsuccessful."
            )

    if "dns" in diagnostics:

        dns = diagnostics["dns"]

        host = dns.get(
            "host",
            "the requested hostname",
        )

        if dns.get("success") is True:

            checks.append(
                f"- DNS lookup for {host} was successful."
            )

        else:

            checks.append(
                f"- DNS lookup for {host} failed."
            )

    if "disk" in diagnostics:

        disk = diagnostics["disk"]

        free_gb = disk.get("free_gb")

        if free_gb is not None:

            checks.append(
                f"- Available disk space: "
                f"{free_gb:.1f} GB."
            )

    if "memory" in diagnostics:

        memory = diagnostics["memory"]

        used_percent = memory.get("used_percent")

        if used_percent is not None:

            checks.append(
                f"- Memory usage: "
                f"{used_percent:.1f}% currently in use."
            )

    if "processes" in diagnostics:

        process_data = diagnostics["processes"]

        process_count = process_data.get(
            "process_count"
        )

        if process_count is not None:

            checks.append(
                f"- Running processes detected: "
                f"{process_count}."
            )

    if checks:

        sections.append(
            "### 1. Checks performed\n\n"
            + "\n".join(checks)
        )

    # ========================================================
    # WHAT THE RESULTS MEAN
    # ========================================================

    meanings = []

    if "ping" in diagnostics:

        ping_success = diagnostics["ping"].get(
            "success"
        )

        if ping_success is True:

            meanings.append(
                "- The computer was able to reach "
                "8.8.8.8 at the time of the test."
            )

        else:

            meanings.append(
                "- The computer could not successfully "
                "reach 8.8.8.8 during the test."
            )

    if "dns" in diagnostics:

        dns_success = diagnostics["dns"].get(
            "success"
        )

        if dns_success is True:

            meanings.append(
                "- The DNS lookup completed successfully, "
                "so the requested hostname resolved correctly."
            )

        else:

            meanings.append(
                "- The DNS lookup failed, so hostname "
                "resolution should be investigated."
            )

    if "disk" in diagnostics:

        free_gb = diagnostics["disk"].get(
            "free_gb"
        )

        if free_gb is not None:

            if free_gb < 20:

                meanings.append(
                    f"- Only {free_gb:.1f} GB of disk space "
                    "is available, which is relatively low "
                    "and may contribute to performance problems."
                )

            else:

                meanings.append(
                    f"- {free_gb:.1f} GB of disk space is "
                    "available, so disk capacity does not "
                    "currently appear to be the cause of "
                    "the performance problem."
                )

    if "memory" in diagnostics:

        used_percent = diagnostics["memory"].get(
            "used_percent"
        )

        if used_percent is not None:

            if used_percent >= 85:

                meanings.append(
                    f"- Memory usage is {used_percent:.1f}%, "
                    "which is high and may contribute to "
                    "system slowness."
                )

            else:

                meanings.append(
                    f"- Memory usage is {used_percent:.1f}%. "
                    "This result alone does not establish "
                    "the cause of the performance problem."
                )

    if "processes" in diagnostics:

        process_data = diagnostics["processes"]

        top_memory = process_data.get(
            "top_memory",
            [],
        )

        top_cpu = process_data.get(
            "top_cpu",
            [],
        )

        relevant_memory = _get_relevant_processes(
            top_memory
        )

        relevant_cpu = _get_relevant_processes(
            top_cpu
        )

        if relevant_memory:

            memory_items = []

            for process in relevant_memory:

                name = process.get(
                    "name",
                    "Unknown",
                )

                memory_percent = process.get(
                    "memory_percent",
                    0.0,
                )

                memory_items.append(
                    f"{name} "
                    f"({memory_percent:.1f}% RAM)"
                )

            meanings.append(
                "- The processes currently using the most "
                "memory include: "
                + ", ".join(memory_items)
                + "."
            )

        if relevant_cpu:

            cpu_items = []

            for process in relevant_cpu:

                name = process.get(
                    "name",
                    "Unknown",
                )

                cpu_percent = process.get(
                    "cpu_percent",
                    0.0,
                )

                if cpu_percent > 1.0:

                    cpu_items.append(
                        f"{name} "
                        f"({cpu_percent:.1f}% CPU)"
                    )

            if cpu_items:

                meanings.append(
                    "- The processes currently using the most "
                    "CPU include: "
                    + ", ".join(cpu_items)
                    + "."
                )

    if meanings:

        sections.append(
            "### 2. What the results mean\n\n"
            + "\n".join(meanings)
        )

    # ========================================================
    # PROCESS DETAILS
    # ========================================================

    if "processes" in diagnostics:

        process_data = diagnostics["processes"]

        top_memory = process_data.get(
            "top_memory",
            [],
        )

        top_cpu = process_data.get(
            "top_cpu",
            [],
        )

        relevant_memory = _get_relevant_processes(
            top_memory
        )

        relevant_cpu = _get_relevant_processes(
            top_cpu
        )

        process_details = []

        if relevant_memory:

            memory_lines = []

            for process in relevant_memory:

                name = process.get(
                    "name",
                    "Unknown",
                )

                pid = process.get(
                    "pid",
                    "N/A",
                )

                memory_percent = process.get(
                    "memory_percent",
                    0.0,
                )

                memory_lines.append(
                    f"- `{name}` "
                    f"(PID {pid}) — "
                    f"{memory_percent:.1f}% RAM"
                )

            process_details.append(
                "**Top memory-consuming processes:**\n"
                + "\n".join(memory_lines)
            )

        cpu_lines = []

        for process in relevant_cpu:

            cpu_percent = process.get(
                "cpu_percent",
                0.0,
            )

            if cpu_percent <= 1.0:
                continue

            name = process.get(
                "name",
                "Unknown",
            )

            pid = process.get(
                "pid",
                "N/A",
            )

            cpu_lines.append(
                f"- `{name}` "
                f"(PID {pid}) — "
                f"{cpu_percent:.1f}% CPU"
            )

        if cpu_lines:

            process_details.append(
                "**Top CPU-consuming processes:**\n"
                + "\n".join(cpu_lines)
            )

        if process_details:

            sections.append(
                "### Process details\n\n"
                + "\n\n".join(process_details)
            )

    # ========================================================
    # RECOMMENDED NEXT STEP
    # ========================================================

    next_steps = []

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

            next_steps.append(
                "Both basic connectivity checks succeeded. "
                "If the network problem is still occurring, "
                "the next step is to check the local Wi-Fi "
                "connection and adapter settings."
            )

        else:

            next_steps.append(
                "At least one connectivity check failed. "
                "The next step is to investigate the failing "
                "check and the local network configuration."
            )

    elif (
        "memory" in diagnostics
        or "processes" in diagnostics
    ):

        used_percent = diagnostics.get(
            "memory",
            {},
        ).get(
            "used_percent"
        )

        process_data = diagnostics.get(
            "processes",
            {}
        )

        recommendation_candidates = process_data.get(
            "recommendation_candidates",
            []
        )

        # If the diagnostic module does not provide the
        # candidates, create them safely from top_memory.
        if not recommendation_candidates:

            recommendation_candidates = _get_relevant_processes(
                process_data.get(
                    "top_memory",
                    [],
                )
            )

        relevant_memory = [
            process
            for process in recommendation_candidates
            if not _is_irrelevant_process(process)
        ]

        if (
            used_percent is not None
            and used_percent >= 85
        ):

            if relevant_memory:

                top_process = relevant_memory[0]

                process_name = top_process.get(
                    "name",
                    "the top memory-consuming process",
                )

                process_memory = top_process.get(
                    "memory_percent",
                    0.0,
                )

                next_steps.append(
                    f"Memory usage is high. "
                    f"{process_name} is currently using "
                    f"about {process_memory:.1f}% of RAM "
                    "among the user-controlled processes "
                    "detected. If you are not actively using "
                    "that application, save your work and "
                    "consider closing it, then check whether "
                    "system performance improves."
                )

            else:

                next_steps.append(
                    "Memory usage is high, but no suitable "
                    "user-controlled application was identified "
                    "as a safe candidate for closure. "
                    "Let's continue with another performance "
                    "check."
                )

        elif relevant_memory:

            top_process = relevant_memory[0]

            process_name = top_process.get(
                "name",
                "the top memory-consuming process",
            )

            process_memory = top_process.get(
                "memory_percent",
                0.0,
            )

            next_steps.append(
                f"The process check shows "
                f"{process_name} using about "
                f"{process_memory:.1f}% of RAM among the "
                "user-controlled processes detected. "
                "If the application is not needed, consider "
                "closing it and check whether performance improves."
            )

        else:

            next_steps.append(
                "No suitable user-controlled process was "
                "identified as a clear candidate for closure. "
                "Continue monitoring CPU and memory usage "
                "while the system is slow."
            )

    elif "disk" in diagnostics:

        free_gb = diagnostics["disk"].get(
            "free_gb"
        )

        if (
            free_gb is not None
            and free_gb < 20
        ):

            next_steps.append(
                "Free up unnecessary disk space and then "
                "check whether system performance improves."
            )

        else:

            next_steps.append(
                "Disk space does not appear to be the cause. "
                "Continue by checking memory usage, CPU usage, "
                "and resource-intensive applications."
            )

    else:

        next_steps.append(
            "The available diagnostic results do not "
            "establish the exact cause. Continue with "
            "the relevant troubleshooting steps."
        )

    sections.append(
        "### 3. Recommended next step\n\n"
        + "\n".join(
            f"- {step}"
            for step in next_steps
        )
    )

    return "\n\n".join(sections)


# ============================================================
# INPUT CAPTURE
# ============================================================

landing_placeholder = st.empty()

user_input = st.chat_input(
    "Describe your IT problem..."
)

prompt = user_input


# ============================================================
# LANDING PAGE
# ============================================================

if (
    not st.session_state.messages
    and not prompt
):

    with landing_placeholder.container():

        st.markdown(
            """
<div class="landing-wrapper">

<div class="landing-label">
IT SUPPORT
</div>

<div class="landing-title">
What can I help you
<span class="landing-title-highlight">
solve?
</span>
</div>

<div class="landing-description">
Tell me what's going wrong with your computer,
network, or software. Describe it naturally —
you don't need technical terms.
</div>

<div class="landing-hint">
Start with what happened and what you're seeing now.
</div>

</div>
""",
            unsafe_allow_html=True,
        )


# ============================================================
# START CHAT
# ============================================================

if prompt:

    landing_placeholder.empty()

    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt,
        }
    )

    st.session_state.memory.add_message(
        "user",
        prompt,
    )

    st.session_state.pending_query = prompt


# ============================================================
# ACTIVE CHAT FEED
# ============================================================

for message in st.session_state.messages:

    if message["role"] == "user":

        with st.chat_message(
            "user",
            avatar="👤",
        ):

            st.markdown(
                "<span class='user-msg'></span>",
                unsafe_allow_html=True,
            )

            st.write(
                message.get(
                    "content",
                    "",
                )
            )

    else:

        with st.chat_message(
            "assistant",
            avatar="🤖",
        ):

            st.markdown(
                "<span class='ai-msg'></span>",
                unsafe_allow_html=True,
            )

            route = message.get(
                "route"
            )

            if route:

                label = {
                    "rag": "Knowledge Base",
                    "network": "Network Check",
                    "performance": "System Check",
                    "follow_up": "Follow-up",
                }.get(
                    route,
                    "IT Support",
                )

                st.markdown(
                    f'<span class="ai-tag">{label}</span>',
                    unsafe_allow_html=True,
                )

            content = message.get(
                "content",
                "",
            )

            if content:

                st.markdown(
                    content
                )
# ============================================================
# PROCESS BACKEND REQUEST
# ============================================================

if (
    "pending_query" in st.session_state
    and st.session_state.pending_query
):

    query_to_process = (
        st.session_state.pending_query
    )

    del st.session_state.pending_query

    with st.spinner(
        "Analyzing your issue..."
    ):

        result = handle_query(
            query_to_process,
            conversation_history=(
                st.session_state.memory.get_history()
            ),
        )

    route = result.get(
        "route",
        "rag",
    )

    diagnostics = result.get(
        "diagnostics",
        {},
    )

    # ========================================================
    # RESPONSE SELECTION
    # ========================================================
    #
    # IMPORTANT:
    #
    # Only network/performance routes are allowed to display
    # live diagnostic results.
    #
    # RAG and follow-up responses must always use the answer
    # returned by the router.
    # ========================================================

    if route in {
        "network",
        "performance",
    }:

        final_answer = build_diagnostic_response(
            diagnostics
        )

    else:

        final_answer = result.get(
            "answer",
            "I couldn't generate a response.",
        )

    assistant_message = {
        "role": "assistant",
        "route": route,
        "content": final_answer,
    }

    st.session_state.memory.add_message(
        "assistant",
        final_answer,
    )

    st.session_state.messages.append(
        assistant_message
    )

    st.rerun()