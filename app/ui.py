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


if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()


if "messages" not in st.session_state:
    st.session_state.messages = []


st.title("🤖 AI IT Support Assistant")

st.write(
    "Describe your IT problem in everyday language and "
    "the AI assistant will investigate it, ask useful "
    "follow-up questions, or provide troubleshooting help."
)


with st.sidebar:
    st.header("Conversation")

    if st.button("🗑️ Clear Conversation"):
        st.session_state.memory.clear()
        st.session_state.messages = []
        st.rerun()

    st.divider()

    st.write("### Supported Features")
    st.write("🧠 AI agent decision-making")
    st.write("💬 Follow-up questions")
    st.write("🔎 Knowledge-base search")
    st.write("📚 Grounded RAG")
    st.write("🌐 Network diagnostics")
    st.write("💾 Disk diagnostics")
    st.write("🧮 Memory diagnostics")
    st.write("🚨 Automatic escalation")
    st.write("📝 Clean support tickets")


for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        if message["role"] == "user":
            st.write(message["content"])
            continue

        route = message.get("route")

        if route:
            st.caption(
                f"Agent action: {route}"
            )

        # -----------------------------------------------------
        # NORMAL AI RESPONSE / FOLLOW-UP
        # -----------------------------------------------------

        if route in ("rag", "follow_up"):
            st.markdown(
                message.get("content", "")
            )

        # -----------------------------------------------------
        # DIAGNOSTICS
        # -----------------------------------------------------

        elif route in ("network", "performance"):

            if message.get("content"):
                st.markdown(
                    message["content"]
                )

            diagnostics = message.get(
                "diagnostics",
                {}
            )

            if diagnostics:
                st.subheader("🔍 Diagnostic Results")

                for name, diagnostic in diagnostics.items():

                    with st.expander(
                        name.upper()
                    ):
                        st.json(diagnostic)

            # -------------------------------------------------
            # ESCALATION TICKET
            # -------------------------------------------------

            if message.get("escalation"):

                ticket = message["escalation"]

                st.warning(
                    "⚠️ This issue needs human IT support."
                )

                st.subheader("🎫 Support Ticket")

                st.write(
                    f"**{ticket.get('title', 'IT Support Ticket')}**"
                )

                st.write(
                    f"**Issue:** {ticket.get('issue', '')}"
                )

                st.write(
                    f"**Summary:** {ticket.get('summary', '')}"
                )

                st.write("**What we found:**")

                for finding in ticket.get(
                    "findings",
                    []
                ):
                    st.write(
                        f"- {finding}"
                    )

                st.write(
                    f"**Action needed:** "
                    f"{ticket.get('action_needed', '')}"
                )

                st.write(
                    f"**Priority:** "
                    f"{ticket.get('priority', 'Normal')}"
                )


problem = st.chat_input(
    "Describe your IT problem..."
)


if problem:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": problem,
        }
    )

    st.session_state.memory.add_message(
        "user",
        problem
    )

    with st.spinner(
        "AI agent is analyzing your problem..."
    ):

        result = handle_query(
            problem,
            conversation_history=(
                st.session_state.memory.get_history()
            )
        )

    route = result["route"]

    assistant_message = {
        "role": "assistant",
        "route": route,
    }

    # ---------------------------------------------------------
    # FOLLOW-UP OR RAG
    # ---------------------------------------------------------

    if route in ("follow_up", "rag"):

        answer = result.get(
            "answer",
            ""
        )

        assistant_message["content"] = answer

        st.session_state.memory.add_message(
            "assistant",
            answer
        )

    # ---------------------------------------------------------
    # DIAGNOSTICS
    # ---------------------------------------------------------

    else:

        assistant_message["content"] = result.get(
            "answer",
            ""
        )

        assistant_message["diagnostics"] = result.get(
            "diagnostics",
            {}
        )

        assistant_message["escalation"] = result.get(
            "escalation"
        )

        st.session_state.memory.add_message(
            "assistant",
            result.get(
                "answer",
                str(result)
            )
        )

    st.session_state.messages.append(
        assistant_message
    )

    st.rerun()