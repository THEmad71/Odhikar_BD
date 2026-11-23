
"""
Odhikar BD — Draft Corpus Identity Guard

Checks that retrieved records match the local draft JSONL corpus.
This is NOT independent legal verification of the Gazette.
"""

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]

CORPUS_CANDIDATES = [
    HERE.parent / "rag_data" / "chunks_DRAFT.jsonl",
    PROJECT_ROOT / "RAG_Recovery_Pack" / "rag_data" / "chunks_DRAFT.jsonl",
    PROJECT_ROOT / "qdrant_experiment"
    / "Odhikar_RAG_Recovery_Pack"
    / "rag_data" / "chunks_DRAFT.jsonl",
    PROJECT_ROOT / "review_final_checkpoint"
    / "Odhikar_RAG_Recovery_Pack"
    / "rag_data" / "chunks_DRAFT.jsonl",
]

REQUIRED = (
    "id",
    "section",
    "pdf_page_start",
    "pdf_page_end",
    "source_pdf",
    "verification_state",
    "production_approved",
    "text_bn",
)


def find_corpus():
    """
    Locate the draft corpus using known local project paths.
    Never download or substitute a different corpus automatically.
    """
    for path in CORPUS_CANDIDATES:
        if path.is_file():
            return path

    raise RuntimeError(
        "Draft corpus not found. Check chunks_DRAFT.jsonl path."
    )


def load_corpus(path=None):
    """
    Build a trusted local lookup using chunk IDs.

    Duplicate IDs or malformed records cause failure.
    """
    path = Path(path) if path is not None else find_corpus()
    records = {}

    with path.open("r", encoding="utf-8-sig") as file:
        for line_number, line in enumerate(file, 1):
            if not line.strip():
                continue

            record = json.loads(line)

            if not isinstance(record, dict):
                raise RuntimeError(
                    f"Invalid corpus record at line {line_number}"
                )

            chunk_id = record.get("id")

            if not isinstance(chunk_id, str) or not chunk_id:
                raise RuntimeError(
                    f"Missing chunk ID at line {line_number}"
                )

            if chunk_id in records:
                raise RuntimeError(
                    f"Duplicate corpus ID: {chunk_id}"
                )

            if record.get("production_approved") is not False:
                raise RuntimeError(
                    f"Non-quarantined corpus record: {chunk_id}"
                )

            if not str(
                record.get("verification_state", "")
            ).startswith("DRAFT"):
                raise RuntimeError(
                    f"Invalid verification state: {chunk_id}"
                )

            records[chunk_id] = record

    if len(records) != 138:
        raise RuntimeError(
            f"Expected 138 draft chunks, found {len(records)}"
        )

    return records


def verify_hits_against_corpus(hits, corpus=None):
    """
    Compare every retrieved hit against its canonical draft record.

    No field is silently repaired.
    A mismatch rejects the whole response.
    """
    if not isinstance(hits, list):
        raise RuntimeError("Retriever hits must be a list")

    records = corpus if corpus is not None else load_corpus()

    for hit in hits:
        if not isinstance(hit, dict):
            raise RuntimeError("Invalid retriever hit")

        chunk_id = hit.get("id")

        if chunk_id not in records:
            raise RuntimeError(
                f"Unknown corpus chunk: {chunk_id}"
            )

        trusted = records[chunk_id]

        for field in REQUIRED:
            if field not in hit or field not in trusted:
                raise RuntimeError(
                    f"Missing {field} for chunk {chunk_id}"
                )

            if hit[field] != trusted[field]:
                raise RuntimeError(
                    f"Corpus mismatch: {chunk_id}, field={field}"
                )

    return True


if __name__ == "__main__":
    corpus = load_corpus()
    print(f"PASS: {len(corpus)} quarantined chunks loaded")
    print(f"Source: {find_corpus()}")
