import os
import numpy as np

from app.embeddings import model
from app.knowledge import KNOWLEDGE_PATH, load_knowledge_base


SIMILARITY_THRESHOLD = 0.5

_CACHED_MTIME = None
_CACHED_KNOWLEDGE = None
_CACHED_EMBEDDINGS = None


def create_article_text(article):
    return (
        f"Problem: {article['problem']}\n"
        f"Symptoms: {', '.join(article['symptoms'])}\n"
        f"Possible causes: {', '.join(article['possible_causes'])}\n"
        f"Troubleshooting steps: {', '.join(article['troubleshooting_steps'])}"
    )


def load_article_embeddings():
    global _CACHED_MTIME, _CACHED_KNOWLEDGE, _CACHED_EMBEDDINGS

    try:
        current_mtime = os.path.getmtime(KNOWLEDGE_PATH)
    except OSError:
        current_mtime = None

    if (
        _CACHED_KNOWLEDGE is not None
        and _CACHED_EMBEDDINGS is not None
        and current_mtime == _CACHED_MTIME
    ):
        return _CACHED_KNOWLEDGE, _CACHED_EMBEDDINGS

    knowledge = load_knowledge_base()
    article_texts = [create_article_text(article) for article in knowledge]
    embeddings = model.encode(article_texts)

    _CACHED_MTIME = current_mtime
    _CACHED_KNOWLEDGE = knowledge
    _CACHED_EMBEDDINGS = embeddings

    return knowledge, embeddings


def _calculate_similarities(query):
    knowledge, embeddings = load_article_embeddings()
    query_embedding = model.encode(query)

    similarities = np.dot(embeddings, query_embedding) / (
        np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
    )

    return knowledge, similarities


def search_knowledge_top_k(query, top_k=3):
    knowledge, similarities = _calculate_similarities(query)
    sorted_indexes = np.argsort(similarities)[::-1]

    results = []
    for index in sorted_indexes[:top_k]:
        score = similarities[index]
        if score >= SIMILARITY_THRESHOLD:
            results.append((knowledge[index], score))

    return results


def search_knowledge(query):
    knowledge, similarities = _calculate_similarities(query)
    best_index = np.argmax(similarities)
    best_score = similarities[best_index]

    if best_score < SIMILARITY_THRESHOLD:
        return None, best_score

    return knowledge[best_index], best_score


def format_article_response(article):
    response = [f"Problem: {article['problem']}", "\nSymptoms:"]
    for symptom in article["symptoms"]:
        response.append(f"- {symptom}")

    response.append("\nPossible causes:")
    for cause in article["possible_causes"]:
        response.append(f"- {cause}")

    response.append("\nTroubleshooting steps:")
    for i, step in enumerate(article["troubleshooting_steps"], start=1):
        response.append(f"{i}. {step}")

    response.append("\nEscalate when:")
    for condition in article["escalate_when"]:
        response.append(f"- {condition}")

    return "\n".join(response)