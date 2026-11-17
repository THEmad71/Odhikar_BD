
from pydantic import ValidationError

from src.odhikar.schemas import (
    FineLookupResult,
    ClaimCheckResult
)


# Test 1: Fine Lookup
print("\n--- TEST 1: FINE LOOKUP ---")

fine_data = {
    "status": "success",
    "offence_id": "no_helmet",
    "offence": "Failure to wear helmet on a motorcycle",
    "max_fine_bdt": 10000
}

fine_result = FineLookupResult.model_validate(fine_data)

print(fine_result.model_dump())


# Test 2: Claim Check
print("\n--- TEST 2: CLAIM CHECK ---")

claim_data = {
    "status": "exceeds_limit",
    "offence_id": "no_helmet",
    "claimed_amount": 15000,
    "max_fine_bdt": 10000,
    "reasons": [
        "Claimed amount exceeds maximum fine."
    ],
    "missing_items": []
}

claim_result = ClaimCheckResult.model_validate(claim_data)

print(claim_result.model_dump())


# Test 3: Invalid Status
print("\n--- TEST 3: INVALID STATUS ---")

try:

    invalid_data = {
        "status": "everything_ok",
        "offence_id": "no_helmet"
    }

    FineLookupResult.model_validate(invalid_data)

except ValidationError as e:

    print("Validation Error Detected!")
    print(e)


print("\nAll schema tests completed!")
