from unittest.mock import patch

from app.diagnostics.memory import check_memory


def test_check_memory():
    mock_memory = type(
        "Memory",
        (),
        {
            "total": 16 * 1024**3,
            "available": 6 * 1024**3,
            "percent": 62.5
        }
    )()

    with patch(
        "app.diagnostics.memory.psutil.virtual_memory",
        return_value=mock_memory
    ):
        result = check_memory()

    assert result["total_gb"] == 16
    assert result["available_gb"] == 6
    assert result["used_percent"] == 62.5
from app.memory import ConversationMemory


def test_memory_stores_messages():
    memory = ConversationMemory()

    memory.add_message("user", "My Wi-Fi is not working")
    memory.add_message("assistant", "Let's check your network connection.")

    history = memory.get_history()

    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_memory_clear():
    memory = ConversationMemory()

    memory.add_message("user", "My computer is slow")
    memory.clear()

    assert memory.get_history() == []

def test_memory_preserves_conversation_order():
    memory = ConversationMemory()

    memory.add_message("user", "My Wi-Fi is not working")
    memory.add_message("assistant", "Let's check your network.")
    memory.add_message("user", "It still isn't working.")

    history = memory.get_history()

    assert history[0]["content"] == "My Wi-Fi is not working"
    assert history[1]["content"] == "Let's check your network."
    assert history[2]["content"] == "It still isn't working."