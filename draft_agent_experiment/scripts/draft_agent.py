
"""
Odhikar BD — DRAFT-only AI Agent (Safety v2)

Purpose:
- Retrieve relevant draft legal section references.
- Never expose unverified legal passages in the preview.
- Validate citation metadata.
- Refuse penalty/punishment questions.
- Keep production release blocked.
- Disable external Gemini calls until further verification.

NOT production legal advice.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, TypedDict


# ==========================================================
# 1. PATHS AND IMPORTS
# ==========================================================

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

sys.path.insert(0, str(HERE))

from banglish_retriever import BanglishRetriever
from corpus_guard import verify_hits_against_corpus


# ==========================================================
# 2. SAFETY CONFIGURATION
# ==========================================================

WARNING = (
    "DRAFT_ONLY — আইনগতভাবে যাচাইকৃত তথ্য নয়; "
    "জরিমানা বা আইনি সিদ্ধান্তের জন্য ব্যবহার করবেন না।"
)

GATE = ROOT / "reports" / "release_gate.json"

# Refuse questions requesting fines, punishment or penalties.
PENALTY_RE = re.compile(
    r"("
    r"জরিমানা|শাস্তি|দণ্ড|টাকা|কারাদণ্ড|"
    r"fine|penalty|punishment|imprisonment|"
    r"taka|tk|"
    r"koto\s*taka|koto\s*fine|"
    r"kototaka|jrim a na|jorimana|shasti|dondo"
    r")",
    re.IGNORECASE,
)

# Expected chunk ID example: RTA2018-S004-P01
CHUNK_ID_RE = re.compile(
    r"^RTA2018-S(\d{3})-P(\d{2})$"
)

# External draft transmission remains disabled.
GEMINI_ENABLED = False


# ==========================================================
# 3. LANGGRAPH STATE
# ==========================================================

class State(TypedDict, total=False):
    query: str
    mode: str
    allow_external_draft: bool

    hits: list[dict[str, Any]]
    answer: str
    blocked_reason: str
    citations: list[dict[str, Any]]


# Lazy-loaded retriever instance
_index = None


# ==========================================================
# 4. PRODUCTION RELEASE GATE
# ==========================================================

def assert_gate_blocked() -> None:
    """
    Refuse execution unless the corpus remains quarantined.
    """

    gate = json.loads(
        GATE.read_text(encoding="utf-8")
    )

    expected_status = "BLOCKED_NOT_PRODUCTION_RAG_READY"

    if (
        gate.get("release_status") != expected_status
        or gate.get("production_approved_chunks") != 0
    ):
        raise RuntimeError(
            "Unexpected release gate. "
            "Refusing to run unverified legal experiment."
        )


# ==========================================================
# 5. QUESTION VALIDATION
# ==========================================================

def validate_question(query: str) -> str:
    """
    Ensure that the user supplies a valid question.
    """

    if not isinstance(query, str):
        raise ValueError("Question must be a string")

    query = query.strip()

    if not query:
        raise ValueError("Nonempty question required")

    if len(query) > 800:
        raise ValueError("Query too long (800 max)")

    return query


# ==========================================================
# 6. RETRIEVE DRAFT SOURCES
# ==========================================================

def retrieve(state: State) -> State:
    """
    Search draft documents using the Banglish retriever.

    Direct penalty questions are blocked before retrieval.
    """

    global _index

    assert_gate_blocked()

    query = validate_question(state["query"])

    if PENALTY_RE.search(query):
        return {
            "blocked_reason": "penalty_or_punishment_query",
            "hits": [],
        }

    if _index is None:
        _index = BanglishRetriever()

    results = _index.search(query, top=3)
    # Reject unknown or modified source records.
    verify_hits_against_corpus(results)

    for hit in results:
        if hit.get("production_approved") is not False:
            raise RuntimeError(
                "Non-draft source unexpectedly returned"
            )

        verification = hit.get("verification_state", "")

        if not isinstance(verification, str):
            raise RuntimeError(
                "Invalid source verification state"
            )

        if not verification.startswith("DRAFT"):
            raise RuntimeError(
                "Non-draft verification state detected"
            )

    return {"hits": results}


# ==========================================================
# 7. CITATION VALIDATION — SAFETY V2
# ==========================================================

def citations_from_hits(
    hits: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Validate citation metadata before generating references.

    Checks:
    - Required fields
    - DRAFT-only status
    - Section range: 1–126
    - PDF page range: 1–47
    - Chunk ID format and section consistency
    - Source PDF metadata
    - Duplicate chunk IDs

    NOTE:
    This is internal consistency validation.
    Original-Gazette and corpus-identity verification
    must be added separately.
    """

    citations = []
    seen = set()

    required_fields = [
        "id",
        "section",
        "pdf_page_start",
        "pdf_page_end",
        "source_pdf",
        "verification_state",
        "production_approved",
    ]

    for hit in hits:

        if not isinstance(hit, dict):
            raise RuntimeError("Invalid citation record")

        # Check required metadata
        for field in required_fields:
            if field not in hit:
                raise RuntimeError(
                    f"Invalid citation: missing {field}"
                )

        chunk_id = hit["id"]
        section = hit["section"]

        start = hit["pdf_page_start"]
        end = hit["pdf_page_end"]

        source_pdf = hit["source_pdf"]
        verification = hit["verification_state"]

        # Reject anything approved or non-draft
        if hit["production_approved"] is not False:
            raise RuntimeError(
                "Non-draft citation rejected"
            )

        if (
            not isinstance(verification, str)
            or not verification.startswith("DRAFT")
        ):
            raise RuntimeError(
                "Citation must have DRAFT verification state"
            )

        # Section validation
        if (
            not isinstance(section, int)
            or isinstance(section, bool)
            or not (1 <= section <= 126)
        ):
            raise RuntimeError(
                "Invalid section number"
            )

        # Page validation
        if not all(
            isinstance(page, int)
            and not isinstance(page, bool)
            for page in (start, end)
        ):
            raise RuntimeError(
                "Invalid PDF page type"
            )

        if not (1 <= start <= end <= 47):
            raise RuntimeError(
                "Invalid PDF page range"
            )

        # Chunk ID validation
        if not isinstance(chunk_id, str):
            raise RuntimeError("Invalid chunk ID")

        match = CHUNK_ID_RE.fullmatch(chunk_id)

        if match is None:
            raise RuntimeError(
                f"Malformed chunk ID: {chunk_id}"
            )

        encoded_section = int(match.group(1))

        if encoded_section != section:
            raise RuntimeError(
                "Chunk ID does not match section"
            )

        # Source validation
        if (
            not isinstance(source_pdf, str)
            or not source_pdf.strip()
        ):
            raise RuntimeError(
                "Missing source PDF"
            )

        # Remove duplicate citations
        if chunk_id in seen:
            continue

        seen.add(chunk_id)

        citations.append({
            "chunk_id": chunk_id,
            "section": section,
            "pdf_pages": [start, end],
            "source_pdf": source_pdf,
            "verification_state": verification,
        })

    return citations


