
from src.odhikar.llm import llm_with_tools


print("\n--- GEMINI TOOL CALL TEST ---")

query = """
What is the maximum fine for riding a motorcycle
without wearing a helmet in Bangladesh?
"""

response = llm_with_tools.invoke(query)


print("\n--- GEMINI RESPONSE ---")

print("Content:", response.content)


print("\n--- TOOL CALLS ---")

print(response.tool_calls)


print("\n--- TEST COMPLETED ---")

