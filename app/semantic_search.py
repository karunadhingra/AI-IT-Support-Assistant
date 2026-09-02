import numpy as np
from functools import lru_cache


from app.embeddings import model
from app.knowledge import load_knowledge_base


def create_article_text(article):
    return (
        f"Problem: {article['problem']}\n"
        f"Symptoms: {', '.join(article['symptoms'])}\n"
        f"Possible causes: {', '.join(article['possible_causes'])}\n"
        f"Troubleshooting steps: {', '.join(article['troubleshooting_steps'])}"
    )

@lru_cache(maxsize=1)
def load_article_embeddings():
    knowledge = load_knowledge_base()

    article_texts = [
        create_article_text(article)
        for article in knowledge
    ]

    embeddings = model.encode(article_texts)

    return knowledge, embeddings

def search_knowledge_top_k(query, top_k=3):
    knowledge, embeddings = load_article_embeddings()

    query_embedding = model.encode(query)

    similarities = np.dot(embeddings, query_embedding) / (
        np.linalg.norm(embeddings, axis=1)
        * np.linalg.norm(query_embedding)
    )

    
    sorted_indexes = np.argsort(similarities)[::-1]

    results = []

    for index in sorted_indexes[:top_k]:
        score = similarities[index]

        
        if score >= 0.5:
            results.append((knowledge[index], score))

    return results


def search_knowledge(query):
    results = search_knowledge_top_k(query, top_k=1)

    if not results:
        knowledge, embeddings = load_article_embeddings()

        query_embedding = model.encode(query)

        similarities = np.dot(embeddings, query_embedding) / (
            np.linalg.norm(embeddings, axis=1)
            * np.linalg.norm(query_embedding)
        )

        best_score = np.max(similarities)

        return None, best_score

    return results[0]



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

    results = search_knowledge_top_k(query, top_k=3)

    print("\nUser query:")
    print(query)

    if not results:
        print("\nNo relevant articles found.")
    else:
        print(f"\nTop {len(results)} relevant articles:")

        for i, (article, score) in enumerate(results, start=1):
            print(f"\n--- Result {i} ---")
            print(f"Problem: {article['problem']}")
            print(f"Similarity score: {round(float(score), 4)}")