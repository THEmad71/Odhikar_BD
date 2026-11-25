
"""
ODHIKAR BD
Automated Pydantic Validation Tests

Tests:
    1. Fine lookup structured success
    2. Fine lookup not found
    3. Fine lookup invalid input
    4. Claim check within limit
    5. Claim check exceeds limit
    6. Claim check missing documents
    7. Claim check unknown offence
    8. Claim check invalid amount
    9. FineLookupResult rejects extra fields
    10. ClaimCheckResult rejects extra fields

Database:
    Neon PostgreSQL
"""

import pytest

from pydantic import ValidationError

from src.odhikar.tools import (
    fine_lookup_structured,
    check_claim_structured,
)

from src.odhikar.schemas import (
    FineLookupResult,
    ClaimCheckResult,
)


# ============================================================
# 1. FINE LOOKUP STRUCTURED TESTS
# ============================================================

def test_fine_lookup_structured_success():

    result = fine_lookup_structured(
        offence="no_helmet",
        vehicle_type="motorcycle",
    )

    assert result["status"] == "success"

    assert result["offence_id"] == "no_helmet"

    assert result["max_fine_bdt"] == 10000

    assert result["vehicle_types"] == ["motorcycle"]

    assert "offence" in result


def test_fine_lookup_structured_not_found():

    result = fine_lookup_structured(
        offence="unknown offence",
        vehicle_type="motorcycle",
    )

    assert result["status"] == "not_found"

    assert "message" in result


def test_fine_lookup_structured_invalid_input():

    result = fine_lookup_structured(
        offence="",
        vehicle_type="motorcycle",
    )

    assert result["status"] == "invalid_input"

    assert "message" in result


# ============================================================
# 2. CLAIM CHECK STRUCTURED TESTS
# ============================================================

def test_check_claim_structured_within_limit():

    result = check_claim_structured(
        offence_id="no_helmet",
        claimed_amount=5000,
        receipt_given=True,
        case_number_given=True,
    )

    assert result["status"] == "within_limit"

    assert result["claimed_amount"] == 5000

    assert result["max_fine_bdt"] == 10000

    assert result["missing_items"] == []


def test_check_claim_structured_exceeds_limit():

    result = check_claim_structured(
        offence_id="no_helmet",
        claimed_amount=15000,
        receipt_given=True,
        case_number_given=True,
    )

    assert result["status"] == "exceeds_limit"

    assert result["claimed_amount"] == 15000

    assert len(result["reasons"]) > 0


def test_check_claim_structured_missing_documents():

    result = check_claim_structured(
        offence_id="no_helmet",
        claimed_amount=5000,
        receipt_given=False,
        case_number_given=False,
    )

    assert result["status"] == "within_limit"

    assert result["missing_items"] == [
        "receipt",
        "case number",
    ]


def test_check_claim_structured_not_found():

    result = check_claim_structured(
        offence_id="unknown_offence",
        claimed_amount=5000,
        receipt_given=False,
        case_number_given=False,
    )

    assert result["status"] == "not_found"

    assert result["missing_items"] == []


def test_check_claim_structured_invalid_amount():

    result = check_claim_structured(
        offence_id="no_helmet",
        claimed_amount=-100,
        receipt_given=True,
        case_number_given=True,
    )

    assert result["status"] == "invalid_input"


# ============================================================
# 3. PYDANTIC SCHEMA VALIDATION TESTS
# ============================================================

def test_fine_lookup_schema_rejects_extra_fields():

    with pytest.raises(ValidationError):

        FineLookupResult.model_validate({
            "status": "success",
            "unexpected_field": "not allowed",
        })


def test_claim_check_schema_rejects_extra_fields():

    with pytest.raises(ValidationError):

        ClaimCheckResult.model_validate({
            "status": "within_limit",
            "unexpected_field": "not allowed",
        })
