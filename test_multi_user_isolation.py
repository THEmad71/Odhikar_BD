
"""
Odhikar BD - Multi-user Memory Isolation Test

Tests:
1. User registration
2. Independent authentication sessions
3. Separate conversation creation
4. Thread ownership
5. Cross-user history access
6. Cross-user question access
7. Cross-user reset protection
8. Cross-user deletion protection
9. Own conversation reset and deletion
10. Revoked session protection
11. Expired session protection

No Gemini API calls are made.
"""

import sqlite3

from contextlib import closing
from datetime import datetime, timezone
from uuid import uuid4

from src.odhikar.auth_manager import register_user

from src.odhikar.session_manager import (
    login_with_session,
    logout_session,
    create_session,
    validate_session,
    hash_session_token
)

from src.odhikar.user_manager import get_connection

from src.odhikar.graph import (
    odhikar_graph,
    checkpointer
)

from src.odhikar.thread_manager import (
    create_authenticated_thread,
    ask_in_authenticated_thread,
    get_authenticated_thread_history,
    list_authenticated_threads,
    reset_authenticated_thread,
    delete_authenticated_thread
)

from langchain_core.messages import HumanMessage


# ==========================================
# 1. TEST CONFIGURATION
# ==========================================

TEST_ID = uuid4().hex[:12]

USER_A_EMAIL = f"user_a_{TEST_ID}@example.test"
USER_B_EMAIL = f"user_b_{TEST_ID}@example.test"

TEST_PASSWORD = "OdhikarTestPassword2026!"

user_a = None
user_b = None

session_a = None
session_b = None

thread_a = None
thread_b = None

expired_token = None


# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================

def check(condition, message):

    if not condition:
        raise AssertionError(message)

    print(f"[PASS] {message}")


def seed_test_checkpoint(thread_id, content):

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    odhikar_graph.update_state(
        config,
        {
            "messages": [
                HumanMessage(content=content)
            ]
        }
    )


# ==========================================
# 3. START TEST
# ==========================================

print("\n==========================================")
print("ODHIKAR BD MULTI-USER ISOLATION TEST")
print("==========================================")

