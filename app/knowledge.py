import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_PATH = PROJECT_ROOT / "data" / "it_knowledge.json"


def load_knowledge_base():
    with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


if __name__ == "__main__":
    knowledge = load_knowledge_base()
    print(f"Loaded {len(knowledge)} knowledge articles.")
    for article in knowledge:
        print(article["problem"])