from app.semantic_search import search_knowledge_top_k


def build_context(query, top_k=3):
    results = search_knowledge_top_k(query, top_k=top_k)

    if not results:
        return None

    context_parts = []

    for article, score in results:
        article_context = (
            f"Problem: {article['problem']}\n"
            f"Symptoms: {', '.join(article['symptoms'])}\n"
            f"Possible causes: {', '.join(article['possible_causes'])}\n"
            f"Troubleshooting steps:\n"
        )

        for i, step in enumerate(
            article["troubleshooting_steps"],
            start=1
        ):
            article_context += f"{i}. {step}\n"

        article_context += "Escalate when:\n"

        for condition in article["escalate_when"]:
            article_context += f"- {condition}\n"

        context_parts.append(article_context)

    return "\n\n".join(context_parts)


if __name__ == "__main__":
    query = "Windows update keeps failing"

    context = build_context(query)

    print("\nUser query:")
    print(query)

    if context is None:
        print("\nNo relevant knowledge found.")
    else:
        print("\nRetrieved context:")
        print(context)
