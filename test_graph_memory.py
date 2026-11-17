
from src.odhikar.graph import ask_odhikar_graph


# Same thread ID for both questions
THREAD_ID = "memory_demo_001"


# QUESTION 1
print("\n--- QUESTION 1 ---")

question_1 = """
What is the maximum fine for riding a motorcycle
without wearing a helmet in Bangladesh?
"""

answer_1 = ask_odhikar_graph(
    question_1,
    thread_id=THREAD_ID
)

print("Answer 1:")
print(answer_1)


# QUESTION 2
print("\n--- QUESTION 2 ---")

question_2 = """
What about imprisonment?
"""

answer_2 = ask_odhikar_graph(
    question_2,
    thread_id=THREAD_ID
)

print("Answer 2:")
print(answer_2)


print("\n--- MEMORY TEST COMPLETED ---")
