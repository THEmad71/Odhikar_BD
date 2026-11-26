"""
Odhikar BD configuration smoke tests.

These tests validate configuration structure
without calling Gemini or PostgreSQL.
"""

from src.odhikar.config import settings


def test_app_environment():

    assert isinstance(settings.app_env, str)
    assert settings.app_env.strip()


def test_langsmith_configuration():

    assert isinstance(settings.langsmith_project, str)
    assert settings.langsmith_project.strip()

    assert isinstance(
        settings.langsmith_tracing,
        bool
    )


def test_gemini_api_key_setting():

    assert (
        settings.gemini_api_key is None
        or isinstance(settings.gemini_api_key, str)
    )


def test_configuration_attributes():

    required = [
        "app_env",
        "langsmith_project",
        "langsmith_tracing",
        "gemini_api_key",
    ]

    for attribute in required:
        assert hasattr(settings, attribute)
