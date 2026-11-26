
from src.odhikar.graph import ask_odhikar_graph


query = """
What is the maximum fine for riding a motorcycle
without wearing a helmet in Bangladesh?
"""

print("\n--- ODHIKAR LANGGRAPH AGENT ---")

answer = ask_odhikar_graph(query)

print("\n--- FINAL ANSWER ---")
print(answer)

print("\n--- TEST COMPLETED ---")
