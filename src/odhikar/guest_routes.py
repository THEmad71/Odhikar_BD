
"""
ODHIKAR BD
Secure Guest API Routes

Primary database:
    Neon PostgreSQL

Connection:
    Central Psycopg 3 ConnectionPool

Features:
    - Anonymous guest sessions
    - Guest CSRF protection
    - Guest conversation ownership
    - Guest conversation history
    - LangGraph / Gemini integration
    - Five messages per rolling 24 hours
    - PostgreSQL connection pooling
    - Existing guest data preservation

No direct SQLite dependency.
No automatic table creation or recreation.
"""

# ==========================================
# 1. IMPORTS
# ==========================================

import hmac
import logging
import secrets
import time

from datetime import datetime, timezone
from typing import Callable

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Request,
    Response,
)

from pydantic import BaseModel, ConfigDict, Field

from src.odhikar.database import get_db_connection

from src.odhikar.graph import (
    ask_odhikar_graph,
    get_conversation_history,
)

from src.odhikar.usage_limits import (
    DAY_SECONDS,
    GUEST_COOKIE,
    GUEST_LIMIT,
    UsageStore,
)


logger = logging.getLogger(__name__)

GUEST_CSRF_COOKIE = "odhikar_guest_csrf"


# ==========================================
# 2. REQUEST MODELS
# ==========================================

class GuestChatRequest(BaseModel):

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
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
# 3. POSTGRESQL SCHEMA REQUIREMENTS
# ==========================================

REQUIRED_GUEST_SCHEMA = {

    "guest_sessions": {
        "token_hash",
        "created_at",
        "expires_at",
    },

    "guest_threads": {
        "thread_id",
        "guest_hash",
        "created_at",
    },

    "usage_events": {
        "id",
        "principal_kind",
        "principal_id",
        "occurred_at",
    },

}


def verify_guest_schema() -> None:

    """
    Verify existing PostgreSQL tables.

    This function is read-only.

    It does not:
        - Create tables
        - Alter tables
        - Delete records
        - Overwrite existing data

    Psycopg uses dict_row, so rows are accessed
    through their column names.
    """

    missing_by_table = {}

    with get_db_connection() as conn:

        for table_name, required_columns in (
            REQUIRED_GUEST_SCHEMA.items()
        ):

            rows = conn.execute(
                """
                SELECT column_name

                FROM information_schema.columns

                WHERE table_schema = 'public'

                AND table_name = %s

                """,
                (table_name,),
            ).fetchall()

            existing_columns = {
                row["column_name"]
                for row in rows
            }

            missing_columns = (
                required_columns - existing_columns
            )

            if missing_columns:

                missing_by_table[table_name] = sorted(
                    missing_columns
                )

    if missing_by_table:

        details = "; ".join(
            f"{table}: {', '.join(columns)}"
            for table, columns in (
                missing_by_table.items()
            )
        )

        raise RuntimeError(
            "Guest PostgreSQL schema verification failed. "
            f"Missing columns: {details}"
        )

    logger.info(
        "Guest PostgreSQL schema verified successfully."
    )