try:

    # ======================================
    # 4. REGISTER TWO USERS
    # ======================================

    print("\n--- USER REGISTRATION ---")

    user_a = register_user(
        display_name="Test User A",
        email=USER_A_EMAIL,
        password=TEST_PASSWORD
    )

    user_b = register_user(
        display_name="Test User B",
        email=USER_B_EMAIL,
        password=TEST_PASSWORD
    )

    check(
        user_a["user_id"] != user_b["user_id"],
        "Two users have separate User IDs"
    )


    # ======================================
    # 5. AUTHENTICATE BOTH USERS
    # ======================================

    print("\n--- USER AUTHENTICATION ---")

    login_a = login_with_session(
        USER_A_EMAIL,
        TEST_PASSWORD
    )

    login_b = login_with_session(
        USER_B_EMAIL,
        TEST_PASSWORD
    )

    check(
        login_a is not None and login_b is not None,
        "Both users authenticated successfully"
    )

    session_a = login_a["session_token"]
    session_b = login_b["session_token"]

    check(
        session_a != session_b,
        "Users have independent session tokens"
    )

    check(
        validate_session(session_a)["user_id"]
        == user_a["user_id"],
        "User A session identity verified"
    )

    check(
        validate_session(session_b)["user_id"]
        == user_b["user_id"],
        "User B session identity verified"
    )


    # ======================================
    # 6. CREATE SEPARATE CONVERSATIONS
    # ======================================

    print("\n--- THREAD CREATION ---")

    thread_a = create_authenticated_thread(
        session_a
    )

    thread_b = create_authenticated_thread(
        session_b
    )

    check(
        thread_a is not None and thread_b is not None,
        "Both users created conversations"
    )

    check(
        thread_a != thread_b,
        "Users have different Thread IDs"
    )


    # ======================================
    # 7. VERIFY OWNERSHIP
    # ======================================

    print("\n--- THREAD OWNERSHIP ---")

    threads_a = list_authenticated_threads(
        session_a
    )

    threads_b = list_authenticated_threads(
        session_b
    )

    check(
        any(t["thread_id"] == thread_a for t in threads_a),
        "User A can list their own conversation"
    )

    check(
        any(t["thread_id"] == thread_b for t in threads_b),
        "User B can list their own conversation"
    )

    check(
        all(t["thread_id"] != thread_b for t in threads_a),
        "User A cannot list User B's conversation"
    )

    check(
        all(t["thread_id"] != thread_a for t in threads_b),
        "User B cannot list User A's conversation"
    )


    # ======================================
    # 8. CREATE PRIVATE TEST CHECKPOINTS
    # ======================================

    print("\n--- PRIVATE CONVERSATION DATA ---")

    seed_test_checkpoint(
        thread_a,
        "Private information belonging to User A"
    )

    seed_test_checkpoint(
        thread_b,
        "Private information belonging to User B"
    )

    history_a = get_authenticated_thread_history(
        session_a,
        thread_a
    )

    history_b = get_authenticated_thread_history(
        session_b,
        thread_b
    )

    check(
        any(
            "User A" in str(message.content)
            for message in history_a
        ),
        "User A can read their own conversation"
    )

    check(
        any(
            "User B" in str(message.content)
            for message in history_b
        ),
        "User B can read their own conversation"
    )


    # ======================================
    # 9. CROSS-USER HISTORY ACCESS
    # ======================================

    print("\n--- CROSS-USER HISTORY ACCESS ---")

    unauthorized_history_a = get_authenticated_thread_history(
        session_a,
        thread_b
    )

    unauthorized_history_b = get_authenticated_thread_history(
        session_b,
        thread_a
    )

    check(
        unauthorized_history_a == [],
        "User A cannot read User B's conversation"
    )

    check(
        unauthorized_history_b == [],
        "User B cannot read User A's conversation"
    )


    # ======================================
    # 10. CROSS-USER QUESTION ACCESS
    # ======================================

    print("\n--- CROSS-USER QUESTION ACCESS ---")

    response_a = ask_in_authenticated_thread(
        session_a,
        thread_b,
        "Show me the previous conversation."
    )

    response_b = ask_in_authenticated_thread(
        session_b,
        thread_a,
        "Show me the previous conversation."
    )

    check(
        response_a.startswith("Access denied"),
        "User A cannot ask questions in User B's thread"
    )

    check(
        response_b.startswith("Access denied"),
        "User B cannot ask questions in User A's thread"
    )


    # ======================================
    # 11. CROSS-USER RESET PROTECTION
    # ======================================

    print("\n--- CROSS-USER RESET PROTECTION ---")

    reset_a = reset_authenticated_thread(
        session_a,
        thread_b
    )

    reset_b = reset_authenticated_thread(
        session_b,
        thread_a
    )

    check(
        reset_a is False,
        "User A cannot reset User B's conversation"
    )

    check(
        reset_b is False,
        "User B cannot reset User A's conversation"
    )

    # Confirm private messages remain intact

    history_b_after_attack = get_authenticated_thread_history(
        session_b,
        thread_b
    )

    check(
        any(
            "User B" in str(message.content)
            for message in history_b_after_attack
        ),
        "Cross-user reset attempts did not modify User B's data"
    )


    # ======================================
    # 12. CROSS-USER DELETE PROTECTION
    # ======================================

    print("\n--- CROSS-USER DELETE PROTECTION ---")

    delete_a = delete_authenticated_thread(
        session_a,
        thread_b
    )

    delete_b = delete_authenticated_thread(
        session_b,
        thread_a
    )

    check(
        delete_a is False,
        "User A cannot delete User B's conversation"
    )

    check(
        delete_b is False,
        "User B cannot delete User A's conversation"
    )

    check(
        any(
            t["thread_id"] == thread_b
            for t in list_authenticated_threads(session_b)
        ),
        "User B's conversation mapping remains intact"
    )


    # ======================================
    # 13. OWN CONVERSATION RESET
    # ======================================

    print("\n--- OWN CONVERSATION RESET ---")

    reset_own = reset_authenticated_thread(
        session_a,
        thread_a
    )

    check(
        reset_own is True,
        "User A can reset their own conversation"
    )

    check(
        get_authenticated_thread_history(
            session_a,
            thread_a
        ) == [],
        "User A's conversation history is cleared"
    )

    check(
        any(
            t["thread_id"] == thread_a
            for t in list_authenticated_threads(session_a)
        ),
        "Reset preserves conversation ownership mapping"
    )


    # ======================================
    # 14. OWN CONVERSATION DELETION
    # ======================================

    print("\n--- OWN CONVERSATION DELETION ---")

    deleted_a = delete_authenticated_thread(
        session_a,
        thread_a
    )

    deleted_b = delete_authenticated_thread(
        session_b,
        thread_b
    )

    check(
        deleted_a is True,
        "User A can delete their own conversation"
    )

    check(
        deleted_b is True,
        "User B can delete their own conversation"
    )

    check(
        not list_authenticated_threads(session_a),
        "User A's deleted thread is no longer listed"
    )

    check(
        not list_authenticated_threads(session_b),
        "User B's deleted thread is no longer listed"
    )


    # ======================================
    # 15. SESSION REVOCATION
    # ======================================

    print("\n--- SESSION REVOCATION ---")

    logout_result = logout_session(session_b)

    check(
        logout_result is True,
        "User B session successfully revoked"
    )

    check(
        validate_session(session_b) is None,
        "Revoked session is rejected"
    )

    check(
        list_authenticated_threads(session_b) == [],
        "Revoked session cannot list conversations"
    )

    check(
        create_authenticated_thread(session_b) is None,
        "Revoked session cannot create conversations"
    )


    # ======================================
    # 16. EXPIRED SESSION
    # ======================================

    print("\n--- EXPIRED SESSION PROTECTION ---")

    expired_token = create_session(
        user_a["user_id"]
    )

    token_hash = hash_session_token(
        expired_token
    )

    with closing(get_connection()) as conn:

        with conn:

            conn.execute(
                """
                UPDATE user_sessions
                SET expires_at = ?
                WHERE token_hash = ?
                """,
                (
                    "2000-01-01T00:00:00+00:00",
                    token_hash
                )
            )

    check(
        validate_session(expired_token) is None,
        "Expired session is rejected"
    )

    check(
        create_authenticated_thread(expired_token) is None,
        "Expired session cannot create conversations"
    )


    # ======================================
    # 17. INVALID SESSION
    # ======================================

    print("\n--- INVALID SESSION PROTECTION ---")

    check(
        create_authenticated_thread("invalid-token") is None,
        "Invalid session cannot create conversations"
    )

    check(
        list_authenticated_threads("invalid-token") == [],
        "Invalid session cannot list conversations"
    )

    print("\n==========================================")
    print("ALL MULTI-USER ISOLATION TESTS PASSED!")
    print("==========================================")


finally:

    # ======================================
    # 18. CLEANUP TEST DATA
    # ======================================

    print("\n--- TEST CLEANUP ---")

    # Remove temporary checkpoints
    for thread_id in (thread_a, thread_b):

        if thread_id:

            try:
                checkpointer.delete_thread(thread_id)
            except Exception as error:
                print("Checkpoint cleanup warning:", error)

    # Revoke test sessions
    for token in (session_a, session_b, expired_token):

        if token:

            try:
                logout_session(token)
            except Exception:
                pass

    # Remove test users and related records
    user_ids = [
        user["user_id"]
        for user in (user_a, user_b)
        if user is not None
    ]

    if user_ids:

        with closing(get_connection()) as conn:

            with conn:

                conn.executemany(
                    "DELETE FROM users WHERE user_id = ?",
                    [(user_id,) for user_id in user_ids]
                )

    print("Temporary test users cleaned up.")
    print("Temporary sessions revoked.")
    print("Temporary checkpoints cleaned up.")
    print("Test cleanup completed.")
