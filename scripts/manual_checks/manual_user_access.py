
from src.odhikar.user_manager import (
    create_user,
    create_user_thread
)

from src.odhikar.thread_manager import (
    ask_in_user_thread
)


# Create two users
user_a = create_user("User A")
user_b = create_user("User B")


# Create conversation for User A
thread_a = create_user_thread(
    user_a["user_id"]
)


# User A accesses own conversation
print("\n--- USER A ACCESS TEST ---")

answer = ask_in_user_thread(
    user_a["user_id"],
    thread_a,
    "What is the maximum fine for riding a motorcycle without wearing a helmet?"
)

print(answer)


# User B tries to access User A's conversation
print("\n--- USER B ACCESS TEST ---")

unauthorized = ask_in_user_thread(
    user_b["user_id"],
    thread_a,
    "What was the previous conversation about?"
)

print(unauthorized)


print("\n--- ACCESS CONTROL TEST COMPLETED ---")
