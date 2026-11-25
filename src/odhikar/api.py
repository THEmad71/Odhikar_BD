
"""
Odhikar BD - Secure FastAPI Application
Version 2.1

Features:
- Registration and login
- Secure session cookies
- CSRF protection
- Login rate limiting
- Authenticated thread management
- Guest session and guest chat
- 5 guest messages / rolling 24 hours
- 30 member messages / Bangladesh day
- Thread ownership verification
- LangGraph and Gemini integration
"""

import os
import time
import hmac
import hashlib
import secrets
import logging

from collections import defaultdict, deque
from threading import Lock
from typing import Literal

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    HTTPException,
    Response,
    Request,
    Depends,
    Path,
)

from fastapi.middleware.cors import CORSMiddleware

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
)

from src.odhikar.config import settings
from src.odhikar.database import init_db

from src.odhikar.auth_manager import register_user

from src.odhikar.session_manager import (
    login_with_session,
    logout_session,
    validate_session,
)

from src.odhikar.thread_manager import (
    create_authenticated_thread,
    ask_in_authenticated_thread,
    get_authenticated_thread_history,
    list_authenticated_threads,
    reset_authenticated_thread,
    delete_authenticated_thread,
)

from src.odhikar.usage_limits import (
    GUEST_COOKIE,
    UsageStore,
)

from src.odhikar.guest_routes import (
    build_guest_router,
)


# ==========================================
# 1. APPLICATION CONFIGURATION
# ==========================================

load_dotenv()

logger = logging.getLogger("odhikar.api")

APP_NAME = "Odhikar BD"

SESSION_COOKIE = "odhikar_session"
CSRF_COOKIE = "odhikar_csrf"

SESSION_MAX_AGE = 24 * 60 * 60

COOKIE_SECURE = (
    settings.app_env.lower()
    in {"production", "prod"}
)

COOKIE_SAMESITE = "lax"

ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "ODHIKAR_ALLOWED_ORIGINS",
        (
            ""
            if COOKIE_SECURE
            else (
                "http://127.0.0.1:5173,"
                "http://localhost:5173"
            )
        ),
    ).split(",")
    if origin.strip()
]


# ==========================================
# 2. LOGIN RATE LIMITING
# ==========================================

MAX_LOGIN_FAILURES = 5
LOGIN_WINDOW_SECONDS = 15 * 60

login_failures = defaultdict(deque)
login_lock = Lock()


def get_client_ip(request: Request) -> str:
    if request.client is None:
        return "unknown"

    return request.client.host


def check_login_rate_limit(client_ip: str):
    now = time.monotonic()

    with login_lock:
        attempts = login_failures[client_ip]

        while (
            attempts
            and now - attempts[0]
            >= LOGIN_WINDOW_SECONDS
        ):
            attempts.popleft()

        if len(attempts) >= MAX_LOGIN_FAILURES:
            retry_after = max(
                1,
                int(
                    LOGIN_WINDOW_SECONDS
                    - (now - attempts[0])
                ),
            )

            raise HTTPException(
                status_code=429,
                detail=(
                    "Too many failed login attempts. "
                    "Please try again later."
                ),
                headers={
                    "Retry-After": str(retry_after)
                },
            )


def record_failed_login(client_ip: str):
    with login_lock:
        login_failures[client_ip].append(
            time.monotonic()
        )


def clear_login_failures(client_ip: str):
    with login_lock:
        login_failures.pop(client_ip, None)


# ==========================================
# 3. CSRF GENERATION
# ==========================================