# ==========================================
# 4. BUILD GUEST ROUTER
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
) -> APIRouter:

    router = APIRouter(
        prefix="/guest",
        tags=["Guest Access"],
    )

    # ======================================
    # 5. STARTUP SCHEMA VERIFICATION
    # ======================================

    # Verify the database during application startup.
    # Do not connect to PostgreSQL during module import.

    router.add_event_handler(
        "startup",
        verify_guest_schema,
    )

    # ======================================
    # 6. VERIFY GUEST SESSION
    # ======================================

    def guest_context(
        request: Request,
    ) -> dict:

        """
        Validate the guest cookie and resolve
        its database identity.
        """

        validate_origin(request)

        token = request.cookies.get(
            GUEST_COOKIE
        )

        if not token:

            raise HTTPException(
                status_code=401,
                detail=(
                    "Guest session is missing. "
                    "Start a new guest session."
                ),
            )

        guest_hash = store.guest_principal(
            token
        )

        if guest_hash is None:

            raise HTTPException(
                status_code=401,
                detail=(
                    "Guest session expired or is invalid. "
                    "Start a new guest session."
                ),
            )

        return {
            "token": token,
            "guest_hash": guest_hash,
        }

    # ======================================
    # 7. GUEST CSRF VALIDATION
    # ======================================

    def guest_csrf(
        request: Request,
        context: dict = Depends(
            guest_context
        ),
    ) -> dict:

        """
        Require matching CSRF cookie/header
        and a valid token signature.
        """

        csrf_cookie = request.cookies.get(
            GUEST_CSRF_COOKIE
        )

        csrf_header = request.headers.get(
            "X-CSRF-Token"
        )

        if not csrf_cookie or not csrf_header:

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
    # 8. CHECK THREAD OWNERSHIP
    # ======================================

    def owns_thread(
        guest_hash: str,
        thread_id: str,
    ) -> bool:

        """
        Confirm that a conversation belongs
        to the current guest.
        """

        with get_db_connection() as conn:

            row = conn.execute(
                """
                SELECT 1

                FROM guest_threads

                WHERE guest_hash = %s

                AND thread_id = %s

                LIMIT 1

                """,
                (
                    guest_hash,
                    thread_id,
                ),
            ).fetchone()

        return row is not None

    # ======================================
    # 9. REQUIRE THREAD OWNERSHIP
    # ======================================

    def require_owned_thread(
        guest_hash: str,
        thread_id: str,
    ) -> None:

        """
        Prevent guests from accessing
        another guest's conversations.
        """

        clean_thread_id = (
            thread_id.strip()
            if isinstance(thread_id, str)
            else ""
        )

        if (
            not clean_thread_id
            or len(clean_thread_id) > 256
            or not owns_thread(
                guest_hash,
                clean_thread_id,
            )
        ):

            raise HTTPException(
                status_code=404,
                detail="Conversation not found.",
            )

    # ======================================
    # 10. CREATE OR REUSE GUEST SESSION
    # ======================================

    @router.post("/session")
    def create_guest_session(
        request: Request,
        response: Response,
    ):

        """
        Reuse an existing valid guest session
        or create a new anonymous session.
        """

        validate_origin(request)

        existing_token = request.cookies.get(
            GUEST_COOKIE
        )

        principal = store.guest_principal(
            existing_token
        )

        # Reuse a valid existing session.

        if principal is not None:

            quota = store.status(
                "guest",
                principal,
            )

            response.status_code = 200

            return {
                "mode": "guest",
                "message": (
                    "Guest session already active."
                ),
                "limit": quota.limit,
                "used": quota.used,
                "remaining": quota.remaining,
                "reset_at": quota.reset_at,
            }

        # Create a new anonymous session.

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

        # A new session needs a fresh CSRF token.

        response.delete_cookie(
            key=GUEST_CSRF_COOKIE,
            httponly=False,
            secure=cookie_secure,
            samesite=cookie_samesite,
            path="/",
        )

        response.status_code = 201

        return {
            "mode": "guest",
            "message": "Guest session created.",
            "limit": GUEST_LIMIT,
            "used": 0,
            "remaining": GUEST_LIMIT,
        }

    # ======================================
    # 11. GET GUEST CSRF TOKEN
    # ======================================

    @router.get("/csrf-token")
    def get_guest_csrf(
        request: Request,
        response: Response,
        context: dict = Depends(
            guest_context
        ),
    ):

        """
        Issue a CSRF token for the current
        guest session.
        """

        csrf_token = generate_csrf(
            context["token"]
        )

        response.set_cookie(
            key=GUEST_CSRF_COOKIE,
            value=csrf_token,
            httponly=False,
            secure=cookie_secure,
            samesite=cookie_samesite,
            max_age=DAY_SECONDS,
            path="/",
        )

        response.headers["Cache-Control"] = "no-store"

        return {
            "csrf_token": csrf_token,
        }

    # ======================================
    # 12. CREATE GUEST CONVERSATION
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

        """
        Create a conversation owned
        by the current guest identity.
        """

        thread_id = (
            "guest:"
            + secrets.token_urlsafe(24)
        )

        created_at = int(
            time.time()
        )

        with get_db_connection() as conn:

            conn.execute(
                """
                INSERT INTO guest_threads (

                    thread_id,

                    guest_hash,

                    created_at

                )

                VALUES (%s, %s, %s)

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
    # 13. LIST GUEST CONVERSATIONS
    # ======================================

    @router.get("/threads")
    def list_guest_threads(
        context: dict = Depends(
            guest_context
        ),
    ):

        """
        Return only conversations belonging
        to the current guest.
        """

        with get_db_connection() as conn:

            rows = conn.execute(
                """
                SELECT

                    thread_id,

                    created_at

                FROM guest_threads

                WHERE guest_hash = %s

                ORDER BY created_at DESC

                """,
                (
                    context["guest_hash"],
                ),
            ).fetchall()

        result = []

        for row in rows:

            created_at = datetime.fromtimestamp(
                int(row["created_at"]),
                tz=timezone.utc,
            ).isoformat()

            result.append({

                "thread_id": row["thread_id"],

                "created_at": created_at,

            })

        return result

    # ======================================
    # 14. GUEST CONVERSATION HISTORY
    # ======================================

    @router.get(
        "/threads/{thread_id}/messages"
    )
    def guest_history(
        thread_id: str = Path(
            min_length=1,
            max_length=256,
        ),
        context: dict = Depends(
            guest_context
        ),
    ):

        """
        Return readable messages after
        verifying conversation ownership.
        """

        thread_id = thread_id.strip()

        require_owned_thread(
            context["guest_hash"],
            thread_id,
        )

        try:

            messages = get_conversation_history(
                thread_id
            )

        except Exception as error:

            logger.exception(
                "Could not load guest conversation history."
            )

            raise HTTPException(
                status_code=503,
                detail=(
                    "Conversation history is temporarily unavailable."
                ),
            ) from error

        return {

            "thread_id": thread_id,

            "messages": serialize_history(
                messages
            ),

        }

    # ======================================
    # 15. GUEST AI CHAT
    # ======================================

    @router.post("/chat")
    def guest_chat(
        payload: GuestChatRequest,
        context: dict = Depends(
            guest_csrf
        ),
    ):

        """
        Send a message to the existing
        LangGraph/Gemini assistant.
        """

        thread_id = payload.thread_id.strip()

        message = payload.message.strip()

        if not thread_id or not message:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Thread ID and message are required."
                ),
            )

        # Verify ownership before consuming quota.

        require_owned_thread(
            context["guest_hash"],
            thread_id,
        )

        # Atomically consume one message
        # from the rolling 24-hour quota.

        quota = store.check_and_consume(
            kind="guest",
            principal_id=context["guest_hash"],
        )

        # Reject requests exceeding the limit.

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
                    "Retry-After": str(retry_after),
                },
            )

        # Call the existing LangGraph + Gemini pipeline.

        try:

            answer = ask_odhikar_graph(
                message,
                thread_id=thread_id,
            )

        except Exception as error:

            logger.exception(
                "Guest LangGraph request failed."
            )

            raise HTTPException(
                status_code=502,
                detail=(
                    "The assistant is temporarily unavailable. "
                    "Please try again later."
                ),
            ) from error

        if not isinstance(answer, str) or not answer.strip():

            logger.error(
                "Guest LangGraph request returned an empty response."
            )

            raise HTTPException(
                status_code=502,
                detail=(
                    "The assistant could not generate a response. "
                    "Please try again later."
                ),
            )

        return {

            "thread_id": thread_id,

            "answer": answer,

            "usage": {

                "limit": quota.limit,

                "used": quota.used,

                "remaining": quota.remaining,

                "reset_at": quota.reset_at,

            },

        }

    # ======================================
    # 16. RETURN ROUTER
    # ======================================

    return router


# ==========================================
# 17. MODULE INFORMATION
# ==========================================

def get_guest_routes_info() -> dict:

    return {

        "module": "Odhikar BD Guest Routes",

        "database": "Neon PostgreSQL",

        "driver": "Psycopg 3",

        "connection_pool": True,

        "guest_sessions": True,

        "guest_conversations": True,

        "conversation_ownership": True,

        "csrf_protection": True,

        "rolling_24_hour_quota": True,

        "guest_message_limit": GUEST_LIMIT,

        "langgraph_integration": True,

        "legacy_sqlite": False,

        "automatic_schema_creation": False,

    }
