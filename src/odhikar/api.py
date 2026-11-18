
from fastapi import (
    FastAPI,
    HTTPException,
    status,
    Response,
    Request
)
from src.odhikar.session_manager import (
    login_with_session,
    logout_session,
    validate_session
)
from src.odhikar.thread_manager import (
    delete_owned_thread
)
from src.odhikar.thread_manager import reset_owned_thread
from src.odhikar.thread_manager import ask_in_thread

from src.odhikar.user_manager import list_user_threads

from src.odhikar.user_manager import (
    create_user_thread,
    list_user_threads
)


from pydantic import BaseModel, Field

from src.odhikar.auth_manager import register_user

from src.odhikar.session_manager import (
    login_with_session
)


# ==========================================
# 1. CREATE FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title="Odhikar BD API",
    description="AI-Powered Bangladesh Traffic Law Assistant",
    version="1.0.0"
)


# ==========================================
# 2. REGISTRATION REQUEST MODEL
# ==========================================

class RegisterRequest(BaseModel):

    display_name: str = Field(
        min_length=1,
        max_length=100
    )

    email: str = Field(
        min_length=5,
        max_length=254
    )

    password: str = Field(
        min_length=12,
        max_length=128
    )


# ==========================================
# 3. LOGIN REQUEST MODEL
# ==========================================

class LoginRequest(BaseModel):

    email: str = Field(
        min_length=5,
        max_length=254
    )

    password: str = Field(
        min_length=1,
        max_length=128
    )


# ==========================================
# 4. USER RESPONSE MODEL
# ==========================================

class UserResponse(BaseModel):

    user_id: str

    display_name: str

    email: str

    created_at: str


# ==========================================
# 5. LOGIN RESPONSE MODEL
# ==========================================

class LoginResponse(BaseModel):

    message: str

    user: UserResponse


# ==========================================
# 6. ROOT ENDPOINT
# ==========================================

@app.get("/")
def root():

    return {
        "application": "Odhikar BD",
        "message": "Welcome to Odhikar BD API",
        "status": "running"
    }


# ==========================================
# 7. HEALTH CHECK
# ==========================================

@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "application": "Odhikar BD",
        "version": "1.0.0"
    }


# ==========================================
# 8. USER REGISTRATION API
# ==========================================

@app.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def register(request: RegisterRequest):

    try:

        user = register_user(
            display_name=request.display_name,
            email=request.email,
            password=request.password
        )

        return user

    except ValueError as error:

        message = str(error)

        error_code = (
            status.HTTP_409_CONFLICT
            if "already registered" in message.lower()
            else status.HTTP_400_BAD_REQUEST
        )

        raise HTTPException(
            status_code=error_code,
            detail=message
        )


# ==========================================
# 9. USER LOGIN API
# ==========================================

@app.post(
    "/login",
    response_model=LoginResponse
)
def login(
    request: LoginRequest,
    response: Response
):

    # Authenticate user and create session
    result = login_with_session(
        email=request.email,
        password=request.password
    )

    # Reject invalid credentials
    if result is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Retrieve session token
    session_token = result["session_token"]

    # Store token in secure browser cookie
    response.set_cookie(
        key="odhikar_session",
        value=session_token,
        httponly=True,
        secure=False,  # Development only
        samesite="lax",
        max_age=24 * 60 * 60,
        path="/"
    )

    # Return public user information
    return {
        "message": "Login successful.",
        "user": result["user"]
    }


# ==========================================
# 10. USER LOGOUT API
# ==========================================

@app.post("/logout")
def logout(
    request: Request,
    response: Response
):

    # Retrieve session cookie
    session_token = request.cookies.get(
        "odhikar_session"
    )

    # Revoke session in SQLite
    revoked = False

    if session_token:

        revoked = logout_session(
            session_token
        )

    # Remove browser cookie
    response.delete_cookie(
        key="odhikar_session",
        httponly=True,
        secure=False,  # Development only
        samesite="lax",
        path="/"
    )

    if revoked:

        return {
            "message": "Logout successful.",
            "status": "logged_out"
        }

    return {
        "message": "No active session.",
        "status": "already_logged_out"
    }

# ==========================================
# 11. GET CURRENT USER API
# ==========================================