def generate_csrf_token(
    session_token: str,
) -> str:
    nonce = secrets.token_urlsafe(32)

    signature = hmac.new(
        session_token.encode("utf-8"),
        nonce.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"{nonce}.{signature}"


# ==========================================
# 4. CSRF VALIDATION
# ==========================================

def validate_csrf_token(
    session_token: str,
    csrf_token: str,
) -> bool:
    if (
        not isinstance(session_token, str)
        or not isinstance(csrf_token, str)
        or len(csrf_token) > 512
    ):
        return False

    try:
        nonce, signature = csrf_token.split(
            ".",
            1,
        )

        if not nonce or not signature:
            return False

        expected = hmac.new(
            session_token.encode("utf-8"),
            nonce.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(
            signature,
            expected,
        )

    except (ValueError, TypeError):
        return False


# ==========================================
# 5. ORIGIN VALIDATION
# ==========================================

def validate_request_origin(
    request: Request,
):
    origin = request.headers.get("origin")

    # Preserve the existing policy for
    # non-browser clients without Origin.
    if not origin:
        return

    origin = origin.rstrip("/")

    request_origin = (
        f"{request.url.scheme}://"
        f"{request.url.netloc}"
    ).rstrip("/")

    if (
        origin != request_origin
        and origin not in ALLOWED_ORIGINS
    ):
        raise HTTPException(
            status_code=403,
            detail="Request origin is not allowed.",
        )


# ==========================================
# 6. AUTHENTICATED CONTEXT
# ==========================================

def get_authenticated_context(
    request: Request,
) -> dict:
    session_token = request.cookies.get(
        SESSION_COOKIE
    )

    if not session_token:
        raise HTTPException(
            status_code=401,
            detail=(
                "Authentication required. "
                "Please login."
            ),
        )

    user = validate_session(session_token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail=(
                "Session expired or invalid. "
                "Please login again."
            ),
        )

    return {
        "session_token": session_token,
        "user": user,
    }


# ==========================================
# 7. AUTHENTICATED CSRF DEPENDENCY
# ==========================================

def require_csrf(
    request: Request,
    context: dict = Depends(
        get_authenticated_context
    ),
) -> dict:
    validate_request_origin(request)

    csrf_cookie = request.cookies.get(
        CSRF_COOKIE
    )

    csrf_header = request.headers.get(
        "X-CSRF-Token"
    )

    if (
        not csrf_cookie
        or not csrf_header
        or not hmac.compare_digest(
            csrf_cookie,
            csrf_header,
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="CSRF validation failed.",
        )

    if not validate_csrf_token(
        context["session_token"],
        csrf_header,
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid CSRF token.",
        )

    return context


# ==========================================
# 8. REQUEST MODELS
# ==========================================

class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    display_name: str = Field(
        min_length=1,
        max_length=100,
    )

    email: str = Field(
        min_length=5,
        max_length=254,
    )

    password: str = Field(
        min_length=12,
        max_length=128,
    )


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    email: str = Field(
        min_length=5,
        max_length=254,
    )

    password: str = Field(
        min_length=1,
        max_length=128,
    )


class ChatRequest(BaseModel):
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
# 9. RESPONSE MODELS
# ==========================================

class UserResponse(BaseModel):
    user_id: str
    display_name: str
    email: str
    created_at: str


class LoginResponse(BaseModel):
    message: str
    user: UserResponse


class ThreadCreateResponse(BaseModel):
    message: str
    thread_id: str


class ThreadResponse(BaseModel):
    thread_id: str
    created_at: str


class ChatResponse(BaseModel):
    thread_id: str
    answer: str


class HistoryMessage(BaseModel):
    role: Literal[
        "user",
        "assistant",
    ]
    content: str


class ConversationHistoryResponse(BaseModel):
    thread_id: str
    messages: list[HistoryMessage]


# ==========================================
# 10. THREAD OWNERSHIP
# ==========================================

def user_owns_thread(
    session_token: str,
    thread_id: str,
) -> bool:
    return any(
        thread.get("thread_id") == thread_id
        for thread in list_authenticated_threads(
            session_token
        )
    )


# ==========================================
# 11. CONVERSATION SERIALIZATION
# ==========================================

def extract_message_text(content) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for block in content:
            if isinstance(block, str):
                parts.append(block)

            elif (
                isinstance(block, dict)
                and isinstance(
                    block.get("text"),
                    str,
                )
            ):
                parts.append(block["text"])

        return "\n".join(parts).strip()

    return ""


def serialize_conversation_history(
    messages,
) -> list[dict]:
    result = []

    for message in messages:
        message_type = getattr(
            message,
            "type",
            "",
        )

        if message_type == "human":
            role = "user"

        elif message_type == "ai":
            role = "assistant"

        else:
            # Hide system and tool messages.
            continue

        content = extract_message_text(
            getattr(
                message,
                "content",
                "",
            )
        )

        if content:
            result.append({
                "role": role,
                "content": content,
            })

    return result


# ==========================================
# 12. FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title="Odhikar BD API",
    description=(
        "AI-Powered Bangladesh Traffic "
        "Law Assistant"
    ),
    version="2.1.0",
)


# ==========================================
# 12A. DATABASE INITIALIZATION
# ==========================================

@app.on_event("startup")
def initialize_application_database():
    """
    Ensure the central offences table exists before
    the API starts serving requests.

    CREATE TABLE IF NOT EXISTS preserves existing data.
    This does not populate or overwrite offence records.
    """
    init_db()
    logger.info("Odhikar BD central database initialized.")




# ==========================================
# 13. CORS
# ==========================================

if ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=[
            "GET",
            "POST",
            "DELETE",
            "OPTIONS",
        ],
        allow_headers=[
            "Content-Type",
            "X-CSRF-Token",
        ],
    )


# ==========================================
# 14. USAGE STORE
# ==========================================

usage_store = UsageStore()


# ==========================================
# 15. ROOT AND HEALTH
# ==========================================

@app.get("/")
def root():
    return {
        "application": APP_NAME,
        "message": (
            "Welcome to Odhikar BD API"
        ),
        "status": "running",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": APP_NAME,
        "version": app.version,
    }


# ==========================================
# 16. REGISTER
# ==========================================

@app.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
)
def register(
    request: RegisterRequest,
    http_request: Request,
):
    validate_request_origin(http_request)

    try:
        return register_user(
            display_name=request.display_name,
            email=request.email,
            password=request.password,
        )

    except ValueError as error:
        message = str(error)

        code = (
            409
            if "already registered"
            in message.lower()
            else 400
        )

        raise HTTPException(
            status_code=code,
            detail=message,
        ) from error


