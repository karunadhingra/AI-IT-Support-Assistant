import sys
from pathlib import Path

# Allow tests to import modules from the app folder
APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from support import diagnose_problem
from app.semantic_search import search_knowledge


def test_wifi_problem():
    result = diagnose_problem("My Wi-Fi is not working")

    assert result["category"] == "Network"
    assert result["diagnosis"] == "Wi-Fi is not working"


def test_audio_problem():
    result = diagnose_problem("There is no sound coming from my computer")

    assert result["category"] == "Audio"
    assert result["diagnosis"] == "No sound on computer"


def test_slow_computer():
    result = diagnose_problem("My computer is running very slowly")

    assert result["category"] == "Performance"
    assert result["diagnosis"] == "Computer is running very slowly"


def test_bluetooth_problem():
    result = diagnose_problem("My Bluetooth headphones won't connect")

    assert result["category"] == "Bluetooth"
    assert result["diagnosis"] == "Bluetooth device is not connecting"


def test_internet_problem():
    result = diagnose_problem(
        "Wi-Fi says connected but websites won't open"
    )

    assert result["category"] == "Network"
    assert result["diagnosis"] == (
        "Internet is connected but websites are not loading"
    )


def test_unknown_problem():
    result = diagnose_problem("My printer is making strange noises")

    assert result["category"] == "Unknown"

def test_semantic_search_rejects_unrelated_query():
    article, score = search_knowledge(
        "My computer is showing a blue screen"
    )

    assert article is None
    assert score < 0.5

def test_semantic_search_finds_relevant_article():
    article, score = search_knowledge(
        "My Bluetooth headphones won't connect"
    )

    assert article is not None
    assert article["problem"] == "Bluetooth device is not connecting"
    assert score >= 0.5