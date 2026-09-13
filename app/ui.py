import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import streamlit as st

from app.router import handle_query
from app.memory import ConversationMemory


st.set_page_config(
    page_title="AI IT Support Assistant",
    page_icon="🤖",
    layout="centered"
)


# -----------------------------
# Session State
# -----------------------------

if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()

if "messages" not in st.session_state:
    st.session_state.messages = []


# -----------------------------
# Page Header
# -----------------------------

st.title("🤖 AI IT Support Assistant")

st.write(
    "Describe your IT problem in everyday language and "
    "the assistant will find a solution or run diagnostics."
)


# -----------------------------
# Sidebar
# -----------------------------

with st.sidebar:
    st.header("Conversation")

    if st.button("🗑️ Clear Conversation"):
        st.session_state.memory.clear()
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.write("### Supported Features")
    st.write("🔎 Knowledge-base search")
    st.write("🧠 AI-generated troubleshooting")
    st.write("🌐 Network diagnostics")
    st.write("💾 Disk diagnostics")
    st.write("🧮 Memory diagnostics")
    st.write("🚨 Automatic escalation")
    st.write("💬 Multi-turn conversation")


# -----------------------------
# Display Previous Messages
# -----------------------------

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        if message["role"] == "user":
            st.write(message["content"])

        else:
            route = message.get("route")

            if route:
                st.caption(f"Selected route: {route}")

            # RAG response
            if route == "rag":
                st.markdown(message["content"])

            # Diagnostic response
            else:
                diagnostics = message.get("diagnostics", {})

                if diagnostics:
                    st.subheader("🔍 Diagnostic Results")

                    for name, diagnostic in diagnostics.items():

                        with st.expander(name.upper()):
                            st.json(diagnostic)

                # Escalation
                if message.get("escalation"):
                    st.warning("⚠️ Issue requires escalation.")

                    st.subheader("🎫 Support Ticket")
                    st.json(message["escalation"])


# -----------------------------
# User Input
# -----------------------------

problem = st.chat_input(
    "Describe your IT problem..."
)


# -----------------------------
# Process User Query
# -----------------------------

if problem:

    # Display user message immediately
    st.session_state.messages.append(
        {
            "role": "user",
            "content": problem
        }
    )

    # Add user message to conversation memory
    st.session_state.memory.add_message(
        "user",
        problem
    )

    # Run backend
    with st.spinner("Analyzing your problem..."):

        result = handle_query(
            problem,
            conversation_history=(
                st.session_state.memory.get_history()
            )
        )

    # Prepare assistant message
    assistant_message = {
        "role": "assistant",
        "route": result["route"]
    }

    # RAG result
    if result["route"] == "rag":

        assistant_message["content"] = result["answer"]

        st.session_state.memory.add_message(
            "assistant",
            result["answer"]
        )

    # Diagnostic result
    else:

        assistant_message["diagnostics"] = result.get(
            "diagnostics",
            {}
        )

        assistant_message["escalation"] = result.get(
            "escalation"
        )

        st.session_state.memory.add_message(
            "assistant",
            str(result)
        )

    # Save assistant response
    st.session_state.messages.append(
        assistant_message
    )

    # Refresh UI
    st.rerun()