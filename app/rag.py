import ollama

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


def generate_answer(query):
    context = build_context(query, top_k=1)

    if context is None:
        return "Sorry, I couldn't find a relevant troubleshooting article."

    prompt = f"""
You are an AI IT Support Assistant.

Use ONLY the information in the context below.

Give the response in this exact structure:

Diagnosis:
<one short sentence describing the likely issue>

Troubleshooting steps:
Copy the troubleshooting steps from the context EXACTLY.
Do not rewrite, combine, reorder, or invent steps.

Escalate when:
Copy the escalation conditions from the context EXACTLY.
Do not rewrite or invent conditions.

Rules:
- Do not ask the user a follow-up question.
- Do not add any information that is not present in the context.
- Keep the response concise.
- Preserve the original troubleshooting steps exactly.

Context:
{context}

User problem:
{query}

Answer:
"""

    response = ollama.chat(
        model="llama3.2:3b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response["message"]["content"]


if __name__ == "__main__":
    query = "My Bluetooth headphones won't connect"

    print("\nUser query:")
    print(query)

    answer = generate_answer(query)

    print("\nAI Support Answer:")
    print(answer)