# ==========================================
# 17. LOGIN
# ==========================================

@app.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    request: LoginRequest,
    response: Response,
    http_request: Request,
):
    validate_request_origin(http_request)

    client_ip = get_client_ip(http_request)

    check_login_rate_limit(client_ip)

    result = login_with_session(
        email=request.email,
        password=request.password,
    )

    if result is None:
        record_failed_login(client_ip)

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    clear_login_failures(client_ip)

    response.set_cookie(
        key=SESSION_COOKIE,
        value=result["session_token"],
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=SESSION_MAX_AGE,
        path="/",
    )

    # Clear CSRF from any previous login.
    response.delete_cookie(
        key=CSRF_COOKIE,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )

    return {
        "message": "Login successful.",
        "user": result["user"],
    }


# ==========================================
# 18. GET AUTHENTICATED CSRF TOKEN
# ==========================================

@app.get("/csrf-token")
def get_csrf_token(
    response: Response,
    context: dict = Depends(
        get_authenticated_context
    ),
):
    csrf_token = generate_csrf_token(
        context["session_token"]
    )

    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=SESSION_MAX_AGE,
        path="/",
    )

    return {
        "csrf_token": csrf_token,
    }


# ==========================================
# 19. LOGOUT
# ==========================================

@app.post("/logout")
def logout(
    request: Request,
    response: Response,
):
    validate_request_origin(request)

    token = request.cookies.get(
        SESSION_COOKIE
    )

    revoked = False

    if token:
        csrf_cookie = request.cookies.get(
            CSRF_COOKIE
        )

        csrf_header = request.headers.get(
            "X-CSRF-Token"
        )

        if (
            not csrf_cookie
            or not csrf_header
            or not hmac.compare_digest(
                csrf_cookie,
                csrf_header,
            )
            or not validate_csrf_token(
                token,
                csrf_header,
            )
        ):
            raise HTTPException(
                status_code=403,
                detail="CSRF validation failed.",
            )

        revoked = logout_session(token)

    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )

    response.delete_cookie(
        key=CSRF_COOKIE,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )

    return {
        "message": "Logout successful.",
        "status": (
            "logged_out"
            if revoked
            else "already_logged_out"
        ),
    }


# ==========================================
# 20. CURRENT USER
# ==========================================

@app.get(
    "/me",
    response_model=UserResponse,
)
def get_current_user(
    context: dict = Depends(
        get_authenticated_context
    ),
):
    return context["user"]


# ==========================================
# 21. CREATE MEMBER THREAD
# ==========================================

@app.post(
    "/threads",
    response_model=ThreadCreateResponse,
    status_code=201,
)
def create_thread(
    context: dict = Depends(require_csrf),
):
    thread_id = create_authenticated_thread(
        context["session_token"]
    )

    if thread_id is None:
        raise HTTPException(
            status_code=500,
            detail="Unable to create conversation.",
        )

    return {
        "message": (
            "Conversation created successfully."
        ),
        "thread_id": thread_id,
    }


# ==========================================
# 22. LIST MEMBER THREADS
# ==========================================

@app.get(
    "/threads",
    response_model=list[ThreadResponse],
)
def get_threads(
    context: dict = Depends(
        get_authenticated_context
    ),
):
    threads = list_authenticated_threads(
        context["session_token"]
    )

    return [
        {
            "thread_id": thread["thread_id"],
            "created_at": thread["created_at"],
        }
        for thread in threads
    ]


# ==========================================
# 23. MEMBER THREAD HISTORY
# ==========================================

