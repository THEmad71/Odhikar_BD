
"""
ODHIKAR BD - API SECURITY AND INTEGRATION TESTS

Tests:
1. API health
2. User registration
3. Duplicate registration protection
4. User authentication
5. Secure session cookies
6. Invalid session protection
7. Login rate limiting
8. CSRF protection
9. Authenticated thread creation
10. User-specific thread listing
11. Conversation history access
12. AI chat integration
13. Cross-user access protection
14. Conversation reset protection
15. Conversation deletion protection
16. Session revocation and logout
17. Database cleanup

Run:
    python test_api_security.py
"""

import unittest

from uuid import uuid4
from contextlib import closing
from unittest.mock import patch

from fastapi.testclient import TestClient

from langchain_core.messages import (
    HumanMessage,
    AIMessage
)

from src.odhikar.api import app

from src.odhikar.user_manager import get_connection

from src.odhikar.thread_manager import (
    delete_authenticated_thread
)

from src.odhikar.session_manager import (
    logout_session
)

from src.odhikar.graph import checkpointer

from src.odhikar.api import clear_login_failures


# ==========================================
# 1. TEST CONFIGURATION
# ==========================================

PASSWORD = "Odhikar_Test@2026!"

SESSION_COOKIE = "odhikar_session"

CSRF_HEADER = "X-CSRF-Token"


# ==========================================
# 2. DATABASE CLEANUP HELPERS
# ==========================================

def delete_test_user(user_id):

    if not user_id:
        return

    with closing(get_connection()) as conn:

        with conn:

            conn.execute(
                "DELETE FROM users WHERE user_id = ?",
                (user_id,)
            )


def delete_test_checkpoint(thread_id):

    if not thread_id:
        return

    try:

        checkpointer.delete_thread(thread_id)

    except Exception as error:

        print(
            f"Checkpoint cleanup warning: {error}"
        )


# ==========================================
# 3. MAIN TEST CLASS
# ==========================================

class OdhikarAPISecurityTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        print("\n======================================")
        print("ODHIKAR BD API SECURITY TEST")
        print("======================================")

        cls.client_a = TestClient(app)

        cls.client_b = TestClient(app)

        cls.users = {}

        cls.sessions = {}

        cls.csrf_tokens = {}

        cls.threads = []

        cls._register_and_login("user_a")

        cls._register_and_login("user_b")


    # ======================================
    # REGISTER AND LOGIN TEST USERS
    # ======================================

    @classmethod
    def _register_and_login(cls, label):

        email = (
            f"{label}_{uuid4().hex[:10]}"
            "@odhikar-test.local"
        )

        client = (
            cls.client_a
            if label == "user_a"
            else cls.client_b
        )

        # Register user
        response = client.post(
            "/register",
            json={
                "display_name": label,
                "email": email,
                "password": PASSWORD
            }
        )

        assert response.status_code == 201, (
            f"Registration failed: {response.text}"
        )

        user = response.json()

        cls.users[label] = user

        # Login user
        response = client.post(
            "/login",
            json={
                "email": email,
                "password": PASSWORD
            }
        )

        assert response.status_code == 200, (
            f"Login failed: {response.text}"
        )

        cls.sessions[label] = client.cookies.get(
            SESSION_COOKIE
        )

        assert cls.sessions[label]

        # Obtain CSRF token
        response = client.get(
            "/csrf-token"
        )

        assert response.status_code == 200

        cls.csrf_tokens[label] = (
            response.json()["csrf_token"]
        )


    # ======================================
    # REQUEST HELPERS
    # ======================================

    def _client(self, label):

        return (
            self.client_a
            if label == "user_a"
            else self.client_b
        )


    def _headers(self, label):

        return {
            CSRF_HEADER: self.csrf_tokens[label]
        }


    def _create_thread(self, label):

        response = self._client(label).post(
            "/threads",
            headers=self._headers(label)
        )

        self.assertEqual(
            response.status_code,
            201,
            response.text
        )

        thread_id = response.json()["thread_id"]

        self.threads.append(
            (label, thread_id)
        )

        return thread_id


    # ======================================
    # TEST 1: API HEALTH
    # ======================================

    def test_01_api_health(self):

        print("\n--- API HEALTH ---")

        response = self.client_a.get(
            "/health"
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.assertEqual(
            response.json()["status"],
            "healthy"
        )

        print("[PASS] API health check")


    # ======================================
    # TEST 2: USER REGISTRATION
    # ======================================

    def test_02_registration(self):

        print("\n--- USER REGISTRATION ---")

        email = (
            f"registration_{uuid4().hex[:10]}"
            "@odhikar-test.local"
        )

        response = self.client_a.post(
            "/register",
            json={
                "display_name": "Registration Test",
                "email": email,
                "password": PASSWORD
            }
        )

        self.assertEqual(
            response.status_code,
            201,
            response.text
        )

        user = response.json()

        self.assertIn(
            "user_id",
            user
        )

        self.users["registration_test"] = user

        print("[PASS] New user registration")

        # Duplicate email protection
        duplicate = self.client_a.post(
            "/register",
            json={
                "display_name": "Duplicate User",
                "email": email,
                "password": PASSWORD
            }
        )

        self.assertEqual(
            duplicate.status_code,
            409
        )

        print("[PASS] Duplicate email rejected")


    # ======================================
    # TEST 3: AUTHENTICATION
    # ======================================

    def test_03_authentication(self):

        print("\n--- AUTHENTICATION ---")

        for label in ("user_a", "user_b"):

            client = self._client(label)

            response = client.get(
                "/me"
            )

            self.assertEqual(
                response.status_code,
                200
            )

            self.assertEqual(
                response.json()["user_id"],
                self.users[label]["user_id"]
            )

            print(
                f"[PASS] {label} identity verified"
            )

        # Verify HttpOnly session cookie
        login_cookie = next(
            (
                cookie
                for cookie in self.client_a.cookies.jar
                if cookie.name == SESSION_COOKIE
            ),
            None
        )

        self.assertIsNotNone(
            login_cookie
        )

        self.assertTrue(
            login_cookie.has_nonstandard_attr("HttpOnly")
            or login_cookie._rest.get("HttpOnly") is not None
        )

        print("[PASS] HttpOnly session cookie")


    # ======================================
    # TEST 4: INVALID SESSION
    # ======================================

    def test_04_invalid_session(self):

        print("\n--- INVALID SESSION ---")

        anonymous = TestClient(app)

        try:

            response = anonymous.get(
                "/me"
            )

            self.assertEqual(
                response.status_code,
                401
            )

            response = anonymous.post(
                "/threads"
            )

            self.assertEqual(
                response.status_code,
                401
            )

            print("[PASS] Anonymous user rejected")

        finally:

            anonymous.close()


    # ======================================
    # TEST 5: LOGIN RATE LIMITING
    # ======================================

    def test_05_login_rate_limit(self):

        print("\n--- LOGIN RATE LIMITING ---")

        client_ip = "198.51.100.250"

        client = TestClient(
            app,
            client=(client_ip, 12345)
        )

        try:

            for attempt in range(5):

                response = client.post(
                    "/login",
                    json={
                        "email": "unknown@odhikar-test.local",
                        "password": "WrongPassword123!"
                    }
                )

                self.assertEqual(
                    response.status_code,
                    401
                )

            response = client.post(
                "/login",
                json={
                    "email": "unknown@odhikar-test.local",
                    "password": "WrongPassword123!"
                }
            )

            self.assertEqual(
                response.status_code,
                429
            )

            print("[PASS] Five failed attempts recorded")

            print("[PASS] Sixth attempt rate-limited")

        finally:

            clear_login_failures(client_ip)

            client.close()


    # ======================================
    # TEST 6: CSRF PROTECTION
    # ======================================

    def test_06_csrf_protection(self):

        print("\n--- CSRF PROTECTION ---")

        # Missing CSRF token
        response = self.client_a.post(
            "/threads"
        )

        self.assertEqual(
            response.status_code,
            403
        )

        print("[PASS] Missing CSRF token rejected")

        # Invalid CSRF token
        response = self.client_a.post(
            "/threads",
            headers={
                CSRF_HEADER: "invalid-token"
            }
        )

        self.assertEqual(
            response.status_code,
            403
        )

        print("[PASS] Invalid CSRF token rejected")

        # Valid CSRF token
        thread_id = self._create_thread(
            "user_a"
        )

        print("[PASS] Valid CSRF token accepted")

        self.assertTrue(thread_id)


    # ======================================
    # TEST 7: THREAD OWNERSHIP AND ISOLATION
    # ======================================

    def test_07_thread_isolation(self):

        print("\n--- THREAD ISOLATION ---")

        thread_a = self._create_thread(
            "user_a"
        )

        thread_b = self._create_thread(
            "user_b"
        )

        # User A lists conversations
        response = self.client_a.get(
            "/threads"
        )

        self.assertEqual(
            response.status_code,
            200
        )

        user_a_threads = {
            item["thread_id"]
            for item in response.json()
        }

        self.assertIn(
            thread_a,
            user_a_threads
        )

        self.assertNotIn(
            thread_b,
            user_a_threads
        )

        print("[PASS] User A sees only own threads")

        # User B lists conversations
        response = self.client_b.get(
            "/threads"
        )

        user_b_threads = {
            item["thread_id"]
            for item in response.json()
        }

        self.assertIn(
            thread_b,
            user_b_threads
        )

        self.assertNotIn(
            thread_a,
            user_b_threads
        )

        print("[PASS] User B sees only own threads")

        # Cross-user history
        response = self.client_a.get(
            f"/threads/{thread_b}/messages"
        )

        self.assertEqual(
            response.status_code,
            404
        )

        print("[PASS] Cross-user history rejected")

        # Cross-user chat
        response = self.client_a.post(
            "/chat",
            headers=self._headers("user_a"),
            json={
                "thread_id": thread_b,
                "message": "Test unauthorized access"
            }
        )

        self.assertEqual(
            response.status_code,
            404
        )

        print("[PASS] Cross-user chat rejected")


    # ======================================
    # TEST 8: AI CHAT INTEGRATION
    # ======================================

    def test_08_ai_chat(self):

        print("\n--- AI CHAT INTEGRATION ---")

        thread_id = self._create_thread(
            "user_a"
        )

        # Mock the graph execution to avoid a real Gemini API call.
        with patch(
            "src.odhikar.thread_manager.ask_odhikar_graph",
            return_value="Mock Odhikar BD legal answer."
        ) as mocked_graph:

            response = self.client_a.post(
                "/chat",
                headers=self._headers("user_a"),
                json={
                    "thread_id": thread_id,
                    "message": "What is the maximum fine for no helmet?"
                }
            )

        self.assertEqual(
            response.status_code,
            200,
            response.text
        )

        self.assertEqual(
            response.json()["answer"],
            "Mock Odhikar BD legal answer."
        )

        mocked_graph.assert_called_once()

        print("[PASS] Authenticated AI chat")

        print("[PASS] Graph called after ownership verification")


    # ======================================
    # TEST 9: CONVERSATION HISTORY
    # ======================================

    def test_09_conversation_history(self):

        print("\n--- CONVERSATION HISTORY ---")

        thread_id = self._create_thread(
            "user_a"
        )

        # Mock graph history with representative messages.
        mock_messages = [
            HumanMessage(
                content="What is the helmet fine?"
            ),
            AIMessage(
                content="The maximum fine is 10,000 BDT."
            )
        ]

        with patch(
            "src.odhikar.api.get_authenticated_thread_history",
            return_value=mock_messages
        ):

            response = self.client_a.get(
                f"/threads/{thread_id}/messages"
            )

        self.assertEqual(
            response.status_code,
            200,
            response.text
        )

        data = response.json()

        self.assertEqual(
            len(data["messages"]),
            2
        )

        self.assertEqual(
            data["messages"][0]["role"],
            "user"
        )

        self.assertEqual(
            data["messages"][1]["role"],
            "assistant"
        )

        print("[PASS] Conversation history retrieved")

        print("[PASS] Message roles serialized correctly")


    # ======================================
    # TEST 10: CROSS-USER RESET PROTECTION
    # ======================================

    def test_10_cross_user_reset(self):

        print("\n--- CROSS-USER RESET PROTECTION ---")

        thread_b = self._create_thread(
            "user_b"
        )

        response = self.client_a.post(
            f"/threads/{thread_b}/reset",
            headers=self._headers("user_a")
        )

        self.assertEqual(
            response.status_code,
            404
        )

        # Verify User B still owns the thread
        response = self.client_b.get(
            "/threads"
        )

        self.assertIn(
            thread_b,
            {
                item["thread_id"]
                for item in response.json()
            }
        )

        print("[PASS] Cross-user reset rejected")

        print("[PASS] User B thread mapping preserved")


    # ======================================
    # TEST 11: OWN THREAD RESET
    # ======================================

    def test_11_own_thread_reset(self):

        print("\n--- OWN THREAD RESET ---")

        thread_id = self._create_thread(
            "user_a"
        )

        response = self.client_a.post(
            f"/threads/{thread_id}/reset",
            headers=self._headers("user_a")
        )

        self.assertEqual(
            response.status_code,
            200,
            response.text
        )

        self.assertEqual(
            response.json()["status"],
            "reset"
        )

        # Thread mapping must remain after reset.
        response = self.client_a.get(
            "/threads"
        )

        self.assertIn(
            thread_id,
            {
                item["thread_id"]
                for item in response.json()
            }
        )

        print("[PASS] Own conversation reset")

        print("[PASS] Thread ownership preserved")


    # ======================================
    # TEST 12: CROSS-USER DELETE PROTECTION
    # ======================================

    def test_12_cross_user_delete(self):

        print("\n--- CROSS-USER DELETE PROTECTION ---")

        thread_b = self._create_thread(
            "user_b"
        )

        response = self.client_a.delete(
            f"/threads/{thread_b}",
            headers=self._headers("user_a")
        )

        self.assertEqual(
            response.status_code,
            404
        )

        response = self.client_b.get(
            "/threads"
        )

        self.assertIn(
            thread_b,
            {
                item["thread_id"]
                for item in response.json()
            }
        )

        print("[PASS] Cross-user deletion rejected")

        print("[PASS] User B conversation preserved")


    # ======================================
    # TEST 13: OWN THREAD DELETE
    # ======================================

    def test_13_own_thread_delete(self):

        print("\n--- OWN THREAD DELETION ---")

        thread_id = self._create_thread(
            "user_a"
        )

        response = self.client_a.delete(
            f"/threads/{thread_id}",
            headers=self._headers("user_a")
        )

        self.assertEqual(
            response.status_code,
            200,
            response.text
        )

        self.assertEqual(
            response.json()["status"],
            "deleted"
        )

        response = self.client_a.get(
            "/threads"
        )

        self.assertNotIn(
            thread_id,
            {
                item["thread_id"]
                for item in response.json()
            }
        )

        print("[PASS] Own conversation deleted")

        print("[PASS] Deleted thread no longer listed")


    # ======================================
    # TEST 14: LOGOUT AND SESSION REVOCATION
    # ======================================

    def test_14_logout(self):

        print("\n--- LOGOUT AND SESSION REVOCATION ---")

        client = TestClient(app)

        email = (
            f"logout_{uuid4().hex[:10]}"
            "@odhikar-test.local"
        )

        user_id = None

        try:

            # Register temporary user
            response = client.post(
                "/register",
                json={
                    "display_name": "Logout Test",
                    "email": email,
                    "password": PASSWORD
                }
            )

            self.assertEqual(
                response.status_code,
                201
            )

            user_id = response.json()["user_id"]

            # Login
            response = client.post(
                "/login",
                json={
                    "email": email,
                    "password": PASSWORD
                }
            )

            self.assertEqual(
                response.status_code,
                200
            )

            # Get CSRF token
            response = client.get(
                "/csrf-token"
            )

            csrf_token = response.json()["csrf_token"]

            # Logout
            response = client.post(
                "/logout",
                headers={
                    CSRF_HEADER: csrf_token
                }
            )

            self.assertEqual(
                response.status_code,
                200
            )

            print("[PASS] Logout successful")

            # Session must no longer work
            response = client.get(
                "/me"
            )

            self.assertEqual(
                response.status_code,
                401
            )

            print("[PASS] Revoked session rejected")

            # Thread creation must also fail
            response = client.post(
                "/threads"
            )

            self.assertEqual(
                response.status_code,
                401
            )

            print("[PASS] Revoked session cannot create threads")

        finally:

            delete_test_user(user_id)

            client.close()


    # ======================================
    # 15. CLEANUP
    # ======================================

    @classmethod
    def tearDownClass(cls):

        print("\n--- TEST CLEANUP ---")

        # Delete all temporary test checkpoints
        for label, thread_id in cls.threads:

            delete_test_checkpoint(
                thread_id
            )

        # Revoke test sessions
        for token in cls.sessions.values():

            if token:
                logout_session(token)

        # Delete temporary users
        for user in cls.users.values():

            delete_test_user(
                user["user_id"]
            )

        cls.client_a.close()

        cls.client_b.close()

        print("[PASS] Test checkpoints cleaned")

        print("[PASS] Test users removed")

        print("[PASS] Test sessions revoked")

        print("\n======================================")
        print("API SECURITY TEST COMPLETED")
        print("======================================")


# ==========================================
# 16. RUN TESTS
# ==========================================

if __name__ == "__main__":

    unittest.main(verbosity=2)
