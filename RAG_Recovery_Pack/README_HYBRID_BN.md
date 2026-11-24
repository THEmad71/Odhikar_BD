# Odhikar BD — Hybrid Retrieval Add-on (DRAFT ONLY)

**Status: EXPERIMENTAL / NOT RAG-READY / NOT LEGAL ADVICE**

This is an **add-on** to the existing `rag_recovery_pack`. It doesn't include/replace the original Gazette, 47 text pages, or previous dataset. It does **not** approve chunks, close the 84 legal review records, or integrate with FastAPI.

## Install safely

Extract this ZIP's `scripts/`, `tests/`, and `README_HYBRID_BN.md` **inside** `C:\Odhikar_Bd\rag_recovery_pack`. Keep original sources unchanged.

In Windows PowerShell:

```powershell
cd C:\Odhikar_Bd
.\.venv\Scripts\Activate.ps1
python -m pip install scikit-learn
python .\rag_recovery_pack\scripts\hybrid_retriever.py "ধারা ৪ ড্রাইভিং লাইসেন্স" --top 5
python -m unittest discover -s .\rag_recovery_pack\tests -v
python .\rag_recovery_pack\scripts\release_gate.py
```

Expected results: 13 tests pass (assuming existing six still pass); release gate **BLOCKED / exit 2**. `hybrid_retriever.py` runs entirely offline. The 'vector' portion is **character n-gram TF-IDF, NOT multilingual neural embeddings**; BM25 and TF-IDF ranks are fused with RRF. Bengali numeral normalization and explicit-section query boost included. It is a retrieval prototype, **not** a production legal-answer generator.

## Optional Qdrant + neural multilingual embeddings

This is an additional **optional** experiment and may require significant model download/storage and dependency setup. It has **not** been executed in the build environment:

```powershell
python -m pip install qdrant-client sentence-transformers
python .\rag_recovery_pack\scripts\qdrant_draft.py build
python .\rag_recovery_pack\scripts\qdrant_draft.py search "ধারা ৪ ড্রাইভিং লাইসেন্স" --top 5
```

It uses `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` and a **local** Qdrant directory `rag_recovery_pack/local_indexes/qdrant_DRAFT`. No server connection, no production collection, and no LangGraph API exposure. Do not commit indexes or downloaded model files. Add to project `.gitignore`:

```
/rag_recovery_pack/local_indexes/
```

For Banglish quality, this baseline requires further tests / query normalization; the model's support should be evaluated rather than assumed.

## Legal verification blocker

- 84 unresolved candidate records from Batch 11
- Full penalty and source-text proofreading incomplete
- Effective amendments/current law not verified
- All 138 records marked `production_approved=false`

**Never set approval flags manually, disable release gate, or connect DRAFT to public chat.** Full source-based human review, date-effective statute validation, and blind retrieval/citation/penalty QA are required for release.
