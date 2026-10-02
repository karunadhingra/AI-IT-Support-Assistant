from unittest.mock import patch

from app.agent import decide_action


def test_agent_returns_network_diagnostics():

    fake_response = {
        "message": {
            "content": """
            {
                "action": "network_diagnostics",
                "reason": "The problem is network related.",
                "question": ""
            }
            """
        }
    }

    with patch(
        "app.agent.ollama.chat",
        return_value=fake_response
    ):

        result = decide_action(
            "My Wi-Fi is not working"
        )

    assert result["action"] == "network_diagnostics"
    assert result["question"] == ""


def test_agent_returns_follow_up():

    fake_response = {
        "message": {
            "content": """
            {
                "action": "follow_up",
                "reason": "More information is needed.",
                "question": "Can you see your Wi-Fi network in the available networks?"
            }
            """
        }
    }

    with patch(
        "app.agent.ollama.chat",
        return_value=fake_response
    ):

        result = decide_action(
            "My Wi-Fi isn't working"
        )

    assert result["action"] == "follow_up"
    assert result["question"]


def test_agent_returns_rag():

    fake_response = {
        "message": {
            "content": """
            {
                "action": "rag",
                "reason": "A knowledge base article can help.",
                "question": ""
            }
            """
        }
    }

    with patch(
        "app.agent.ollama.chat",
        return_value=fake_response
    ):

        result = decide_action(
            "My Bluetooth headphones won't connect"
        )

    assert result["action"] == "rag"


def test_agent_fallback_when_ollama_fails():

    with patch(
        "app.agent.ollama.chat",
        side_effect=Exception("Ollama unavailable")
    ):

        result = decide_action(
            "My Wi-Fi is not working"
        )

    assert result["action"] == "network_diagnostics"


def test_agent_uses_conversation_history():

    fake_response = {
        "message": {
            "content": """
            {
                "action": "network_diagnostics",
                "reason": "The conversation indicates a network issue.",
                "question": ""
            }
            """
        }
    }

    history = [
        {
            "role": "user",
            "content": "My Wi-Fi isn't working."
        },
        {
            "role": "assistant",
            "content": "Can you see the Wi-Fi network?"
        },
        {
            "role": "user",
            "content": "Yes, but it won't connect."
        },
    ]

    with patch(
        "app.agent.ollama.chat",
        return_value=fake_response
    ) as mock_chat:

        result = decide_action(
            "It still won't connect.",
            conversation_history=history
        )

    assert result["action"] == "network_diagnostics"

    prompt = mock_chat.call_args.kwargs["messages"][0]["content"]

    assert "My Wi-Fi isn't working." in prompt
    assert "Yes, but it won't connect." in prompt
    assert "It still won't connect." in prompt
def test_decide_action_handles_empty_follow_up_question():
    fake_response = {
        "message": {
            "content": (
                '{"action": "follow_up", '
                '"reason": "More information is needed.", '
                '"question": ""}'
            )
        }
    }

    with patch(
        "app.agent.ollama.chat",
        return_value=fake_response
    ):
        decision = decide_action(
            "My computer has a problem"
        )

    assert decision["action"] == "follow_up"
    assert decision["question"] != ""

def test_agent_does_not_force_diagnostics_for_network_security_question():
    fake_response = {
        "message": {
            "content": (
                '{"action": "rag", '
                '"reason": "The knowledge base can explain network security.", '
                '"question": ""}'
            )
        }
    }

    with patch(
        "app.agent.ollama.chat",
        return_value=fake_response
    ):
        result = decide_action(
            "How can I improve my network security?"
        )

    assert result["action"] == "rag"
def test_agent_does_not_force_diagnostics_for_performance_advice():
    fake_response = {
        "message": {
            "content": (
                '{"action": "rag", '
                '"reason": "The knowledge base can provide performance advice.", '
                '"question": ""}'
            )
        }
    }

    with patch(
        "app.agent.ollama.chat",
        return_value=fake_response
    ):
        result = decide_action(
            "How can I improve my computer's performance?"
        )

    assert result["action"] == "rag"
def test_network_diagnostic_reason_matches_selected_action():
    fake_response = {
        "message": {
            "content": (
                '{"action": "network_diagnostics", '
                '"reason": "The Wi-Fi connection is failing.", '
                '"question": ""}'
            )
        }
    }

    with patch(
        "app.agent.ollama.chat",
        return_value=fake_response,
    ):
        result = decide_action("My Wi-Fi is not working")

    assert result["action"] == "network_diagnostics"
    assert "performance diagnostics" not in result["reason"].lower()


def test_performance_diagnostics_does_not_require_follow_up():
    fake_response = {
        "message": {
            "content": (
                '{"action": "performance_diagnostics", '
                '"reason": "The computer is running slowly.", '
                '"question": ""}'
            )
        }
    }

    with patch(
        "app.agent.ollama.chat",
        return_value=fake_response,
    ):
        result = decide_action(
            "My computer is running very slowly"
        )

    assert result["action"] == "performance_diagnostics"
    assert result["question"] == ""