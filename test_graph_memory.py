
from src.odhikar.graph import (
    ask_odhikar_graph,
    odhikar_graph
)

THREAD_ID = "memory_demo_001"

config = {
    "configurable": {
        "thread_id": THREAD_ID
    }
}


# QUESTION 1
print("\n--- QUESTION 1 ---")

answer_1 = ask_odhikar_graph(
    """
    What is the maximum fine for riding a motorcycle
    without wearing a helmet in Bangladesh?
    """,
    thread_id=THREAD_ID
)

print(answer_1)


# CHECKPOINT INSPECTION
print("\n--- SQLITE MEMORY CHECK ---")

snapshot = odhikar_graph.get_state(config)

messages = snapshot.values.get("messages", [])

print("Saved messages:", len(messages))

for message in messages:
    print(
        type(message).__name__,
        str(message.content)[:200]
    )


# QUESTION 2
print("\n--- QUESTION 2 ---")

answer_2 = ask_odhikar_graph(
    "What about imprisonment?",
    thread_id=THREAD_ID
)

print(answer_2)


print("\n--- MEMORY TEST COMPLETED ---")
