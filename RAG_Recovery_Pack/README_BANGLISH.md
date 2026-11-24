# Odhikar BD — Banglish Query Expansion (DRAFT ONLY)

A local, small manually curated query-alias adapter on top of the existing BM25 + TF-IDF retriever. It **does not** change any legal text, chunk approval flag, FastAPI endpoint, or release gate. It is **not** a certified transliteration model.

## Install

Extract/merge the `scripts/`, `evaluation/`, and `tests/` folders into `C:\Odhikar_Bd\rag_recovery_pack\` (existing `hybrid_retriever.py` remains untouched).

## Commands (PowerShell from project root)

```
python .\rag_recovery_pack\scripts\banglish_retriever.py "license chara gari chalano jabe?" --top 5
python .\rag_recovery_pack\evaluation\evaluate_banglish.py
python -m unittest discover -s .\rag_recovery_pack\tests -v
python .\rag_recovery_pack\scripts\release_gate.py
```

`release_gate.py` must remain **BLOCKED** (exit code 2). Keep all OCR text and unapproved chunks quarantined. These results are on only 12 diagnostic queries, including 3 Banglish. Since the three phrases informed normalization choices, improved results are **not an independent benchmark**. Before production, expand the held-out dataset with spelling variations, colloquial forms, and misleading near-matches, verify law from authoritative sources, and evaluate retrieval and citations. A multilingual embedding index with Qdrant remains optional future work and is not included here.
