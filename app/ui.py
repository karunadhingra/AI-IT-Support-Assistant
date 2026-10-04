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


/* ============================================================
   APPLICATION
   ============================================================ */

.stApp {
    background-color: #1e1e1e;
    color: #ececec;
}

.main .block-container {
    max-width: 820px;
    padding-top: 1.5rem;
    padding-bottom: 8rem;
}


/* ============================================================
   SIDEBAR
   ============================================================ */

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


/* ============================================================
   LANDING PAGE
   ============================================================ */

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


/* ============================================================
   CHAT MESSAGES
   ============================================================ */

[data-testid="stChatMessage"] {
    background-color: transparent !important;
    border: none !important;
    padding: 0.75rem 0 !important;
}


/* ============================================================
   USER MESSAGE
   ============================================================ */

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


/* User bubble */

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


/* ============================================================
   ASSISTANT MESSAGE
   ============================================================ */

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


/* ============================================================
   CHAT INPUT
   ============================================================ */

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


/* ============================================================
   DIAGNOSTICS
   ============================================================ */

[data-testid="stExpander"] {
    border: 1px solid #3a3a3a !important;
    border-radius: 10px !important;
    background-color: #252525 !important;
}


/* ============================================================
   ANIMATION
   ============================================================ */

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
# HELPER FUNCTIONS
# ============================================================

def format_diagnostic_points(
    raw_answer,
    diagnostics,
):
    """Turns diagnostic data into simple, readable bullet points."""

    points = []

    if "ping" in diagnostics:

        success = diagnostics["ping"].get(
            "success"
        )

        points.append(
            "- **Internet connection:** Working properly."
            if success
            else
            "- **Internet connection:** Offline or unreachable."
        )

    if "dns" in diagnostics:

        success = diagnostics["dns"].get(
            "success"
        )

        points.append(
            "- **Web routing (DNS):** Working fine."
            if success
            else
            "- **Web routing (DNS):** Failing to find web addresses."
        )

    if "disk" in diagnostics:

        free_gb = diagnostics["disk"].get(
            "free_gb"
        )

        if free_gb is not None:

            points.append(
                f"- **Available disk space:** "
                f"{free_gb:.1f} GB remaining."
            )

    if "memory" in diagnostics:

        used_percent = diagnostics["memory"].get(
            "used_percent"
        )

        if used_percent is not None:

            points.append(
                f"- **Memory (RAM) usage:** "
                f"{used_percent:.1f}% currently in use."
            )

    formatted = ""

    if raw_answer:

        formatted += (
            f"{raw_answer}\n\n"
        )

    if points:

        formatted += (
            "**Here is what I checked:**\n"
            + "\n".join(points)
        )

    return formatted.strip()


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

    raw_answer = result.get(
        "answer",
        "I couldn't generate a response.",
    )

    diagnostics = result.get(
        "diagnostics",
        {},
    )

    final_answer = format_diagnostic_points(
        raw_answer,
        diagnostics,
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