@app.get(
    "/me",
    response_model=UserResponse
)
def get_current_user(request: Request):

    # Retrieve session token from browser cookie
    session_token = request.cookies.get(
        "odhikar_session"
    )

    # Check whether session exists
    if not session_token:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please login."
        )

    # Validate session
    user = validate_session(session_token)

    # Reject invalid or expired sessions
    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please login again."
        )

    # Return authenticated user information
    return user

# ==========================================
# 12. THREAD RESPONSE MODEL
# ==========================================

class ThreadResponse(BaseModel):

    thread_id: str

    user_id: str

    created_at: str


# ==========================================
# 14. LIST USER CONVERSATIONS API
# ==========================================

@app.get(
    "/threads",
    response_model=list[ThreadResponse]
)
def get_threads(request: Request):

    # STEP 1: Get session token
    session_token = request.cookies.get(
        "odhikar_session"
    )

    if not session_token:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please login first."
        )

    # STEP 2: Validate session
    user = validate_session(session_token)

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session."
        )

    # STEP 3: Get conversations of current user
    threads = list_user_threads(
        user["user_id"]
    )

    return threads

# ==========================================
# 15. CHAT REQUEST MODEL
# ==========================================

class ChatRequest(BaseModel):

    thread_id: str = Field(
        min_length=1,
        max_length=100
    )

    message: str = Field(
        min_length=1,
        max_length=5000
    )


# ==========================================
# 16. CHAT RESPONSE MODEL
# ==========================================

class ChatResponse(BaseModel):

    thread_id: str

    answer: str


# ==========================================
# 17. AI CHAT API
# ==========================================

@app.post(
    "/chat",
    response_model=ChatResponse
)
def chat(
    request: Request,
    chat_request: ChatRequest
):

    # STEP 1: GET SESSION TOKEN

    session_token = request.cookies.get(
        "odhikar_session"
    )

    if not session_token:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please login first."
        )


    # STEP 2: VALIDATE SESSION

    user = validate_session(
        session_token
    )

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session."
        )


    # STEP 3: VALIDATE MESSAGE

    thread_id = chat_request.thread_id.strip()

    message = chat_request.message.strip()

    if not thread_id or not message:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thread ID and message are required."
        )


    # STEP 4: CHECK THREAD OWNERSHIP

    user_threads = list_user_threads(
        user["user_id"]
    )

    owns_thread = any(
        thread["thread_id"] == thread_id
        for thread in user_threads
    )

    if not owns_thread:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: This conversation does not belong to this user."
        )


    # STEP 5: SEND QUESTION TO LANGGRAPH

    answer = ask_in_thread(
        message,
        thread_id
    )


    # STEP 6: RETURN AI RESPONSE

    return {
        "thread_id": thread_id,
        "answer": answer
    }

# ==========================================
# 18. DELETE CONVERSATION API
# ==========================================

@app.delete("/threads/{thread_id}")
def delete_conversation(
    thread_id: str,
    request: Request
):

    # STEP 1: Get session
    session_token = request.cookies.get(
        "odhikar_session"
    )

    if not session_token:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please login first."
        )

    # STEP 2: Validate session
    user = validate_session(session_token)

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session."
        )

    # STEP 3: Delete owned conversation
    deleted = delete_owned_thread(
        user["user_id"],
        thread_id
    )

    if not deleted:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or could not be deleted."
        )

    # STEP 4: Return confirmation
    return {
        "message": "Conversation deleted successfully.",
        "thread_id": thread_id,
        "status": "deleted"
    }

# ==========================================
# 19. RESET CONVERSATION API
# ==========================================

@app.post("/threads/{thread_id}/reset")
def reset_conversation(
    thread_id: str,
    request: Request
):

    # STEP 1: Get session token
    session_token = request.cookies.get(
        "odhikar_session"
    )

    if not session_token:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please login first."
        )

    # STEP 2: Validate session
    user = validate_session(session_token)

    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session."
        )

    # STEP 3: Reset owned conversation
    reset_success = reset_owned_thread(
        user["user_id"],
        thread_id
    )

    if not reset_success:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or could not be reset."
        )

    # STEP 4: Return confirmation
    return {
        "message": "Conversation reset successfully.",
        "thread_id": thread_id,
        "status": "reset"
    }
