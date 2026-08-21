from knowledge import load_knowledge_base


def search_knowledge_base(problem):
    problem = problem.lower()
    knowledge_base = load_knowledge_base()

    stop_words = {
        "my", "is", "the", "a", "an", "i", "am",
        "not", "working", "on", "in", "to", "and"
    }

    problem_words = set(problem.split()) - stop_words

    scored_results = []

    for article in knowledge_base:
        searchable_text = (
            article["problem"]
            + " "
            + " ".join(article["symptoms"])
            + " "
            + " ".join(article["possible_causes"])
        ).lower()

        score = sum(
            1 for word in problem_words
            if word in searchable_text
        )

        if score > 0:
            scored_results.append((score, article))

    scored_results.sort(reverse=True, key=lambda item: item[0])

    return [article for score, article in scored_results]
def diagnose_problem(problem):
    results = search_knowledge_base(problem)

    if not results:
        return {
            "category": "Unknown",
            "diagnosis": "I could not find a relevant troubleshooting article.",
            "steps": [
                "Describe the problem in more detail."
            ]
        }

    article = results[0]

    return {
        "category": article["category"],
        "diagnosis": article["problem"],
        "steps": article["troubleshooting_steps"]
    }
 