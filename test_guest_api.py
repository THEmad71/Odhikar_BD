
"""
Odhikar BD - Guest API Integration Tests

Tests:
1. Guest session creation and CSRF protection
2. Five free guest messages and HTTP 429
3. Guest conversation ownership isolation
4. Guest session reuse
5. Missing session access rejection
6. Unauthorized request does not consume quota

Real Gemini API calls are mocked.
"""

import hashlib
import hmac
import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.odhikar.guest_routes import (
    build_guest_router,
)

from src.odhikar.usage_limits import (
    UsageStore,
)


# ==========================================
# 1. TEST CSRF HELPERS
# ==========================================

def make_csrf(token: str) -> str:
    nonce = "test-nonce"

    signature = hmac.new(
        token.encode("utf-8"),
        nonce.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"{nonce}.{signature}"


def verify_csrf(
    token: str,
    csrf_token: str,
) -> bool:
    if not isinstance(csrf_token, str):
        return False

    try:
        nonce, signature = csrf_token.split(
            ".",
            1,
        )

        expected = hmac.new(
            token.encode("utf-8"),
            nonce.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return (
            nonce == "test-nonce"
            and hmac.compare_digest(
                signature,
                expected,
            )
        )

    except (ValueError, TypeError):
        return False


# ==========================================
# 2. GUEST API TEST CLASS
# ==========================================

class GuestApiTests(unittest.TestCase):

    def setUp(self):
        # Temporary isolated SQLite database.
        self.temp_dir = tempfile.TemporaryDirectory()

        self.db_path = (
            Path(self.temp_dir.name)
            / "test_guest_usage.sqlite"
        )

        self.store = UsageStore(
            self.db_path
        )

        self.app = FastAPI()

        self.app.include_router(
            build_guest_router(
                store=self.store,
                validate_origin=lambda request: None,
                generate_csrf=make_csrf,
                validate_csrf=verify_csrf,
                serialize_history=lambda messages: [],
                cookie_secure=False,
                cookie_samesite="lax",
            )
        )

        self.client = TestClient(
            self.app
        )

    def tearDown(self):
        self.client.close()
        self.temp_dir.cleanup()

    # ======================================
    # HELPER: START GUEST SESSION
    # ======================================

    def start_guest(self, client=None):
        if client is None:
            client = self.client

        response = client.post(
            "/guest/session"
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.json()["mode"],
            "guest",
        )

        csrf_response = client.get(
            "/guest/csrf-token"
        )

        self.assertEqual(
            csrf_response.status_code,
            200,
        )

        csrf_token = csrf_response.json()[
            "csrf_token"
        ]

        return {
            "X-CSRF-Token": csrf_token,
        }

    # ======================================
    # TEST 1: SESSION AND CSRF
    # ======================================

    def test_guest_session_and_csrf(self):
        headers = self.start_guest()

        # Valid request succeeds.
        valid_response = self.client.post(
            "/guest/threads",
            headers=headers,
        )

        self.assertEqual(
            valid_response.status_code,
            201,
        )

        self.assertIn(
            "thread_id",
            valid_response.json(),
        )

        # Missing CSRF header must fail.
        missing_csrf = self.client.post(
            "/guest/threads"
        )

        self.assertEqual(
            missing_csrf.status_code,
            403,
        )

        # Incorrect CSRF token must fail.
        invalid_csrf = self.client.post(
            "/guest/threads",
            headers={
                "X-CSRF-Token": "invalid-token",
            },
        )

        self.assertEqual(
            invalid_csrf.status_code,
            403,
        )

    # ======================================
    # TEST 2: FIVE MESSAGES THEN 429
    # ======================================

    @patch(
        "src.odhikar.guest_routes.ask_odhikar_graph",
        return_value="Mock legal answer",
    )
    def test_five_messages_then_429(
        self,
        mock_ai,
    ):
        headers = self.start_guest()

        created = self.client.post(
            "/guest/threads",
            headers=headers,
        )

        self.assertEqual(
            created.status_code,
            201,
        )

        thread_id = created.json()[
            "thread_id"
        ]

        payload = {
            "thread_id": thread_id,
            "message": (
                "What is the motorcycle helmet rule?"
            ),
        }

        # Five requests should be accepted.
        for index in range(5):
            response = self.client.post(
                "/guest/chat",
                headers=headers,
                json=payload,
            )

            self.assertEqual(
                response.status_code,
                200,
            )

            self.assertEqual(
                response.json()["answer"],
                "Mock legal answer",
            )

            self.assertEqual(
                response.json()["usage"]["remaining"],
                4 - index,
            )

        # Sixth request must be blocked.
        blocked = self.client.post(
            "/guest/chat",
            headers=headers,
            json=payload,
        )

        self.assertEqual(
            blocked.status_code,
            429,
        )

        self.assertEqual(
            blocked.json()["detail"]["code"],
            "GUEST_LIMIT_REACHED",
        )

        self.assertEqual(
            blocked.json()["detail"]["remaining"],
            0,
        )

        # Gemini/LangGraph must only be called 5 times.
        self.assertEqual(
            mock_ai.call_count,
            5,
        )

    # ======================================
    # TEST 3: THREAD OWNERSHIP
    # ======================================

    @patch(
        "src.odhikar.guest_routes.ask_odhikar_graph",
        return_value="Mock legal answer",
    )
    def test_guest_cannot_access_other_thread(
        self,
        mock_ai,
    ):
        headers_a = self.start_guest(
            self.client
        )

        created = self.client.post(
            "/guest/threads",
            headers=headers_a,
        )

        thread_a = created.json()[
            "thread_id"
        ]

        # Independent browser session.
        with TestClient(self.app) as client_b:
            headers_b = self.start_guest(
                client_b
            )

            # Guest B cannot read Guest A's chat.
            history = client_b.get(
                f"/guest/threads/{thread_a}/messages"
            )

            self.assertEqual(
                history.status_code,
                404,
            )

            # Guest B cannot send into A's chat.
            forbidden = client_b.post(
                "/guest/chat",
                headers=headers_b,
                json={
                    "thread_id": thread_a,
                    "message": "Read guest A's chat",
                },
            )

            self.assertEqual(
                forbidden.status_code,
                404,
            )

        self.assertEqual(
            mock_ai.call_count,
            0,
        )

    # ======================================
    # TEST 4: REUSE EXISTING GUEST SESSION
    # ======================================

    def test_guest_session_reuse(self):
        self.start_guest()

        original_cookie = self.client.cookies.get(
            "odhikar_guest"
        )

        self.assertIsNotNone(
            original_cookie
        )

        response = self.client.post(
            "/guest/session"
        )

        self.assertEqual(
            response.status_code,
            201,
        )

        self.assertEqual(
            response.json()["message"],
            "Guest session already active.",
        )

        current_cookie = self.client.cookies.get(
            "odhikar_guest"
        )

        self.assertEqual(
            original_cookie,
            current_cookie,
        )

    # ======================================
    # TEST 5: MISSING GUEST SESSION
    # ======================================

    def test_missing_guest_session_rejected(self):
        with TestClient(self.app) as new_client:

            response = new_client.get(
                "/guest/threads"
            )

            self.assertEqual(
                response.status_code,
                401,
            )

            csrf_response = new_client.get(
                "/guest/csrf-token"
            )

            self.assertEqual(
                csrf_response.status_code,
                401,
            )

    # ======================================
    # TEST 6: INVALID OWNERSHIP DOES
    # NOT CONSUME THE GUEST QUOTA
    # ======================================

    @patch(
        "src.odhikar.guest_routes.ask_odhikar_graph",
        return_value="Mock legal answer",
    )
    def test_forbidden_chat_does_not_consume_quota(
        self,
        mock_ai,
    ):
        headers = self.start_guest()

        invalid_request = self.client.post(
            "/guest/chat",
            headers=headers,
            json={
                "thread_id": (
                    "guest:nonexistent-thread"
                ),
                "message": "Hello",
            },
        )

        self.assertEqual(
            invalid_request.status_code,
            404,
        )

        token = self.client.cookies.get(
            "odhikar_guest"
        )

        principal = self.store.guest_principal(
            token
        )

        usage = self.store.status(
            "guest",
            principal,
        )

        self.assertEqual(
            usage.used,
            0,
        )

        self.assertEqual(
            usage.remaining,
            5,
        )

        self.assertEqual(
            mock_ai.call_count,
            0,
        )


if __name__ == "__main__":
    unittest.main()
