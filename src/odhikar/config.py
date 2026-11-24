
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    gemini_api_key: str | None = None

    langsmith_api_key: str | None = None
    langsmith_tracing: bool = False
    langsmith_project: str = "odhikar-bd"

    app_env: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()


# ==========================================
# LANGSMITH ENVIRONMENT CONFIGURATION
# ==========================================

if settings.langsmith_api_key:
    os.environ["LANGSMITH_API_KEY"] = (
        settings.langsmith_api_key
    )

os.environ["LANGSMITH_TRACING"] = (
    "true" if settings.langsmith_tracing else "false"
)

os.environ["LANGSMITH_PROJECT"] = (
    settings.langsmith_project
)
