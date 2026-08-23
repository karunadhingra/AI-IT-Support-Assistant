import numpy as np

from app import knowledge
from app.embeddings import model
from app.knowledge import load_knowledge_base


def create_article_text(article):
    return (
        f"Problem: {article['problem']}\n"
        f"Symptoms: {', '.join(article['symptoms'])}\n"
        f"Possible causes: {', '.join(article['possible_causes'])}\n"
        f"Troubleshooting steps: {', '.join(article['troubleshooting_steps'])}"
    )


def load_article_embeddings():
    knowledge = load_knowledge_base()

    article_texts = [
        create_article_text(article)
        for article in knowledge
    ]

    embeddings = model.encode(article_texts)

    return knowledge, embeddings


def search_knowledge(query):
    knowledge, embeddings = load_article_embeddings()

    query_embedding = model.encode(query)

    similarities = np.dot(embeddings, query_embedding) / (
        np.linalg.norm(embeddings, axis=1)
        * np.linalg.norm(query_embedding)
    )

    best_index = np.argmax(similarities)
    best_score = similarities[best_index]

    if best_score < 0.5:
        return None, best_score

    return knowledge[best_index], best_score


def format_article_response(article):
    response = []

    response.append(f"Problem: {article['problem']}")

    response.append("\nSymptoms:")
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

if __name__ == "__main__":
    query = "My Bluetooth headphones won't connect"

    article, score = search_knowledge(query)

    print("\nUser query:")
    print(query)
    if article is None:
        print("\nNo relevant article found.")
    else:
        print("\n"+ format_article_response(article))

        print("\nSimilarity score:")
        print(round(float(score), 4))