
from src.odhikar.thread_manager import list_threads

print("\n--- SAVED CONVERSATIONS ---")

threads = list_threads()

if not threads:
    print("No saved conversations found.")

else:

    for index, thread_id in enumerate(threads, start=1):

        print(f"{index}. {thread_id}")

print("\nTotal Conversations:", len(threads))