# ==========================================================
# 8. ROUTING LOGIC
# ==========================================================

def guard(state: State) -> str:
    """
    Select the next graph node.
    """

    if state.get("blocked_reason"):
        return "refuse"

    if not state.get("hits"):
        return "refuse"

    mode = state.get("mode", "preview")

    if mode == "preview":
        return "preview"

    if mode == "gemini":
        return "gemini"

    return "refuse"


# ==========================================================
# 9. REFUSAL RESPONSE
# ==========================================================

def refuse(state: State) -> State:
    """
    Return a safe refusal without legal source text.
    """

    reason = (
        state.get("blocked_reason")
        or "no_matching_draft_sources"
    )

    return {
        "answer": (
            f"{WARNING}\n"
            "অনুরোধটি এই experimental system-এ "
            "উত্তর দেওয়া যাবে না। "
            f"কারণ: {reason}"
        ),
        "citations": [],
    }


# ==========================================================
# 10. SAFE PREVIEW — NO RAW TEXT LEAKAGE
# ==========================================================

def preview(state: State) -> State:
    """
    Show source references only.

    Raw unverified legal text is never included.
    """

    hits = state.get("hits", [])

    if not hits:
        return refuse({
            "blocked_reason": "no_matching_draft_sources"
        })

    # Validate all citations before displaying anything.
    citations = citations_from_hits(hits)

    lines = [
        WARNING,
        "এটি শুধু পরীক্ষামূলক document retrieval.",
        "নিচের তথ্যগুলো যাচাইকৃত আইনি পরামর্শ নয়।",
        "",
        "সম্ভাব্য প্রাসঙ্গিক Draft Sources:",
    ]

    for citation in citations:

        chunk_id = citation["chunk_id"]
        section = citation["section"]

        start, end = citation["pdf_pages"]

        lines.append(
            f"[DRAFT | {chunk_id}] "
            f"ধারা {section}, "
            f"PDF পৃষ্ঠা {start}-{end}"
        )

    lines.extend([
        "",
        "সতর্কতা: Source text ও বর্তমান আইন "
        "স্বাধীনভাবে যাচাই করা হয়নি।"
    ])

    return {
        "answer": "\n".join(lines),
        "citations": citations,
    }


