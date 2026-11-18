
from src.odhikar.graph import (
    ask_odhikar_graph,
    odhikar_graph
)


# Use a fresh thread ID for a clean test
THREAD_ID = "memory_test_002"

config = {
    "configurable": {
        "thread_id": THREAD_ID
    }
}


# ==========================================
# TEST 1: FIRST QUESTION
# ==========================================

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


# ==========================================
# TEST 2: CHECK SQLITE MEMORY
# ==========================================

print("\n--- SQLITE MEMORY CHECK ---")

snapshot = odhikar_graph.get_state(config)

saved_messages = snapshot.values.get(
    "messages", []
)

print("Thread ID:", THREAD_ID)
print("Saved Messages:", len(saved_messages))

for i, message in enumerate(saved_messages, start=1):

    print(f"\nMessage {i}")
    print("Type:", type(message).__name__)
    print("Content:", str(message.content)[:250])


# ==========================================
# TEST 3: FOLLOW-UP QUESTION
# ==========================================

print("\n--- QUESTION 2 ---")

question_2 = """
What about imprisonment for the same offence?
"""

answer_2 = ask_odhikar_graph(
    question_2,
    thread_id=THREAD_ID
)

print("Answer 2:")
print(answer_2)


# ==========================================
# TEST 4: FINAL MEMORY COUNT
# ==========================================

print("\n--- FINAL MEMORY CHECK ---")

final_snapshot = odhikar_graph.get_state(config)

final_messages = final_snapshot.values.get(
    "messages", []
)

print("Total Saved Messages:", len(final_messages))

print("\n--- MEMORY TEST COMPLETED ---")
