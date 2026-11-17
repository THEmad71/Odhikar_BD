
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# 1. Fine Lookup Result
class FineLookupResult(BaseModel):

    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "success",
        "not_found",
        "ambiguous",
        "vehicle_mismatch",
        "invalid_input"
    ]

    message: str | None = None

    offence_id: str | None = None
    offence: str | None = None
    name_bn: str | None = None

    section: str | None = None

    max_fine_bdt: int | float | None = None
    max_imprisonment: str | None = None

    bailable: bool | None = None
    additional_penalty: str | None = None

    vehicle_types: list[str] = Field(default_factory=list)

    law_status: str | None = None
    source_url: str | None = None
    last_verified: str | None = None


# 2. Claim Check Result
class ClaimCheckResult(BaseModel):

    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "within_limit",
        "exceeds_limit",
        "unclear",
        "not_found",
        "invalid_input"
    ]

    message: str | None = None

    offence_id: str | None = None
    offence: str | None = None
    section: str | None = None

    claimed_amount: int | float | None = None
    max_fine_bdt: int | float | None = None

    reasons: list[str] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)

    source_url: str | None = None
    last_verified: str | None = None
