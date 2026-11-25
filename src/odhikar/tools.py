
"""
ODHIKAR BD
Legal Tools - Neon PostgreSQL Edition

Features:
    - PostgreSQL offence lookup
    - Bangla and Banglish alias matching
    - Vehicle type validation
    - Fine claim verification
    - Pydantic structured validation

Database:
    Neon PostgreSQL

SQLite:
    No SQLite runtime dependency.
"""

import os
import json
import math

from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from dotenv import load_dotenv

from src.odhikar.schemas import (
    FineLookupResult,
    ClaimCheckResult,
)


# ============================================================
# 1. ENVIRONMENT CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(
    PROJECT_ROOT / ".env",
    override=False,
)

DATABASE_URL = (
    os.getenv("DATABASE_URL_DIRECT")
    or os.getenv("DATABASE_URL")
)

EXPECTED_DATABASE = "neondb"


# ============================================================
# 2. POSTGRESQL CONNECTION
# ============================================================

def get_database_connection():

    """
    Create a PostgreSQL connection to Neon.

    No SQLite fallback is permitted.
    """

    if not DATABASE_URL:

        raise RuntimeError(
            "DATABASE_URL_DIRECT or DATABASE_URL "
            "is not configured."
        )

    conn = psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10,
        application_name="odhikar-bd-legal-tools",
    )

    try:

        database_name = conn.execute(
            "SELECT current_database()"
        ).fetchone()["current_database"]

        if database_name != EXPECTED_DATABASE:

            raise RuntimeError(
                f"Unexpected database: {database_name}. "
                f"Expected: {EXPECTED_DATABASE}."
            )

        return conn

    except Exception:

        conn.close()
        raise


# ============================================================
# 3. NORMALIZE TEXT
# ============================================================

def normalize_text(text: str) -> str:

    return " ".join(
        text.casefold().split()
    )


# ============================================================
# 4. LOAD JSON LIST SAFELY
# ============================================================

def load_json_list(value) -> list:

    if isinstance(value, list):
        return value

    try:

        result = json.loads(value or "[]")

        if isinstance(result, list):
            return result

        return []

    except (json.JSONDecodeError, TypeError):

        return []


# ============================================================
# 5. VALIDATE MONETARY AMOUNT
# ============================================================

def is_valid_amount(value) -> bool:

    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
    ):
        return False

    try:

        return (
            math.isfinite(value)
            and value >= 0
        )

    except (
        OverflowError,
        TypeError,
        ValueError,
    ):

        return False


# ============================================================
# 6. MAIN FINE LOOKUP FUNCTION
# ============================================================

def fine_lookup(
    offence: str,
    vehicle_type: str,
) -> dict:

    # Validate input types.

    if (
        not isinstance(offence, str)
        or not isinstance(vehicle_type, str)
    ):

        return {
            "status": "invalid_input",
            "message": (
                "Offence and vehicle type must be text."
            ),
        }

    # Validate empty input.

    if (
        not offence.strip()
        or not vehicle_type.strip()
    ):

        return {
            "status": "invalid_input",
            "message": (
                "Offence and vehicle type are required."
            ),
        }

    # Normalize user input.

    offence = normalize_text(offence)
    vehicle_type = normalize_text(vehicle_type)

    # Retrieve offences from Neon PostgreSQL.

    with get_database_connection() as conn:

        rows = conn.execute("""
            SELECT *
            FROM offences
            ORDER BY offence_id
        """).fetchall()

    # Find matching offences.

    matches = []

    for row in rows:

        aliases = load_json_list(
            row["aliases_banglish"]
        )

        names = [
            row["offence_id"],
            row["name_en"],
            row["name_bn"],
        ] + aliases

        normalized_names = [
            normalize_text(name)
            for name in names
            if isinstance(name, str)
        ]

        # Exact or phrase matching.

        if (
            offence in normalized_names
            or any(
                name and name in offence
                for name in normalized_names
            )
        ):

            matches.append(row)

    # No match found.

    if not matches:

        return {
            "status": "not_found",
            "message": "No matching offence found.",
        }

    # Multiple matches found.

    if len(matches) > 1:

        return {
            "status": "ambiguous",
            "message": (
                "Multiple matching offences found."
            ),
        }

    # Get matching record.

    record = matches[0]

    # Validate vehicle type.

    vehicle_types = load_json_list(
        record["vehicle_types"]
    )

    allowed = [
        normalize_text(item)
        for item in vehicle_types
        if isinstance(item, str)
    ]

    if (
        allowed
        and vehicle_type not in allowed
    ):

        return {
            "status": "vehicle_mismatch",
            "message": (
                "This offence is not listed "
                "for this vehicle type."
            ),
        }

    # Return legal information.

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
        "last_verified": record["last_verified"],
    }


