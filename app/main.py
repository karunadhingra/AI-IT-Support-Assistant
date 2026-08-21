from support import diagnose_problem


print("=================================")
print("   AI IT Support Assistant")
print("=================================")

problem = input("\nDescribe your IT problem: ")

result = diagnose_problem(problem)

print(f"\nCategory: {result['category']}")
print(f"Diagnosis: {result['diagnosis']}")

print("\nTroubleshooting steps:")

for number, step in enumerate(result["steps"], start=1):
    print(f"{number}. {step}")