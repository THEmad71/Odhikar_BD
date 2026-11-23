
"""
Odhikar BD — Draft AI Preview API
=================================

Local development and research demonstration only.

Features:
- FastAPI endpoint for draft retrieval
- Existing LangGraph agent integration
- Corpus-based citation verification via draft_agent.py
- No Gemini external calls
- No raw legal text in API preview
- Localhost-only access
- Production legal advice disabled
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool


# ==========================================================
# 1. PROJECT PATHS
# ==========================================================

ROOT = Path(__file__).resolve().parent

AGENT_PATH = (
    ROOT / "draft_agent_experiment" / "scripts"
)

AGENT_FILE = AGENT_PATH / "draft_agent.py"

# The agent imports banglish_retriever and corpus_guard.
if str(AGENT_PATH) not in sys.path:
    sys.path.insert(0, str(AGENT_PATH))


# ==========================================================
# 2. LOAD EXISTING DRAFT AGENT
# ==========================================================

def load_draft_agent():
    """
    Import draft_agent.py directly from its local file.

    This avoids the Pylance unresolved-import warning
    for a module outside the standard Python package path.
    """

    if not AGENT_FILE.is_file():
        raise RuntimeError(
            f"Draft agent file not found: {AGENT_FILE}"
        )

    spec = importlib.util.spec_from_file_location(
        "odhikar_draft_agent",
        AGENT_FILE,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "Unable to create draft agent module specification"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[spec.name] = module

    spec.loader.exec_module(module)

    return module


draft_agent = load_draft_agent()

build_graph = draft_agent.build_graph
assert_gate_blocked = draft_agent.assert_gate_blocked


# ==========================================================
# 3. APP CONFIGURATION
# ==========================================================

app = FastAPI(
    title="Odhikar BD — Draft AI Preview",
    description=(
        "Experimental retrieval API for unverified "
        "Bangladesh Road Transport Act 2018 draft data."
    ),
    version="0.2.0",
    docs_url="/docs",
    redoc_url=None,
)

# Vite development origins only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


# ==========================================================
# 4. LOCAL-ONLY ACCESS CHECK
# ==========================================================

LOCAL_CLIENTS = {
    "127.0.0.1",
    "::1",
}


def require_local_client(request: Request) -> None:
    """
    Reject requests from non-local client addresses.

    This is a development safeguard, not a substitute
    for production authentication or network isolation.
    """

    client = request.client

    if client is None or client.host not in LOCAL_CLIENTS:
        raise HTTPException(
            status_code=403,
            detail="This experimental API is local-only",
        )


# ==========================================================
# 5. REQUEST SCHEMA
# ==========================================================

class Question(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=800,
        description="Bangla or Banglish question",
    )


# ==========================================================
# 6. LANGGRAPH INITIALIZATION
# ==========================================================

_graph = None
_graph_lock = Lock()


def get_graph():
    """
    Initialize LangGraph once per server process.

    Release gate is rechecked for every request
    in run_preview().
    """

    global _graph

    if _graph is None:
        with _graph_lock:
            if _graph is None:
                assert_gate_blocked()
                _graph = build_graph()

    return _graph


# ==========================================================
# 7. HEALTH ENDPOINT
# ==========================================================

@app.get("/health")
def health(request: Request):
    require_local_client(request)

    try:
        assert_gate_blocked()

    except (RuntimeError, OSError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="Draft safety gate unavailable",
        )

    return {
        "status": "ok",
        "mode": "DRAFT_ONLY",
        "production_approved": False,
        "external_ai_enabled": False,
    }


# ==========================================================
# 8. EXECUTE SAFE DRAFT PREVIEW
# ==========================================================

def run_preview(query: str) -> dict[str, Any]:
    """
    Run existing LangGraph in preview-only mode.

    The draft_agent.py is responsible for:
    - Penalty query refusal
    - Draft-only source checks
    - Corpus identity verification
    - Citation metadata validation
    - No raw source text in preview answers
    """

    assert_gate_blocked()

    question = query.strip()

    if not question:
        raise ValueError("Question cannot be empty")

    graph = get_graph()

    result = graph.invoke({
        "query": question,
        "mode": "preview",
        "allow_external_draft": False,
    })

    if not isinstance(result, dict):
        raise RuntimeError("Invalid agent result")

    answer = result.get("answer")
    citations = result.get("citations", [])

    if not isinstance(answer, str):
        raise RuntimeError("Invalid agent answer")

    if not isinstance(citations, list):
        raise RuntimeError("Invalid agent citations")

    # Only output approved metadata fields.
    safe_citations = []

    for item in citations:

        if not isinstance(item, dict):
            raise RuntimeError("Invalid citation item")

        safe_citations.append({
            "chunk_id": item["chunk_id"],
            "section": item["section"],
            "pdf_pages": item["pdf_pages"],
            "verification_state": item["verification_state"],
        })

    return {
        "status": "DRAFT_ONLY_NOT_LEGAL_ADVICE",
        "answer": answer,
        "citations": safe_citations,
        "blocked_reason": result.get("blocked_reason"),
        "production_approved": False,
    }


# ==========================================================
# 9. API ENDPOINT
# ==========================================================

@app.post("/api/draft-preview")
async def draft_preview(
    body: Question,
    request: Request,
):
    require_local_client(request)

    try:
        return await run_in_threadpool(
            run_preview,
            body.query,
        )

    except (RuntimeError, ValueError, KeyError, OSError):
        # Do not expose internal file paths or source data.
        raise HTTPException(
            status_code=503,
            detail=(
                "Draft retrieval unavailable "
                "or citation verification failed"
            ),
        )


# ==========================================================
# 10. LOCAL SERVER ENTRY POINT
# ==========================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8001,
    )
