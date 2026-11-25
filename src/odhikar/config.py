
import os

from pathlib import Path

from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict
)


# ==========================================
# 1. PROJECT ROOT
# ==========================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# ==========================================
# 2. APPLICATION SETTINGS
# ==========================================

class Settings(BaseSettings):

    # Google Gemini

    gemini_api_key: str | None = None

    # LangSmith

    langsmith_api_key: str | None = None

    langsmith_tracing: bool = False

    langsmith_project: str = "odhikar-bd"

    # Application

    app_env: str = "development"

    # PostgreSQL

    database_url: str | None = None

    database_url_direct: str | None = None

    # Connection pool

    database_pool_min_size: int = 1

    database_pool_max_size: int = 5

    database_pool_timeout: float = 30.0

    # Environment configuration

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )


# ==========================================
# 3. INITIALIZE SETTINGS
# ==========================================

settings = Settings()


# ==========================================
# 4. VALIDATE DATABASE CONFIGURATION
# ==========================================

if settings.database_pool_min_size < 1:

    raise ValueError(
        "DATABASE_POOL_MIN_SIZE must be at least 1."
    )


if (
    settings.database_pool_max_size
    < settings.database_pool_min_size
):

    raise ValueError(
        "DATABASE_POOL_MAX_SIZE cannot be "
        "smaller than DATABASE_POOL_MIN_SIZE."
    )


if settings.database_pool_timeout <= 0:

    raise ValueError(
        "DATABASE_POOL_TIMEOUT must be positive."
    )


# ==========================================
# 5. LANGSMITH CONFIGURATION
# ==========================================

if settings.langsmith_api_key:

    os.environ["LANGSMITH_API_KEY"] = (
        settings.langsmith_api_key
    )


os.environ["LANGSMITH_TRACING"] = (
    "true"
    if settings.langsmith_tracing
    else "false"
)


os.environ["LANGSMITH_PROJECT"] = (
    settings.langsmith_project
)
