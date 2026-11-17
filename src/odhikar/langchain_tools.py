
from langchain_core.tools import tool

from src.odhikar.tools import (
    fine_lookup_structured,
    check_claim_structured
)


# 1. Fine Lookup Tool
@tool("lookup_traffic_offence")
def lookup_traffic_offence(
    offence: str,
    vehicle_type: str
) -> dict:
    """
    Search the Odhikar BD database for a traffic offence.

    Use this tool when a user wants to know the legal
    information, maximum fine, or punishment for a
    particular traffic offence.

    Args:
        offence: Offence name, offence ID, Bangla or Banglish phrase.
        vehicle_type: Vehicle category, such as motorcycle or car.
    """

    return fine_lookup_structured(
        offence,
        vehicle_type
    )


# 2. Fine Claim Verification Tool
@tool("check_fine_claim")
def check_fine_claim(
    offence_id: str,
    claimed_amount: float,
    receipt_given: bool,
    case_number_given: bool
) -> dict:
    """
    Compare a claimed traffic fine with the recorded
    maximum fine for an offence.

    Also identify whether the user reports receiving
    a receipt and case number.

    Args:
        offence_id: Unique offence ID from the database.
        claimed_amount: Fine amount claimed by the user in BDT.
        receipt_given: Whether the user reports receiving a receipt.
        case_number_given: Whether the user reports receiving a case number.
    """

    return check_claim_structured(
        offence_id,
        claimed_amount,
        receipt_given,
        case_number_given
    )


# 3. Register all Odhikar BD tools
ODHIKAR_TOOLS = [
    lookup_traffic_offence,
    check_fine_claim
]
