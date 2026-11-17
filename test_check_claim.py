
from src.odhikar.tools import check_claim


# Test 1: Amount within legal maximum
print("\n--- TEST 1: WITHIN LIMIT ---")

result = check_claim(
    offence_id="no_helmet",
    claimed_amount=5000,
    receipt_given=False,
    case_number_given=False
)

print(result)


# Test 2: Amount exceeds legal maximum
print("\n--- TEST 2: EXCEEDS LIMIT ---")

result = check_claim(
    offence_id="no_helmet",
    claimed_amount=15000,
    receipt_given=True,
    case_number_given=True
)

print(result)


# Test 3: All paperwork received
print("\n--- TEST 3: ALL DOCUMENTS GIVEN ---")

result = check_claim(
    offence_id="no_helmet",
    claimed_amount=5000,
    receipt_given=True,
    case_number_given=True
)

print(result)


# Test 4: Invalid offence ID
print("\n--- TEST 4: UNKNOWN OFFENCE ---")

result = check_claim(
    offence_id="unknown_offence",
    claimed_amount=5000,
    receipt_given=False,
    case_number_given=False
)

print(result)
