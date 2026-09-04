from app.semantic_search import (
    search_knowledge,
    search_knowledge_top_k,
    format_article_response,
)

from app.main import get_response
from app.rag import build_context

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

def test_build_context_returns_relevant_knowledge():
    context = build_context("My printer is not printing")

    assert context is not None
    assert "Printer is not working" in context


def test_build_context_returns_overheating_knowledge():
    context = build_context("My laptop is getting very hot")

    assert context is not None
    assert "Laptop is overheating" in context


def test_build_context_returns_none_for_irrelevant_query():
    context = build_context("My washing machine is leaking water")

    assert context is None