
from src.odhikar.thread_manager import (
    create_thread_id,
    ask_in_thread,
    get_thread_history,
    reset_thread
)


# ==========================================
# 1. CREATE TEST CONVERSATION
# ==========================================

thread_id = create_thread_id()

print("\n--- CREATE TEST CONVERSATION ---")

print("Thread ID:", thread_id)


# ==========================================
# 2. SAVE FIRST MESSAGE
# ==========================================

print("\n--- FIRST QUESTION ---")

answer = ask_in_thread(
    "What is the maximum fine for riding without a helmet?",
    thread_id
)

print("Answer:", answer)


# ==========================================
# 3. CHECK EXISTING HISTORY
# ==========================================

history_before = get_thread_history(thread_id)

print("\n--- BEFORE RESET ---")

print("Messages:", len(history_before))


# ==========================================
# 4. RESET CONVERSATION
# ==========================================

print("\n--- RESET CONVERSATION ---")

success = reset_thread(thread_id)

print("Reset successful:", success)


# ==========================================
# 5. VERIFY RESET
# ==========================================

history_after = get_thread_history(thread_id)

print("\n--- AFTER RESET ---")

print("Messages:", len(history_after))


# ==========================================
# 6. REUSE SAME THREAD ID
# ==========================================

print("\n--- REUSE THREAD ID ---")

new_answer = ask_in_thread(
    "What is the fine for driving without a valid licence?",
    thread_id
)

print("New Answer:", new_answer)

new_history = get_thread_history(thread_id)

print("New Messages:", len(new_history))


print("\n--- RESET TEST COMPLETED ---")
