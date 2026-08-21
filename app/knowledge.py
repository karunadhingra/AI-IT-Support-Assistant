import json


def load_knowledge_base():
    with open("data/it_knowledge.json", "r", encoding="utf-8") as file:
        return json.load(file)

if __name__ == "__main__":
    knowledge = load_knowledge_base()

    print(f"Loaded {len(knowledge)} knowledge articles.")

    for article in knowledge:
        print(article["problem"])