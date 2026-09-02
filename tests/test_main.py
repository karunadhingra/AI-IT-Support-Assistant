import sys
from pathlib import Path

# Allow tests to import modules from the app folder
APP_DIR = Path(__file__).resolve().parents[1] / "app"
sys.path.insert(0, str(APP_DIR))

from app.support import diagnose_problem
from app.semantic_search import (
    search_knowledge,
    search_knowledge_top_k,
    format_article_response,
)
from app.main import get_response

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
    result = diagnose_problem("My washing machine is leaking water")

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

def test_format_article_response():
    article = {
        "problem": "Wi-Fi is not working",
        "symptoms": [
            "Cannot connect to Wi-Fi",
            "Wi-Fi keeps disconnecting"
        ],
        "possible_causes": [
            "Wi-Fi is disabled",
            "Router problem"
        ],
        "troubleshooting_steps": [
            "Check whether Wi-Fi is enabled.",
            "Restart the Wi-Fi connection."
        ],
        "escalate_when": [
            "The problem continues after restarting the router."
        ]
    }

    response = format_article_response(article)

    assert "Problem: Wi-Fi is not working" in response
    assert "- Cannot connect to Wi-Fi" in response
    assert "- Wi-Fi is disabled" in response
    assert "1. Check whether Wi-Fi is enabled." in response
    assert "- The problem continues after restarting the router." in response

def test_get_response_for_valid_problem():
    response = get_response("My Bluetooth headphones won't connect")

    assert "Bluetooth device is not connecting" in response
    assert "Troubleshooting steps:" in response
    assert "Similarity score:" in response

def test_get_response_for_unknown_problem():
    response = get_response("My printer is making strange noises")

    assert "Sorry, I couldn't find a relevant troubleshooting article." in response

def test_top_k_returns_results():
    results = search_knowledge_top_k(
        "My Bluetooth headphones won't connect",
        top_k=3
    )

    assert len(results) <= 3
    assert len(results) > 0


def test_top_k_results_are_sorted():
    results = search_knowledge_top_k(
        "My Bluetooth headphones won't connect",
        top_k=3
    )

    scores = [score for article, score in results]

    assert scores == sorted(scores, reverse=True)


def test_top_k_rejects_irrelevant_query():
    results = search_knowledge_top_k(
        "My washing machine is leaking",
        top_k=3
    )

    assert results == []