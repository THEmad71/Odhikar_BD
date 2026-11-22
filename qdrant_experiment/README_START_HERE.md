# Odhikar BD — DRAFT-only Qdrant Semantic Retrieval v2

This is a **drop-in addon for the existing `Odhikar_RAG_Recovery_Pack`** from the 2026-11-23 checkpoint. It does **NOT** connect to public FastAPI/Gemini or approve any legal data.

## Installation on Windows

1. Keep existing project and review files untouched. Extract the ZIP into a separate folder, then copy ONLY `scripts/qdrant_safe_v2.py`, `tests/test_qdrant_safe_v2.py`, and `evaluation/evaluate_qdrant_v2.py` into the corresponding folders under `C:\Odhikar_Bd\review_final_checkpoint\Odhikar_RAG_Recovery_Pack`. The optional easier route: extract the included `Odhikar_RAG_Recovery_Pack` folder to a new `C:\Odhikar_Bd\qdrant_experiment` folder, without changing `rag_recovery_pack`.
2. Use your activated Python venv. **Python 3.11 or 3.12 recommended** if Torch / sentence-transformers lacks a compatible wheel for Python 3.15. Do not force-install unsupported wheels.
3. Install: `python -m pip install qdrant-client sentence-transformers` (downloads dependencies; building embeddings downloads a pretrained model on first run).

## Exact commands (separate experiment folder)

```powershell
cd C:\Odhikar_Bd
python -m unittest discover -s .\qdrant_experiment\Odhikar_RAG_Recovery_Pack\tests -v
python .\qdrant_experiment\Odhikar_RAG_Recovery_Pack\scripts\qdrant_safe_v2.py build
python .\qdrant_experiment\Odhikar_RAG_Recovery_Pack\scripts\qdrant_safe_v2.py search "license chara gari chalano jabe?" --top 5
python .\qdrant_experiment\Odhikar_RAG_Recovery_Pack\evaluation\evaluate_qdrant_v2.py
```

If you extracted `Odhikar_RAG_Recovery_Pack` to a different location, adjust the paths. The default local index is inside its `local_indexes/qdrant_v2_DRAFT`. Index builds refuse to overwrite the directory; use an entirely new `--db` path after any corpus/model changes.

## Security / validity guarantees

- `load_chunks()` validates 138 existing chunk text SHA-256s and `production_approved=false`.
- Model ID, full ordered corpus digest, individual point checksums, collection ID, index count, and quarantine flags are checked before search.
- Search runs offline on the local index, aside from the **first embedding-model download**; it does not call Gemini, FastAPI, or production systems.
- The dataset remains `DRAFT_ONLY`. Never use retrieved content for public legal advice or current fines.
- The 12-query benchmark partially informed the hand-written Banglish lexicon; its scores are *not* independent generalization estimates.
- **This package was tested with 26/26 unit/integrity tests on the supplied corpus; actual Qdrant build and dense semantic metrics have NOT been executed here because Qdrant/embedding dependencies are absent.** Test those commands on your machine and inspect results.

## Further verification

After the local model and index work, create a **separate held-out query set** and compare Banglish hybrid/dense retrieval with the baseline. Keep the original Gazette legal review and release safety gate unchanged.
