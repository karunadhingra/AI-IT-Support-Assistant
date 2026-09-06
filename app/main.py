from app.rag import generate_answer


def main():
    print("====================================")
    print("       AI IT Support Assistant")
    print("====================================")

    while True:
        problem = input(
            "\nDescribe your IT problem (or type 'exit' to quit): "
        )

        if problem.lower().strip() == "exit":
            print("\nThank you for using AI IT Support Assistant!")
            break

        print("\nAI Support Answer:")
        print(generate_answer(problem))


if __name__ == "__main__":
    main()