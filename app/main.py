from app.router import handle_query
from app.memory import ConversationMemory


def main():
    print("====================================")
    print("       AI IT Support Assistant")
    print("====================================")

    memory = ConversationMemory()

    while True:
        problem = input(
            "\nDescribe your IT problem (or type 'exit' to quit): "
        )

        if problem.lower().strip() == "exit":
            print("\nThank you for using AI IT Support Assistant!")
            break

        memory.add_message("user", problem)

        result = handle_query(
            problem,
            conversation_history=memory.get_history()
        )

        print(f"\nSelected route: {result['route']}")

        if result["route"] == "rag":
            print("\nAI Support Answer:")
            print(result["answer"])

            memory.add_message("assistant", result["answer"])

        else:
            print("\nDiagnostic Results:")

            for name, diagnostic in result["diagnostics"].items():
                print(f"\n{name.upper()}:")
                print(diagnostic)

            if "escalation" in result:
                print("\n⚠️ Issue requires escalation.")
                print("Support Ticket:")
                print(result["escalation"])

            memory.add_message("assistant", str(result))


if __name__ == "__main__":
    main()