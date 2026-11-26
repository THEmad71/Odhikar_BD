
from src.odhikar.thread_manager import (
    create_thread_id,
    ask_in_thread,
    get_thread_history
)


# Create new conversation
thread_id = create_thread_id()

print("New Thread ID:", thread_id)


# Ask question
answer = ask_in_thread(
    "What is the maximum fine for riding a motorcycle without wearing a helmet?",
    thread_id
)

print("\nAnswer:")
print(answer)


# Retrieve history
history = get_thread_history(thread_id)

print("\nConversation Messages:", len(history))
