"""Non-bypassable fail-closed pre-production gate for this recovery archive."""
from pathlib import Path
import json,sys
root=Path(__file__).resolve().parents[1]
gate=json.loads((root/'reports'/'release_gate.json').read_text(encoding='utf8'))
chunks=[json.loads(x) for x in (root/'rag_data'/'chunks_DRAFT.jsonl').read_text(encoding='utf8').splitlines() if x]
issues=[]
if gate.get('release_status')!='PRODUCTION_APPROVED':issues.append('Dataset is not approved')
if gate.get('unresolved_review_count')!=0:issues.append(f"{gate['unresolved_review_count']} unresolved review records")
if any(not x.get('production_approved',False) for x in chunks):issues.append('Unapproved draft chunks exist')
if any(not x.get('amendment_currency_checked',False) for x in chunks):issues.append('Amendment/current-law verification missing')
if any(not x.get('legal_penalty_verified',False) for x in chunks):issues.append('Penalty verification missing')
if issues:
 print('RELEASE BLOCKED — NOT RAG READY')
 for issue in issues: print(' - '+issue)
 sys.exit(2)
print('RELEASE APPROVED')