# ==========================================================
# 11. GEMINI — DISABLED UNTIL FURTHER VERIFICATION
# ==========================================================

def gemini(state: State) -> State:
    """
    Preserve the Gemini workflow node but do not
    transmit unverified legal text externally.
    """

    if (
        state.get("mode") != "gemini"
        or state.get("allow_external_draft") is not True
    ):
        return {
            "answer": (
                WARNING
                + "\nGemini call blocked: "
                "explicit draft transmission consent required."
            ),
            "citations": [],
        }

    if not os.getenv("GEMINI_API_KEY"):
        return {
            "answer": (
                WARNING
                + "\nGemini call blocked: "
                "GEMINI_API_KEY missing."
            ),
            "citations": [],
        }

    if not GEMINI_ENABLED:
        return {
            "answer": (
                WARNING
                + "\nGemini call blocked: "
                "external generation is disabled "
                "until further safety verification."
            ),
            "citations": [],
        }

    # Intentionally fail closed.
    # Do not activate live Gemini merely by changing
    # GEMINI_ENABLED without reviewing this node.
    raise RuntimeError(
        "Live Gemini implementation requires safety review"
    )


# ==========================================================
# 12. BUILD LANGGRAPH WORKFLOW
# ==========================================================

def build_graph():
    """
    Workflow:

    retrieve
       |
       +---- refuse
       |
       +---- preview
       |
       +---- gemini (disabled)
    """

    try:
        from langgraph.graph import StateGraph, END

    except ImportError as exc:
        raise RuntimeError(
            "Install dependency: "
            "python -m pip install langgraph"
        ) from exc

    graph = StateGraph(State)

    graph.add_node("retrieve", retrieve)
    graph.add_node("refuse", refuse)
    graph.add_node("preview", preview)
    graph.add_node("gemini", gemini)

    graph.set_entry_point("retrieve")

    graph.add_conditional_edges(
        "retrieve",
        guard,
        {
            "refuse": "refuse",
            "preview": "preview",
            "gemini": "gemini",
        },
    )

    for node in ("refuse", "preview", "gemini"):
        graph.add_edge(node, END)

    return graph.compile()


# ==========================================================
# 13. COMMAND-LINE ENTRY POINT
# ==========================================================

def main():

    parser = argparse.ArgumentParser(
        description=(
            "Odhikar BD DRAFT-only "
            "LangGraph Agent — Safety v2"
        )
    )

    parser.add_argument(
        "query",
        help="User question"
    )

    parser.add_argument(
        "--mode",
        choices=("preview", "gemini"),
        default="preview"
    )

    parser.add_argument(
        "--allow-external-draft",
        action="store_true",
        help=(
            "Record explicit external draft consent. "
            "External calls remain disabled."
        )
    )

    args = parser.parse_args()

    if (
        args.mode == "gemini"
        and not args.allow_external_draft
    ):
        parser.error(
            "Gemini mode requires --allow-external-draft"
        )

    assert_gate_blocked()

    graph = build_graph()

    result = graph.invoke({
        "query": args.query,
        "mode": args.mode,
        "allow_external_draft": args.allow_external_draft,
    })

    print(
        json.dumps(
            {
                "status": "DRAFT_ONLY_NOT_LEGAL_ADVICE",
                "answer": result["answer"],
                "citations": result.get("citations", []),
                "blocked_reason": result.get(
                    "blocked_reason"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
