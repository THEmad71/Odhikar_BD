
from src.odhikar.user_manager import (
    create_user,
    get_user,
    create_user_thread,
    list_user_threads
)


# ==========================================
# 1. CREATE USER
# ==========================================

print("\n--- CREATE USER ---")

user = create_user("Test User")

print("User Created:")
print(user)


# ==========================================
# 2. GET USER
# ==========================================

print("\n--- USER INFORMATION ---")

user_info = get_user(user["user_id"])

print(user_info)


# ==========================================
# 3. CREATE CONVERSATIONS
# ==========================================

print("\n--- CREATE USER CONVERSATIONS ---")

thread_1 = create_user_thread(
    user["user_id"]
)

thread_2 = create_user_thread(
    user["user_id"]
)

print("Thread 1:", thread_1)
print("Thread 2:", thread_2)


# ==========================================
# 4. LIST USER CONVERSATIONS
# ==========================================

print("\n--- USER CONVERSATION LIST ---")

threads = list_user_threads(
    user["user_id"]
)

for thread in threads:
    print(thread)

print("\nTotal Conversations:", len(threads))


print("\n--- USER MANAGEMENT TEST COMPLETED ---")
