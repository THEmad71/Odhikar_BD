
import sqlite3
import json
import math

from contextlib import closing

from src.odhikar.database import DB_PATH
from src.odhikar.schemas import (
    FineLookupResult,
    ClaimCheckResult
)


# 1. Normalize text
def normalize_text(text: str) -> str:
    return " ".join(text.casefold().split())


# 2. Load JSON list safely
def load_json_list(value) -> list:
    try:
        result = json.loads(value or "[]")

        if isinstance(result, list):
            return result

        return []

    except (json.JSONDecodeError, TypeError):
        return []


# 3. Validate monetary amount
def is_valid_amount(value) -> bool:

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False

    try:
        return math.isfinite(value) and value >= 0

    except (OverflowError, TypeError, ValueError):
        return False


# 4. Main fine lookup function
def fine_lookup(offence: str, vehicle_type: str) -> dict:

    # Validate input types
    if not isinstance(offence, str) or not isinstance(vehicle_type, str):
        return {
            "status": "invalid_input",
            "message": "Offence and vehicle type must be text."
        }

    # Validate empty input
    if not offence.strip() or not vehicle_type.strip():
        return {
            "status": "invalid_input",
            "message": "Offence and vehicle type are required."
        }

    # Normalize user input
    offence = normalize_text(offence)
    vehicle_type = normalize_text(vehicle_type)

    # Connect to database
    with closing(sqlite3.connect(DB_PATH)) as conn:

        conn.row_factory = sqlite3.Row

        rows = conn.execute("""
            SELECT * FROM offences
        """).fetchall()

    # Find matching offences
    matches = []

    for row in rows:

        aliases = load_json_list(row["aliases_banglish"])

        names = [
            row["offence_id"],
            row["name_en"],
            row["name_bn"]
        ] + aliases

        normalized_names = [
            normalize_text(name)
            for name in names
            if isinstance(name, str)
        ]

        # Exact or phrase matching
        if (
            offence in normalized_names
            or any(name and name in offence for name in normalized_names)
        ):
            matches.append(row)

    # No match found
    if not matches:
        return {
            "status": "not_found",
            "message": "No matching offence found."
        }

    # Multiple matches found
    if len(matches) > 1:
        return {
            "status": "ambiguous",
            "message": "Multiple matching offences found."
        }

    # Get matching record
    record = matches[0]

    # Check vehicle type
    vehicle_types = load_json_list(record["vehicle_types"])

    allowed = [
        normalize_text(item)
        for item in vehicle_types
        if isinstance(item, str)
    ]

    if allowed and vehicle_type not in allowed:
        return {
            "status": "vehicle_mismatch",
            "message": "This offence is not listed for this vehicle type."
        }

    # Return legal information
    return {
        "status": "success",
        "offence_id": record["offence_id"],
        "offence": record["name_en"],
        "name_bn": record["name_bn"],
        "section": record["section"],
        "max_fine_bdt": record["max_fine_bdt"],
        "max_imprisonment": record["max_imprisonment"],
        "bailable": record["bailable"],
        "additional_penalty": record["additional_penalty"],
        "vehicle_types": vehicle_types,
        "law_status": record["law_status"],
        "source_url": record["source_url"],
        "last_verified": record["last_verified"]
    }


# 5. Check claimed fine and paperwork
def check_claim(
    offence_id: str,
    claimed_amount: float,
    receipt_given: bool,
    case_number_given: bool
) -> dict:

    # Validate offence ID
    if not isinstance(offence_id, str) or not offence_id.strip():
        return {
            "status": "invalid_input",
            "reasons": ["Valid offence ID is required."],
            "missing_items": []
        }

    # Validate claimed amount
    if not is_valid_amount(claimed_amount):
        return {
            "status": "invalid_input",
            "reasons": [
                "Claimed amount must be a valid non-negative number."
            ],
            "missing_items": []
        }

    # Validate receipt and case number
    if (
        not isinstance(receipt_given, bool)
        or not isinstance(case_number_given, bool)
    ):
        return {
            "status": "invalid_input",
            "reasons": [
                "Receipt and case number values must be True or False."
            ],
            "missing_items": []
        }

    # Retrieve offence from database
    with closing(sqlite3.connect(DB_PATH)) as conn:

        conn.row_factory = sqlite3.Row

        record = conn.execute("""
            SELECT
                offence_id,
                name_en,
                section,
                max_fine_bdt,
                law_status,
                source_url,
                last_verified
            FROM offences
            WHERE offence_id = ?
        """, (offence_id.strip(),)).fetchone()

    # Check whether offence exists
    if record is None:
        return {
            "status": "not_found",
            "reasons": ["Offence ID not found in database."],
            "missing_items": []
        }

    # Identify missing paperwork information
    missing_items = []

    if not receipt_given:
        missing_items.append("receipt")

    if not case_number_given:
        missing_items.append("case number")

    # Prepare comparison
    max_fine = record["max_fine_bdt"]
    law_status = record["law_status"]

    reasons = []

    # Check whether current legal maximum is verifiable
    if law_status != "in_force" or not is_valid_amount(max_fine):

        status = "unclear"

        reasons.append(
            "A current in-force maximum fine could not be confirmed."
        )

    # Compare claimed amount with legal maximum
    elif claimed_amount > max_fine:

        status = "exceeds_limit"

        reasons.append(
            f"Claimed amount ({claimed_amount}) exceeds "
            f"the recorded maximum fine ({max_fine})."
        )

    else:

        status = "within_limit"

    # Return structured result
    return {
        "status": status,
        "offence_id": record["offence_id"],
        "offence": record["name_en"],
        "section": record["section"],
        "claimed_amount": claimed_amount,
        "max_fine_bdt": max_fine,
        "reasons": reasons,
        "missing_items": missing_items,
        "source_url": record["source_url"],
        "last_verified": record["last_verified"]
    }


# 6. Pydantic validated fine lookup
def fine_lookup_structured(
    offence: str,
    vehicle_type: str
) -> dict:

    result = fine_lookup(offence, vehicle_type)

    validated = FineLookupResult.model_validate(result)

    return validated.model_dump(exclude_none=True)


# 7. Pydantic validated claim check
def check_claim_structured(
    offence_id: str,
    claimed_amount: float,
    receipt_given: bool,
    case_number_given: bool
) -> dict:

    result = check_claim(
        offence_id,
        claimed_amount,
        receipt_given,
        case_number_given
    )

    validated = ClaimCheckResult.model_validate(result)

    return validated.model_dump(exclude_none=True)
