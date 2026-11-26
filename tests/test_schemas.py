import pytest
from pydantic import ValidationError

from src.odhikar.schemas import (
    FineLookupResult,
    ClaimCheckResult,
)


def test_fine_lookup_schema():

    data = {
        "status": "success",
        "offence_id": "no_helmet",
        "offence": "Failure to wear helmet on a motorcycle",
        "max_fine_bdt": 10000,
    }

    result = FineLookupResult.model_validate(data)

    assert result.status == "success"
    assert result.offence_id == "no_helmet"
    assert result.max_fine_bdt == 10000


def test_claim_check_schema():

    data = {
        "status": "exceeds_limit",
        "offence_id": "no_helmet",
        "claimed_amount": 15000,
        "max_fine_bdt": 10000,
        "reasons": [
            "Claimed amount exceeds maximum fine."
        ],
        "missing_items": [],
    }

    result = ClaimCheckResult.model_validate(data)

    assert result.status == "exceeds_limit"
    assert result.claimed_amount == 15000
    assert result.max_fine_bdt == 10000


def test_invalid_status_rejected():

    data = {
        "status": "everything_ok",
        "offence_id": "no_helmet",
    }

    with pytest.raises(ValidationError):
        FineLookupResult.model_validate(data)
