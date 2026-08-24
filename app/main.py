from app.semantic_search import search_knowledge, format_article_response


def get_response(problem):
    article, score = search_knowledge(problem)

    if article is None:
        return "Sorry, I couldn't find a relevant troubleshooting article."

    response = format_article_response(article)
    response += f"\n\nSimilarity score: {round(float(score), 4)}"

    return response


def main():
    print("====================================")
    print("       AI IT Support Assistant")
    print("====================================")

    while True:
        problem = input("\nDescribe your IT problem (or type 'exit' to quit): ")

        if problem.lower().strip() == "exit":
            print("\nThank you for using AI IT Support Assistant!")
            break

        print("\n" + get_response(problem))


if __name__ == "__main__":
    main()