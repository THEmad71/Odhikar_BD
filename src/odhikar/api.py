
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from src.odhikar.auth_manager import register_user


# ==========================================
# 1. CREATE FASTAPI APPLICATION
# ==========================================

app = FastAPI(
    title="Odhikar BD API",
    description="AI-Powered Bangladesh Traffic Law Assistant",
    version="1.0.0"
)


# ==========================================
# 2. REGISTRATION REQUEST SCHEMA
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
# 3. REGISTRATION RESPONSE SCHEMA
# ==========================================

class RegisterResponse(BaseModel):

    user_id: str

    display_name: str

    email: str

    created_at: str


# ==========================================
# 4. ROOT ENDPOINT
# ==========================================

@app.get("/")
def root():

    return {
        "application": "Odhikar BD",
        "message": "Welcome to Odhikar BD API",
        "status": "running"
    }


# ==========================================
# 5. HEALTH CHECK
# ==========================================

@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "application": "Odhikar BD",
        "version": "1.0.0"
    }


# ==========================================
# 6. USER REGISTRATION API
# ==========================================

@app.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED
)
def register(request: RegisterRequest):

    try:

        # Call existing authentication function
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
