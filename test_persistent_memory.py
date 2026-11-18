
from src.odhikar.graph import (
    ask_odhikar_graph,
    get_conversation_history
)

THREAD_ID = "memory_test_002"


# ==========================================
# CHECK PREVIOUS MEMORY
# ==========================================

print("\n--- PERSISTENT MEMORY CHECK ---")

history = get_conversation_history(THREAD_ID)

print("Previous Messages:", len(history))


# ==========================================
# ASK A FOLLOW-UP QUESTION
# ==========================================

print("\n--- NEW QUESTION AFTER RESTART ---")

question = """
What was the offence ID for the offence
we discussed earlier?
"""

answer = ask_odhikar_graph(
    question,
    thread_id=THREAD_ID
)

print("Answer:")
print(answer)


# ==========================================
# CHECK UPDATED MEMORY
# ==========================================

history_after = get_conversation_history(THREAD_ID)

print("\n--- UPDATED MEMORY ---")
print("Messages Before:", len(history))
print("Messages After:", len(history_after))

print("\n--- PERSISTENT MEMORY TEST COMPLETED ---")
