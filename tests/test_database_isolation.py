"""
Odhikar BD - Database isolation safety tests.

These tests never connect to PostgreSQL.
"""

import os
from urllib.parse import urlsplit, unquote

import pytest


def database_identity(url):
    """
    Extract database identity without exposing credentials.

    Authentication and connection options are intentionally
    excluded from the comparison.
    """
    parsed = urlsplit(url)

    if not parsed.hostname:
        raise ValueError("Database hostname is missing.")

    database_name = unquote(parsed.path.lstrip("/"))

    if not database_name:
        raise ValueError("Database name is missing.")

    return (
        parsed.hostname.lower(),
        parsed.port or 5432,
        database_name,
    )


def validate_test_database(test_url, production_urls):
    """
    Validate test database isolation.

    Raises ValueError for unsafe configuration.
    """
    if not test_url:
        raise ValueError("TEST_DATABASE_URL is missing.")

    test_identity = database_identity(test_url)
    test_name = test_identity[2].lower()

    if not any(
        word in test_name
        for word in ("test", "testing")
    ):
        raise ValueError(
            "Test database name must contain 'test'."
        )

    for production_url in production_urls:
        if not production_url:
            continue

        if test_identity == database_identity(production_url):
            raise ValueError(
                "Test database matches production database."
            )

    return True


def test_reject_missing_test_database_url():

    with pytest.raises(ValueError):
        validate_test_database("", [])


def test_reject_production_database():

    url = "postgresql://user:password@db.example.com/odhikar"

    with pytest.raises(ValueError):
        validate_test_database(url, [url])


def test_reject_same_database_with_different_credentials():

    production = (
        "postgresql://prod:secret@db.example.com/"
        "odhikar_test"
    )

    testing = (
        "postgresql://tester:another@db.example.com/"
        "odhikar_test"
    )

    with pytest.raises(ValueError):
        validate_test_database(testing, [production])


def test_accept_separate_test_database():

    production = (
        "postgresql://user:password@db.example.com/"
        "odhikar"
    )

    testing = (
        "postgresql://user:password@db.example.com/"
        "odhikar_test"
    )

    assert validate_test_database(
        testing,
        [production],
    )


def test_actual_test_database_configuration():

    test_url = os.getenv("TEST_DATABASE_URL")

    if not test_url:
        pytest.skip(
            "TEST_DATABASE_URL not configured."
        )

    production_urls = [
        os.getenv("DATABASE_URL"),
        os.getenv("DATABASE_URL_DIRECT"),
    ]

    assert validate_test_database(
        test_url,
        production_urls,
    )
