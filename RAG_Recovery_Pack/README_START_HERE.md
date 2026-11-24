# Odhikar BD — RAG Recovery & Verification Pack

**Safety status (2026-11-22): QUARANTINED DRAFT — NOT PRODUCTION RAG READY.**

This archive is an honest working dataset and reproducible development scaffold, **not** a legally certified corpus. The 47-page 2018 Gazette is the source. Targeted OCR corrections are from Batch 11, but source-to-text checking of all lines is incomplete. Do not feed the draft dataset to a public legal advice chatbot or let it generate fines, imprisonment, or current-law answers.

## What is complete

- Original 47-page *Road Transport Act 2018* Gazette PDF and **all 47 Batch 11 text pages** preserved without edits.
- Exact section-start map: **sections 1–126 detected once each** (structural check only).
- Section-wise **138 draft retrieval chunks** with act ID, section number, PDF page/line ranges, text checksums and official reference URL.
- Preamble in separate file; automatic section splitting retains line provenance.
- Batch 11 135-row review log preserved; **21 targeted corrected lines**, **30 partial English term matches**, **84 unresolved**. None of these counts certify the whole legal text.
- Offline keyword/character-overlap search demo and fail-closed release gate.
- Four original supplied legal PDFs retained as inputs. Names resembling 2026 amendments **have not been confirmed as enacted amendments**.
- Basic automated smoke tests available, no API key needed.

## Layout

- `source_pages/page_001.txt` ... `page_047.txt` — latest available Batch 11 targeted OCR text
- `source_pages/road_transport_act_2018_OFFICIAL_SOURCE.pdf` — 2018 Gazette identical (SHA-256) to uploaded `road_transport_act_2018.pdf`
- `source_pages/road_transport_rules_2022.pdf` and two 2026-labelled files — quarantined, not ingested
- `rag_data/chunks_DRAFT.jsonl` — provisional section-wise chunks, **production_approved=false** for every row
- `rag_data/section_index.json` — 126-section index
- `rag_data/preamble_DRAFT.json` — non-section front matter
- `reports/batch11_review_decisions.csv` — source review queue and decisions
- `reports/release_gate.json` — explicit blockers
- `reports/source_document_registry.json` — PDFs and SHA hashes
- `scripts/build_dataset.py` — regenerate all JSONL and release checks from source pages
- `scripts/search_draft.py` — simple offline retrieval preview, **not final BM25/vector RAG**
- `scripts/release_gate.py` — exits nonzero until independently approved
- `tests/test_dataset.py` — integrity smoke tests

## Run on Windows PowerShell (separate from your main project)

```powershell
cd C:\Odhikar_Bd
# Extract this archive to C:\Odhikar_Bd\rag_recovery_pack
python .\rag_recovery_pack\scripts\build_dataset.py
python -m unittest discover -s .\rag_recovery_pack\tests -v
python .\rag_recovery_pack\scripts\search_draft.py "ড্রাইভিং লাইসেন্স" --top 5
python .\rag_recovery_pack\scripts\release_gate.py
```

**Expected:** six integrity smoke tests pass; release gate exits **2 = BLOCKED** intentionally. The search tool may retrieve an incorrect section; it is a development preview only.

## What is still blocking launch

1. Resolve 84 unresolved review rows, and fully audit source text not covered by those flags. Confirm numbers, offence names, monetary penalties, imprisonment, exceptions and subsection structure visually against Gazette / authoritative electronic statute. Flagged-line remediation is not full accuracy.
2. Check current law **as of the intended deployment date** against `https://bdlaws.minlaw.gov.bd/act-print-1262.html` and official government Gazette. Check 2022 rules and the 2026-labelled PDFs for identity, legal force and temporal applicability. A consultation draft or list of gazettes must never be treated as enacted legislation without evidence.
3. Have reviewer sign off a clause-by-clause audit and save source screenshots/decision records. Keep original files immutable. Record reviewer, date, source, effective date, check results.
4. Review section boundaries and split any exceptionally long sections at legal subsection/paragraph boundaries; do not split penalties away from conditions or exceptions.
5. Build production embedding + BM25 indexes, tune multilingual/Banglish retrieval, and implement reranking/citation verification. No production Qdrant collection is created by this archive.
6. Build an answer set grounded in verified sections. Evaluate Recall@5, citation support, factual faithfulness, Bangla/Banglish robustness, penalty numeric precision, and safe abstention. Set thresholds before test selection and run blind test cases.
7. Integrate the verified retriever into existing FastAPI/LangGraph, and run guest/user permission, CSRF, origin, quota and integration regression tests.
8. Only after all the above: a designated reviewer should issue a new approval manifest, re-run tests, and explicitly unlock a **separate** production deployment pipeline. **Do not edit `production_approved` flags to make the tests pass.**

## Developer integration note

The uploaded existing source has **2 registered AI tools** (`lookup_traffic_offence`, `check_fine_claim`) in `src/odhikar/langchain_tools.py`; the LangGraph agent binds these through `llm.py` and `graph.py`. This pack is **not automatically connected**. When the corpus is fully verified, add a `search_legal_provisions` tool that calls a tested hybrid retriever, returns source excerpt + section/page + version, and updates answer policies to refuse unsupported fines or definitive legal conclusions. Do not point the current user-facing bot to `chunks_DRAFT.jsonl`.

## Authoritative source references

- Original archive Gazette: 2018 Act No. 47, 47 pages, included here.
- Government legal portal: https://bdlaws.minlaw.gov.bd/act-print-1262.html
- Road Transport & Highways Division laws index: https://rthd.gov.bd/pages/laws

The government pages were located, but a complete word-for-word comparison against their current contents was **not performed** in this pack. Any changes to legal force/current status must be documented with authoritative evidence.
