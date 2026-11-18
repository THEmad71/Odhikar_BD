
from uuid import uuid4

from src.odhikar.auth_manager import register_user

from src.odhikar.session_manager import (
    login_with_session,
    validate_session,
    logout_session
)


# ==========================================
# 1. REGISTER TEST USER
# ==========================================

print("\n--- CREATE TEST USER ---")

email = f"session_{uuid4().hex[:8]}@example.com"

password = "OdhikarSession123!"

user = register_user(
    "Session Test User",
    email,
    password
)

print("User Created:", user["user_id"])


# ==========================================
# 2. LOGIN AND CREATE SESSION
# ==========================================

print("\n--- LOGIN WITH SESSION ---")

login = login_with_session(
    email,
    password
)

assert login is not None

token = login["session_token"]

print("Login Successful!")
print("Session Token Generated:", bool(token))


# ==========================================
# 3. VALIDATE SESSION
# ==========================================

print("\n--- SESSION VALIDATION ---")

session_user = validate_session(token)

assert session_user is not None

print("Session Valid:", True)
print("Authenticated User:", session_user["display_name"])


# ==========================================
# 4. INVALID TOKEN TEST
# ==========================================

print("\n--- INVALID SESSION TEST ---")

invalid_session = validate_session(
    "invalid_session_token"
)

assert invalid_session is None

print("Invalid Session Rejected!")


# ==========================================
# 5. LOGOUT
# ==========================================

print("\n--- LOGOUT TEST ---")

logout_result = logout_session(token)

assert logout_result is True

print("Logout Successful:", logout_result)


# ==========================================
# 6. VALIDATE AFTER LOGOUT
# ==========================================

print("\n--- POST LOGOUT VALIDATION ---")

session_after_logout = validate_session(token)

assert session_after_logout is None

print("Session Revoked Successfully!")


print("\n--- SESSION MANAGEMENT TEST COMPLETED ---")
