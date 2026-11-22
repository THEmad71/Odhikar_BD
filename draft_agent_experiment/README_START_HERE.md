# Odhikar BD — DRAFT-only LangGraph + Gemini prototype

**Not a production legal chatbot.** The 2018 OCR corpus is unverified; current legislation/penalties are not certified. All 138 chunks remain quarantined. Do not put this app on a public website.

## How to install on Windows

Extract this folder to `C:\Odhikar_Bd\draft_agent_experiment`.

```powershell
cd C:\Odhikar_Bd
python -m pip install langgraph google-genai scikit-learn
python -m unittest discover -s .\draft_agent_experiment\tests -v
python .\draft_agent_experiment\scripts\draft_agent.py "license chara gari chalano jabe?"
python .\draft_agent_experiment\scripts\draft_agent.py "fine koto taka?"
```

Preview is offline, no Gemini API calls. Uses existing BM25+TF-IDF+Banglish baseline. Qdrant is **not** primary because the reported 12-query benchmark was weaker.

## Optional external Gemini experiment (PRIVATE only)

**Unverified legal OCR snippets will be transmitted to Gemini.** Only do this if authorized to transmit these documents and you understand that experimental model output is not legal advice.

```powershell
$env:GEMINI_API_KEY="YOUR_OWN_API_KEY"
python .\draft_agent_experiment\scripts\draft_agent.py "license chara gari chalano jabe?" --mode gemini --allow-external-draft
```

Do **not** commit the API key. `GEMINI_MODEL` defaults to `gemini-2.5-flash` and can be changed through environment configuration. API calls may incur charges. The Gemini code path has **not been live-tested** here (no API key used).

## Guardrails

- Release gate must remain `BLOCKED_NOT_PRODUCTION_RAG_READY`, with zero approved chunks.
- Every source must have `production_approved=false`, draft verification state and valid SHA-256.
- Penalty/fine/punishment questions are refused before retrieval and before any LLM call.
- No API key or transmission consent -> no Gemini request.
- Default preview is a cited excerpt list, not an answer about legal rights or fines.
- **Do not infer legal safety from passing unit tests.** The keyword guard is not sufficient for production and does not catch all oblique legal questions.

## Next work

Independently certify source passages, incorporate official amendments and rules, create evaluated labeled queries, implement source-grounded generation verification, API security and frontend integration, and only then design a reviewed production release process.
