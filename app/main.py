from app.semantic_search import search_knowledge, format_article_response


print("====================================")
print("       AI IT Support Assistant")
print("====================================")


problem = input("\nDescribe your IT problem: ")

article, score = search_knowledge(problem)

if article is None:
    print("\nSorry, I couldn't find a relevant troubleshooting article.")
else:
    print("\n" + format_article_response(article))
    print("\nSimilarity score:", round(float(score), 4))