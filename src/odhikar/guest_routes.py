
"""
Odhikar BD - Secure Guest API Routes

Features:
- Anonymous guest sessions
- Guest CSRF protection
- Guest conversation ownership
- Guest conversation history
- LangGraph / Gemini integration
- Five messages per rolling 24 hours
- Proper SQLite connection cleanup

Compatible with the existing UsageStore
and FastAPI application.
"""

import hmac
import secrets
import sqlite3
import time

from contextlib import closing
from datetime import datetime, timezone
from typing import Callable

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from src.odhikar.graph import (
    ask_odhikar_graph,
    get_conversation_history,
)

from src.odhikar.usage_limits import (
    UsageStore,
    GUEST_COOKIE,
    DAY_SECONDS,
    GUEST_LIMIT,
)


# ==========================================
# 1. REQUEST MODELS
# ==========================================

class GuestChatRequest(BaseModel):

    model_config = ConfigDict(
        extra="forbid"
    )

    thread_id: str = Field(
        min_length=1,
        max_length=256,
    )

    message: str = Field(
        min_length=1,
        max_length=5000,
    )


# ==========================================
# 2. BUILD GUEST ROUTER
# ==========================================

def build_guest_router(
    store: UsageStore,
    validate_origin: Callable,
    generate_csrf: Callable,
    validate_csrf: Callable,
    serialize_history: Callable,
    *,
    cookie_secure: bool,
    cookie_samesite: str = "lax",
):

    router = APIRouter(
        prefix="/guest",
        tags=["Guest Access"],
    )

    guest_csrf_cookie = "odhikar_guest_csrf"

    # ======================================
    # 3. INITIALIZE GUEST THREAD TABLE
    # ======================================

    def initialize_guest_tables():

        with closing(
            sqlite3.connect(store.db_path)
        ) as conn:

            with conn:

                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS
                    guest_threads (

                        thread_id TEXT PRIMARY KEY,

                        guest_hash TEXT NOT NULL,

                        created_at INTEGER NOT NULL,

                        FOREIGN KEY (guest_hash)
                        REFERENCES guest_sessions(token_hash)
                    )
                    """
                )

                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_guest_threads_owner

                    ON guest_threads (
                        guest_hash
                    )
                    """
                )

    initialize_guest_tables()

    # ======================================
    # 4. VERIFY GUEST SESSION
    # ======================================

    def guest_context(
        request: Request,
    ) -> dict:

        token = request.cookies.get(
            GUEST_COOKIE
        )

        guest_hash = store.guest_principal(
            token
        )

        if guest_hash is None:

            raise HTTPException(
                status_code=401,
                detail=(
                    "Guest session expired or missing. "
                    "Start a new guest session."
                ),
            )

        return {
            "token": token,
            "guest_hash": guest_hash,
        }

    # ======================================
    # 5. GUEST CSRF VALIDATION
    # ======================================

    def guest_csrf(
        request: Request,
        context: dict = Depends(
            guest_context
        ),
    ) -> dict:

        validate_origin(request)

        csrf_cookie = request.cookies.get(
            guest_csrf_cookie
        )

        csrf_header = request.headers.get(
            "X-CSRF-Token"
        )

        if (
            not csrf_cookie
            or not csrf_header
        ):

            raise HTTPException(
                status_code=403,
                detail="Guest CSRF validation failed.",
            )

        if not hmac.compare_digest(
            csrf_cookie,
            csrf_header,
        ):

            raise HTTPException(
                status_code=403,
                detail="Guest CSRF validation failed.",
            )

        if not validate_csrf(
            context["token"],
            csrf_header,
        ):

            raise HTTPException(
                status_code=403,
                detail="Invalid guest CSRF token.",
            )

        return context

    # ======================================
    # 6. CHECK THREAD OWNERSHIP
    # ======================================

    def owns_thread(
        guest_hash: str,
        thread_id: str,
    ) -> bool:

        # Explicitly close SQLite connection.
        with closing(
            sqlite3.connect(store.db_path)
        ) as conn:

            row = conn.execute(
                """
                SELECT 1
                FROM guest_threads

                WHERE guest_hash = ?
                AND thread_id = ?

                LIMIT 1
                """,
                (
                    guest_hash,
                    thread_id,
                ),
            ).fetchone()

        return row is not None

    # ======================================
    # 7. REQUIRE THREAD OWNERSHIP
    # ======================================

    def require_owned_thread(
        guest_hash: str,
        thread_id: str,
    ):

        if not owns_thread(
            guest_hash,
            thread_id,
        ):

            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

    # ======================================
    # 8. CREATE OR REUSE GUEST SESSION
    # ======================================

    @router.post(
        "/session",
        status_code=201,
    )
    def create_guest_session(
        request: Request,
        response: Response,
    ):

        validate_origin(request)

        existing_token = request.cookies.get(
            GUEST_COOKIE
        )

        principal = store.guest_principal(
            existing_token
        )

        # Reuse the valid existing session.
        if principal is not None:

            quota = store.status(
                "guest",
                principal,
            )

            return {
                "mode": "guest",
                "message": (
                    "Guest session already active."
                ),
                "limit": quota.limit,
                "remaining": quota.remaining,
                "reset_at": quota.reset_at,
            }

        # Create a new anonymous identity.
        token = store.create_guest()

        response.set_cookie(
            key=GUEST_COOKIE,
            value=token,
            httponly=True,
            secure=cookie_secure,
            samesite=cookie_samesite,
            max_age=DAY_SECONDS,
            path="/",
        )

        # Remove CSRF token associated with
        # any previous guest identity.
        response.delete_cookie(
            key=guest_csrf_cookie,
            httponly=False,
            secure=cookie_secure,
            samesite=cookie_samesite,
            path="/",
        )

        return {
            "mode": "guest",
            "message": "Guest session created.",
            "limit": GUEST_LIMIT,
            "remaining": GUEST_LIMIT,
        }

    # ======================================
    # 9. GET GUEST CSRF TOKEN
    # ======================================

    @router.get("/csrf-token")
    def get_guest_csrf(
        response: Response,
        context: dict = Depends(
            guest_context
        ),
    ):

        csrf_token = generate_csrf(
            context["token"]
        )

        response.set_cookie(
            key=guest_csrf_cookie,
            value=csrf_token,
            httponly=False,
            secure=cookie_secure,
            samesite=cookie_samesite,
            max_age=DAY_SECONDS,
            path="/",
        )

        return {
            "csrf_token": csrf_token,
        }

    # ======================================
    # 10. CREATE GUEST CONVERSATION
    # ======================================

    @router.post(
        "/threads",
        status_code=201,
    )
    def create_guest_thread(
        context: dict = Depends(
            guest_csrf
        ),
    ):

        thread_id = (
            "guest:"
            + secrets.token_urlsafe(24)
        )

        created_at = int(time.time())

        with closing(
            sqlite3.connect(store.db_path)
        ) as conn:

            with conn:

                conn.execute(
                    """
                    INSERT INTO guest_threads (
                        thread_id,
                        guest_hash,
                        created_at
                    )

                    VALUES (?, ?, ?)
                    """,
                    (
                        thread_id,
                        context["guest_hash"],
                        created_at,
                    ),
                )

        return {
            "thread_id": thread_id,
            "message": (
                "Guest conversation created."
            ),
        }

    # ======================================
    # 11. LIST GUEST CONVERSATIONS
    # ======================================

    @router.get("/threads")
    def list_guest_threads(
        context: dict = Depends(
            guest_context
        ),
    ):

        with closing(
            sqlite3.connect(store.db_path)
        ) as conn:

            conn.row_factory = sqlite3.Row

            rows = conn.execute(
                """
                SELECT thread_id, created_at

                FROM guest_threads

                WHERE guest_hash = ?

                ORDER BY created_at DESC
                """,
                (
                    context["guest_hash"],
                ),
            ).fetchall()

        result = []

        for row in rows:

            created_at = datetime.fromtimestamp(
                row["created_at"],
                tz=timezone.utc,
            ).isoformat()

            result.append({
                "thread_id": row["thread_id"],
                "created_at": created_at,
            })

        return result

    # ======================================
    # 12. GUEST CONVERSATION HISTORY
    # ======================================

    @router.get(
        "/threads/{thread_id}/messages"
    )
    def guest_history(
        thread_id: str,
        context: dict = Depends(
            guest_context
        ),
    ):

        # Never read a conversation without
        # verifying its guest ownership.
        require_owned_thread(
            context["guest_hash"],
            thread_id,
        )

        messages = get_conversation_history(
            thread_id
        )

        return {
            "thread_id": thread_id,
            "messages": serialize_history(
                messages
            ),
        }

    # ======================================
    # 13. REAL GUEST AI CHAT
    # ======================================

    @router.post("/chat")
    def guest_chat(
        payload: GuestChatRequest,
        context: dict = Depends(
            guest_csrf
        ),
    ):

        thread_id = payload.thread_id.strip()
        message = payload.message.strip()

        if not thread_id or not message:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Thread ID and message required."
                ),
            )

        # Verify thread ownership before
        # consuming the guest's quota.
        require_owned_thread(
            context["guest_hash"],
            thread_id,
        )

        quota = store.check_and_consume(
            kind="guest",
            principal_id=context["guest_hash"],
        )

        # Reject sixth message in the
        # rolling 24-hour window.
        if not quota.allowed:

            retry_after = max(
                1,
                quota.reset_at - int(time.time()),
            )

            raise HTTPException(
                status_code=429,
                detail={
                    "code": "GUEST_LIMIT_REACHED",
                    "message": (
                        "Your 5 free guest messages "
                        "have been used. "
                        "Sign in to continue."
                    ),
                    "limit": quota.limit,
                    "remaining": quota.remaining,
                    "reset_at": quota.reset_at,
                },
                headers={
                    "Retry-After": str(
                        retry_after
                    )
                },
            )

        # Call existing LangGraph + Gemini.
        # Each guest thread uses an isolated ID.
        answer = ask_odhikar_graph(
            message,
            thread_id=thread_id,
        )

        return {
            "thread_id": thread_id,
            "answer": answer,
            "usage": {
                "limit": quota.limit,
                "remaining": quota.remaining,
                "reset_at": quota.reset_at,
            },
        }

    return router
