
"""
Odhikar BD - Secure Thread Manager

Features:
1. Authenticated conversation creation
2. Authenticated conversation access
3. Thread ownership verification
4. Conversation history retrieval
5. User-specific thread listing
6. Secure conversation deletion
7. Secure conversation reset
8. SQLite checkpoint management

IMPORTANT:
All public user-facing operations require
a valid authenticated session token.
"""


# ==========================================
# 1. IMPORTS
# ==========================================

from src.odhikar.user_manager import (
    create_user_thread,
    list_user_threads,
    delete_user_thread_record
)

from src.odhikar.session_manager import (
    validate_session
)

from src.odhikar.graph import (
    ask_odhikar_graph,
    get_conversation_history,
    checkpointer
)


# ==========================================
# 2. INPUT VALIDATION
# ==========================================

def _valid_thread_id(thread_id: str) -> bool:

    return (
        isinstance(thread_id, str)
        and bool(thread_id.strip())
        and len(thread_id) <= 256
    )


def _valid_query(query: str) -> bool:

    return (
        isinstance(query, str)
        and bool(query.strip())
    )


# ==========================================
# 3. VERIFY THREAD OWNERSHIP
# ==========================================

def _owns_thread(
    user_id: str,
    thread_id: str
) -> bool:

    if not isinstance(user_id, str) or not user_id.strip():
        return False

    if not _valid_thread_id(thread_id):
        return False

    user_threads = list_user_threads(
        user_id.strip()
    )

    return any(
        thread.get("thread_id") == thread_id.strip()
        for thread in user_threads
    )


# ==========================================
# 4. GET CHECKPOINT THREAD IDS
# ==========================================

def _get_checkpoint_thread_ids() -> set:

    thread_ids = set()

    for checkpoint in checkpointer.list(None):

        config = checkpoint.config or {}

        configurable = config.get(
            "configurable", {}
        )

        thread_id = configurable.get("thread_id")

        if thread_id:
            thread_ids.add(thread_id)

    return thread_ids


# ==========================================
# 5. DELETE THREAD CHECKPOINT
# ==========================================

def _delete_thread_checkpoint(
    thread_id: str
) -> bool:

    if not _valid_thread_id(thread_id):
        return False

    thread_id = thread_id.strip()

    try:

        # Delete all LangGraph checkpoints
        checkpointer.delete_thread(thread_id)

        # Verify deletion
        return (
            thread_id not in _get_checkpoint_thread_ids()
        )

    except Exception as error:

        print(
            f"Checkpoint deletion error: {error}"
        )

        return False


# ==========================================
# 6. CREATE AUTHENTICATED THREAD
# ==========================================

def create_authenticated_thread(
    session_token: str
):

    # Validate session
    user = validate_session(session_token)

    if user is None:
        return None

    # Create conversation for authenticated user
    try:

        thread_id = create_user_thread(
            user["user_id"]
        )

        return thread_id

    except Exception as error:

        print(
            f"Thread creation error: {error}"
        )

        return None


# ==========================================
# 7. ASK QUESTION IN AUTHENTICATED THREAD
# ==========================================

def ask_in_authenticated_thread(
    session_token: str,
    thread_id: str,
    query: str
) -> str:

    # STEP 1: Validate session
    user = validate_session(session_token)

    if user is None:

        return (
            "Authentication required. "
            "Please login first."
        )

    # STEP 2: Validate thread ID
    if not _valid_thread_id(thread_id):

        return "A valid Thread ID is required."

    # STEP 3: Validate query
    if not _valid_query(query):

        return "Please enter a valid question."

    thread_id = thread_id.strip()

    # STEP 4: Verify ownership
    if not _owns_thread(
        user["user_id"],
        thread_id
    ):

        return (
            "Access denied: This conversation "
            "does not belong to this user."
        )

    # STEP 5: Execute AI agent
    return ask_odhikar_graph(
        query.strip(),
        thread_id=thread_id
    )


# ==========================================
# 8. GET AUTHENTICATED THREAD HISTORY
# ==========================================

def get_authenticated_thread_history(
    session_token: str,
    thread_id: str
) -> list:

    # Validate session
    user = validate_session(session_token)

    if user is None:
        return []

    if not _valid_thread_id(thread_id):
        return []

    thread_id = thread_id.strip()

    # Verify ownership
    if not _owns_thread(
        user["user_id"],
        thread_id
    ):
        return []

    # Retrieve conversation history
    try:

        return get_conversation_history(
            thread_id
        )

    except Exception as error:

        print(
            f"History retrieval error: {error}"
        )

        return []


# ==========================================
# 9. LIST AUTHENTICATED USER THREADS
# ==========================================

def list_authenticated_threads(
    session_token: str
) -> list:

    # Validate session
    user = validate_session(session_token)

    if user is None:
        return []

    # Return only authenticated user's threads
    return list_user_threads(
        user["user_id"]
    )


# ==========================================
# 10. RESET AUTHENTICATED THREAD
# ==========================================

def reset_authenticated_thread(
    session_token: str,
    thread_id: str
) -> bool:

    # STEP 1: Validate session
    user = validate_session(session_token)

    if user is None:
        return False

    if not _valid_thread_id(thread_id):
        return False

    thread_id = thread_id.strip()

    # STEP 2: Verify ownership
    if not _owns_thread(
        user["user_id"],
        thread_id
    ):
        return False

    # STEP 3: Delete conversation checkpoints
    reset_success = _delete_thread_checkpoint(
        thread_id
    )

    if not reset_success:
        return False

    # STEP 4: Verify ownership mapping remains
    return _owns_thread(
        user["user_id"],
        thread_id
    )


# ==========================================
# 11. DELETE AUTHENTICATED THREAD
# ==========================================

def delete_authenticated_thread(
    session_token: str,
    thread_id: str
) -> bool:

    # STEP 1: Validate session
    user = validate_session(session_token)

    if user is None:
        return False

    if not _valid_thread_id(thread_id):
        return False

    thread_id = thread_id.strip()

    # STEP 2: Verify ownership
    if not _owns_thread(
        user["user_id"],
        thread_id
    ):
        return False

    # STEP 3: Delete LangGraph checkpoints
    checkpoint_deleted = _delete_thread_checkpoint(
        thread_id
    )

    if not checkpoint_deleted:
        return False

    # STEP 4: Delete user-thread mapping
    mapping_deleted = delete_user_thread_record(
        user["user_id"],
        thread_id
    )

    if not mapping_deleted:
        return False

    # STEP 5: Verify complete deletion
    return (
        not _owns_thread(user["user_id"], thread_id)
        and thread_id not in _get_checkpoint_thread_ids()
    )


# ==========================================
# 12. THREAD MANAGER INFORMATION
# ==========================================

def get_thread_manager_info():

    return {
        "module": "Odhikar BD Thread Manager",

        "authentication_required": True,

        "ownership_verification": True,

        "features": [
            "authenticated_thread_creation",
            "authenticated_question_answering",
            "authenticated_history",
            "authenticated_thread_listing",
            "authenticated_thread_reset",
            "authenticated_thread_deletion"
        ],

        "storage": "SQLite + LangGraph Checkpointer"
    }
