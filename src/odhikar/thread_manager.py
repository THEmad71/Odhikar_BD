
from uuid import uuid4


from src.odhikar.graph import (
    ask_odhikar_graph,
    get_conversation_history,
    checkpointer
)


# ==========================================
# 1. CREATE NEW THREAD
# ==========================================

def create_thread_id():

    return f"odhikar_{uuid4().hex[:12]}"


# ==========================================
# 2. ASK QUESTION IN A THREAD
# ==========================================

def ask_in_thread(query: str, thread_id: str):

    return ask_odhikar_graph(
        query,
        thread_id=thread_id
    )


# ==========================================
# 3. GET THREAD HISTORY
# ==========================================

def get_thread_history(thread_id: str):

    return get_conversation_history(thread_id)


# ==========================================
# 4. LIST ALL SAVED THREADS
# ==========================================

def list_threads():

    threads = set()

    # Retrieve saved checkpoints
    for checkpoint in checkpointer.list(None):

        config = checkpoint.config

        configurable = config.get(
            "configurable", {}
        )

        thread_id = configurable.get("thread_id")

        if thread_id:
            threads.add(thread_id)

    return sorted(threads)

# ==========================================
# 5. DELETE A CONVERSATION
# ==========================================

def delete_thread(thread_id: str) -> bool:

    # Validate input
    if not isinstance(thread_id, str):
        return False

    thread_id = thread_id.strip()

    if not thread_id:
        return False

    # Check whether conversation exists
    if thread_id not in list_threads():
        return False

    # Delete conversation from SQLite
    checkpointer.delete_thread(thread_id)

    # Verify deletion
    return thread_id not in list_threads()


# ==========================================
# 6. RESET A CONVERSATION
# ==========================================

def reset_thread(thread_id: str) -> bool:

    # Validate input
    if not isinstance(thread_id, str):
        return False

    thread_id = thread_id.strip()

    if not thread_id:
        return False

    # Check whether thread exists
    if thread_id not in list_threads():
        return False

    # Clear existing conversation checkpoints
    checkpointer.delete_thread(thread_id)

    # Verify that old history is cleared
    return thread_id not in list_threads()