@app.get(
    "/threads/{thread_id}/messages",
    response_model=ConversationHistoryResponse,
)
def get_thread_messages(
    thread_id: str = Path(
        min_length=1,
        max_length=256,
    ),
    context: dict = Depends(
        get_authenticated_context
    ),
):
    thread_id = thread_id.strip()

    if not user_owns_thread(
        context["session_token"],
        thread_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    messages = get_authenticated_thread_history(
        context["session_token"],
        thread_id,
    )

    return {
        "thread_id": thread_id,
        "messages": (
            serialize_conversation_history(messages)
        ),
    }


# ==========================================
# 24. MEMBER QUOTA ENFORCEMENT
# ==========================================

def enforce_member_quota(
    user_id: str,
):
    quota = usage_store.check_and_consume(
        kind="member",
        principal_id=user_id,
    )

    if not quota.allowed:
        retry_after = max(
            1,
            quota.reset_at - int(time.time()),
        )

        raise HTTPException(
            status_code=429,
            detail={
                "code": "DAILY_LIMIT_REACHED",
                "message": (
                    "Your daily 30-message limit "
                    "has been reached."
                ),
                "limit": quota.limit,
                "remaining": quota.remaining,
                "reset_at": quota.reset_at,
            },
            headers={
                "Retry-After": str(retry_after)
            },
        )

    return quota


# ==========================================
# 25. AUTHENTICATED AI CHAT
# ==========================================

@app.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(
    chat_request: ChatRequest,
    context: dict = Depends(require_csrf),
):
    thread_id = chat_request.thread_id.strip()
    message = chat_request.message.strip()

    if not thread_id or not message:
        raise HTTPException(
            status_code=400,
            detail=(
                "Thread ID and message are required."
            ),
        )

    # Ownership must be checked BEFORE
    # consuming any message quota.
    if not user_owns_thread(
        context["session_token"],
        thread_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    enforce_member_quota(
        context["user"]["user_id"]
    )

    answer = ask_in_authenticated_thread(
        session_token=context["session_token"],
        thread_id=thread_id,
        query=message,
    )

    if answer.startswith("Access denied"):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    if answer.startswith(
        "Authentication required"
    ):
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    return {
        "thread_id": thread_id,
        "answer": answer,
    }


# ==========================================
# 26. RESET MEMBER THREAD
# ==========================================

@app.post("/threads/{thread_id}/reset")
def reset_conversation(
    thread_id: str = Path(
        min_length=1,
        max_length=256,
    ),
    context: dict = Depends(require_csrf),
):
    thread_id = thread_id.strip()

    if not user_owns_thread(
        context["session_token"],
        thread_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    successful = reset_authenticated_thread(
        session_token=context["session_token"],
        thread_id=thread_id,
    )

    if not successful:
        raise HTTPException(
            status_code=404,
            detail=(
                "Conversation not found "
                "or could not be reset."
            ),
        )

    return {
        "message": "Conversation reset successfully.",
        "thread_id": thread_id,
        "status": "reset",
    }


# ==========================================
# 27. DELETE MEMBER THREAD
# ==========================================

@app.delete("/threads/{thread_id}")
def delete_conversation(
    thread_id: str = Path(
        min_length=1,
        max_length=256,
    ),
    context: dict = Depends(require_csrf),
):
    thread_id = thread_id.strip()

    if not user_owns_thread(
        context["session_token"],
        thread_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Conversation not found.",
        )

    deleted = delete_authenticated_thread(
        session_token=context["session_token"],
        thread_id=thread_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=(
                "Conversation not found "
                "or could not be deleted."
            ),
        )

    return {
        "message": "Conversation deleted successfully.",
        "thread_id": thread_id,
        "status": "deleted",
    }


# ==========================================
# 28. INCLUDE GUEST ROUTES
# ==========================================

guest_router = build_guest_router(
    store=usage_store,
    validate_origin=validate_request_origin,
    generate_csrf=generate_csrf_token,
    validate_csrf=validate_csrf_token,
    serialize_history=serialize_conversation_history,
    cookie_secure=COOKIE_SECURE,
    cookie_samesite=COOKIE_SAMESITE,
)

app.include_router(guest_router)


# ==========================================
# 29. SHARED USAGE STATUS
# ==========================================

@app.get("/usage")
def get_usage_status(
    request: Request,
):
    session_token = request.cookies.get(
        SESSION_COOKIE
    )

    # Prefer the authenticated identity.
    if session_token:
        user = validate_session(
            session_token
        )

        if user is not None:
            quota = usage_store.status(
                "member",
                user["user_id"],
            )

            return {
                "mode": "member",
                "limit": quota.limit,
                "used": quota.used,
                "remaining": quota.remaining,
                "reset_at": quota.reset_at,
            }

    # Otherwise check the guest session.
    guest_token = request.cookies.get(
        GUEST_COOKIE
    )

    guest_hash = usage_store.guest_principal(
        guest_token
    )

    if guest_hash is None:
        raise HTTPException(
            status_code=401,
            detail=(
                "Login or guest session required."
            ),
        )

    quota = usage_store.status(
        "guest",
        guest_hash,
    )

    return {
        "mode": "guest",
        "limit": quota.limit,
        "used": quota.used,
        "remaining": quota.remaining,
        "reset_at": quota.reset_at,
    }
