from src.odhikar.user_manager import list_user_threads
from uuid import uuid4

from src.odhikar.user_manager import (
    list_user_threads,
    create_user_thread
)

from src.odhikar.session_manager import validate_session

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


# ==========================================
# 7. USER-OWNED CONVERSATION ACCESS
# ==========================================

def ask_in_user_thread(
    user_id: str,
    thread_id: str,
    query: str
) -> str:

    if not user_id or not thread_id:
        return "User ID and Thread ID are required."

    # Retrieve conversations owned by this user
    user_threads = list_user_threads(user_id)

    # Verify ownership
    owns_thread = any(
        thread["thread_id"] == thread_id
        for thread in user_threads
    )

    if not owns_thread:
        return "Access denied: This conversation does not belong to this user."

    # Execute question only after ownership verification
    return ask_in_thread(query, thread_id)


# ==========================================
# 8. CREATE AUTHENTICATED CONVERSATION
# ==========================================

def create_authenticated_thread(session_token: str):

    # Verify login session
    user = validate_session(session_token)

    if user is None:
        return None

    # Create conversation for authenticated user
    return create_user_thread(user["user_id"])


# ==========================================
# 9. ASK QUESTION WITH AUTHENTICATION
# ==========================================

def ask_in_authenticated_thread(
    session_token: str,
    thread_id: str,
    query: str
) -> str:

    # STEP 1: Validate session
    user = validate_session(session_token)

    if user is None:
        return "Authentication required. Please login first."

    # STEP 2: Validate input
    if not isinstance(thread_id, str) or not thread_id.strip():
        return "A valid Thread ID is required."

    if not isinstance(query, str) or not query.strip():
        return "Please enter a valid question."

    # STEP 3: Check conversation ownership
    user_threads = list_user_threads(user["user_id"])

    owns_thread = any(
        thread["thread_id"] == thread_id
        for thread in user_threads
    )

    if not owns_thread:
        return "Access denied: This conversation does not belong to this user."

    # STEP 4: Execute AI agent
    return ask_in_thread(
        query,
        thread_id
    )
