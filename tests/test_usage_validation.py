"""
Odhikar BD - PostgreSQL-independent usage validation tests.

No database connection, API request, or Gemini call.
"""

import pytest

from src.odhikar.usage_limits import UsageStore


@pytest.fixture
def store():
    # Bypass __init__ to avoid database initialization.
    return UsageStore.__new__(UsageStore)


@pytest.mark.parametrize(
    "kind",
    ["unknown", "", None, "admin"],
)
def test_reject_invalid_account_type(store, kind):

    with pytest.raises(
        ValueError,
        match="Invalid account type",
    ):
        store.check_and_consume(
            kind,
            "test-principal",
        )


@pytest.mark.parametrize(
    "principal",
    ["", "   ", None, 123],
)
def test_reject_invalid_principal(store, principal):

    with pytest.raises(
        ValueError,
        match="Principal ID required",
    ):
        store.check_and_consume(
            "guest",
            principal,
        )


@pytest.mark.parametrize(
    "kind",
    ["invalid", "", None],
)
def test_status_rejects_invalid_account_type(store, kind):

    with pytest.raises(
        ValueError,
        match="Invalid account type",
    ):
        store.status(
            kind,
            "test-principal",
        )


@pytest.mark.parametrize(
    "principal",
    ["", "   ", None, 123],
)
def test_status_rejects_invalid_principal(store, principal):

    with pytest.raises(
        ValueError,
        match="Principal ID required",
    ):
        store.status(
            "member",
            principal,
        )
