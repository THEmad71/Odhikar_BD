
from src.odhikar.agent import ask_odhikar


print("\n--- ODHIKAR BD AI TEST ---")

query = """
What is the maximum fine for riding a motorcycle
without wearing a helmet in Bangladesh?
"""

answer = ask_odhikar(query)

print("\n--- FINAL ANSWER ---")
print(answer)

print("\n--- TEST COMPLETED ---")
