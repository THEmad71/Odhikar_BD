
from src.odhikar.thread_manager import (
    list_threads,
    delete_thread
)


# ==========================================
# 1. SHOW AVAILABLE THREADS
# ==========================================

print("\n--- AVAILABLE CONVERSATIONS ---")

threads = list_threads()

if not threads:
    print("No conversations available.")
    raise SystemExit

for index, thread_id in enumerate(threads, start=1):
    print(f"{index}. {thread_id}")

print("Total:", len(threads))


# ==========================================
# 2. SELECT CONVERSATION
# ==========================================

selection = input(
    "\nEnter conversation number or Thread ID: "
).strip()


# Support selection by number
if selection.isdigit():

    index = int(selection) - 1

    if 0 <= index < len(threads):
        selected_thread = threads[index]
    else:
        selected_thread = None

# Support selection by Thread ID
elif selection in threads:

    selected_thread = selection

else:

    selected_thread = None


# ==========================================
# 3. CONFIRM DELETION
# ==========================================

if selected_thread is None:

    print("\nConversation not found.")

else:

    print("\nSelected Thread:", selected_thread)

    confirmation = input(
        "Type DELETE to confirm: "
    ).strip()

    if confirmation == "DELETE":

        success = delete_thread(selected_thread)

        if success:
            print("\nConversation deleted successfully!")
        else:
            print("\nConversation deletion failed.")

    else:

        print("\nDeletion cancelled.")


# ==========================================
# 4. VERIFY REMAINING THREADS
# ==========================================

print("\n--- REMAINING CONVERSATIONS ---")

remaining_threads = list_threads()

for index, thread in enumerate(remaining_threads, start=1):
    print(f"{index}. {thread}")

print("\nTotal:", len(remaining_threads))
