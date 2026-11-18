
from uuid import uuid4

from src.odhikar.auth_manager import register_user

from src.odhikar.session_manager import (
    login_with_session,
    logout_session
)

from src.odhikar.thread_manager import (
    create_authenticated_thread,
    ask_in_authenticated_thread
)


# ==========================================
# 1. CREATE TWO USERS
# ==========================================

print("\n--- CREATE USERS ---")

email_a = f"user_a_{uuid4().hex[:8]}@example.com"
email_b = f"user_b_{uuid4().hex[:8]}@example.com"

user_a = register_user(
    "User A",
    email_a,
    "SecurePasswordA123!"
)

user_b = register_user(
    "User B",
    email_b,
    "SecurePasswordB123!"
)

print("Two users created successfully.")


# ==========================================
# 2. LOGIN BOTH USERS
# ==========================================

print("\n--- LOGIN TEST ---")

login_a = login_with_session(
    email_a,
    "SecurePasswordA123!"
)

login_b = login_with_session(
    email_b,
    "SecurePasswordB123!"
)

assert login_a is not None
assert login_b is not None

token_a = login_a["session_token"]
token_b = login_b["session_token"]

print("Both users logged in successfully.")


# ==========================================
# 3. CREATE USER A CONVERSATION
# ==========================================

print("\n--- CREATE CONVERSATION ---")

thread_a = create_authenticated_thread(token_a)

assert thread_a is not None

print("User A Thread:", thread_a)


# ==========================================
# 4. USER A ACCESS OWN THREAD
# ==========================================

print("\n--- AUTHORIZED ACCESS TEST ---")

answer = ask_in_authenticated_thread(
    token_a,
    thread_a,
    "What is the maximum fine for riding a motorcycle without wearing a helmet?"
)

print("Answer:", answer)


# ==========================================
# 5. USER B ACCESS USER A THREAD
# ==========================================

print("\n--- UNAUTHORIZED ACCESS TEST ---")

unauthorized = ask_in_authenticated_thread(
    token_b,
    thread_a,
    "What was the previous conversation about?"
)

assert unauthorized.startswith("Access denied")

print(unauthorized)


# ==========================================
# 6. INVALID SESSION TEST
# ==========================================

print("\n--- INVALID SESSION TEST ---")

invalid = ask_in_authenticated_thread(
    "invalid_token",
    thread_a,
    "Tell me the previous answer."
)

assert invalid.startswith("Authentication required")

print(invalid)


# ==========================================
# 7. LOGOUT TEST
# ==========================================

print("\n--- LOGOUT TEST ---")

logout_result = logout_session(token_a)

assert logout_result is True

print("User A logged out:", logout_result)


# ==========================================
# 8. ACCESS AFTER LOGOUT
# ==========================================

print("\n--- POST LOGOUT ACCESS TEST ---")

after_logout = ask_in_authenticated_thread(
    token_a,
    thread_a,
    "What is the previous answer?"
)

assert after_logout.startswith("Authentication required")

print(after_logout)


print("\n--- AUTHENTICATED ACCESS TEST COMPLETED ---")