# ============================================================
# 7. CHECK CLAIMED FINE AND PAPERWORK
# ============================================================

def check_claim(
    offence_id: str,
    claimed_amount: float,
    receipt_given: bool,
    case_number_given: bool,
) -> dict:

    # Validate offence ID.

    if (
        not isinstance(offence_id, str)
        or not offence_id.strip()
    ):

        return {
            "status": "invalid_input",
            "reasons": [
                "Valid offence ID is required."
            ],
            "missing_items": [],
        }

    # Validate claimed amount.

    if not is_valid_amount(claimed_amount):

        return {
            "status": "invalid_input",
            "reasons": [
                "Claimed amount must be a valid "
                "non-negative number."
            ],
            "missing_items": [],
        }

    # Validate receipt and case number.

    if (
        not isinstance(receipt_given, bool)
        or not isinstance(case_number_given, bool)
    ):

        return {
            "status": "invalid_input",
            "reasons": [
                "Receipt and case number values "
                "must be True or False."
            ],
            "missing_items": [],
        }

    # Retrieve offence from Neon PostgreSQL.

    with get_database_connection() as conn:

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

            WHERE offence_id = %s

        """, (
            offence_id.strip(),
        )).fetchone()

    # Check whether offence exists.

    if record is None:

        return {
            "status": "not_found",
            "reasons": [
                "Offence ID not found in database."
            ],
            "missing_items": [],
        }

    # Identify missing paperwork information.

    missing_items = []

    if not receipt_given:
        missing_items.append("receipt")

    if not case_number_given:
        missing_items.append("case number")

    # Prepare comparison.

    max_fine = record["max_fine_bdt"]
    law_status = record["law_status"]

    reasons = []

    # Check whether current legal maximum is verifiable.

    if (
        law_status != "in_force"
        or not is_valid_amount(max_fine)
    ):

        status = "unclear"

        reasons.append(
            "A current in-force maximum fine "
            "could not be confirmed."
        )

    # Compare claimed amount with legal maximum.

    elif claimed_amount > max_fine:

        status = "exceeds_limit"

        reasons.append(
            f"Claimed amount ({claimed_amount}) "
            f"exceeds the recorded maximum fine "
            f"({max_fine})."
        )

    else:

        status = "within_limit"

    # Return structured information.

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
        "last_verified": record["last_verified"],
    }


# ============================================================
# 8. PYDANTIC VALIDATED FINE LOOKUP
# ============================================================

def fine_lookup_structured(
    offence: str,
    vehicle_type: str,
) -> dict:

    result = fine_lookup(
        offence,
        vehicle_type,
    )

    validated = FineLookupResult.model_validate(
        result
    )

    return validated.model_dump(
        exclude_none=True
    )


# ============================================================
# 9. PYDANTIC VALIDATED CLAIM CHECK
# ============================================================

def check_claim_structured(
    offence_id: str,
    claimed_amount: float,
    receipt_given: bool,
    case_number_given: bool,
) -> dict:

    result = check_claim(
        offence_id,
        claimed_amount,
        receipt_given,
        case_number_given,
    )

    validated = ClaimCheckResult.model_validate(
        result
    )

    return validated.model_dump(
        exclude_none=True
    )
