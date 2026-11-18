
from uuid import uuid4

from src.odhikar.auth_manager import (
    register_user,
    login_user
)


# ==========================================
# 1. CREATE TEST ACCOUNT
# ==========================================

print("\n--- USER REGISTRATION TEST ---")

email = f"test_{uuid4().hex[:8]}@example.com"

password = "OdhikarSecure123!"

user = register_user(
    display_name="Test User",
    email=email,
    password=password
)

print("Registration successful!")
print("User ID:", user["user_id"])
print("Email:", user["email"])


# ==========================================
# 2. LOGIN WITH CORRECT PASSWORD
# ==========================================

print("\n--- CORRECT LOGIN TEST ---")

login_result = login_user(
    email,
    password
)

if login_result:

    print("Login successful!")
    print("Welcome:", login_result["display_name"])

else:

    print("Login failed!")


# ==========================================
# 3. LOGIN WITH WRONG PASSWORD
# ==========================================

print("\n--- WRONG PASSWORD TEST ---")

wrong_login = login_user(
    email,
    "WrongPassword123!"
)

if wrong_login is None:

    print("Login rejected successfully!")

else:

    print("Security test failed!")


# ==========================================
# 4. DUPLICATE EMAIL TEST
# ==========================================

print("\n--- DUPLICATE EMAIL TEST ---")

try:

    register_user(
        display_name="Another User",
        email=email,
        password="AnotherSecure123!"
    )

    print("Duplicate registration unexpectedly succeeded.")

except ValueError as error:

    print("Duplicate registration rejected!")
    print("Reason:", error)


# ==========================================
# 5. FINAL RESULT
# ==========================================

print("\n--- AUTHENTICATION TEST COMPLETED ---")
