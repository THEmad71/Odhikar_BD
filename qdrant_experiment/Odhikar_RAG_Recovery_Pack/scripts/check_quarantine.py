"""Run the strict checks that prevent DRAFT legal text entering production."""
import json, pathlib, subprocess, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    chunks=[json.loads(s) for s in (ROOT/'rag_data/chunks_DRAFT.jsonl').read_text(encoding='utf-8').splitlines() if s]
    assert len(chunks)==138 and len(set(c['section'] for c in chunks))==126
    assert all(c.get('production_approved') is False for c in chunks)
    assert all(c.get('amendment_currency_checked') is False for c in chunks)
    assert all(c.get('legal_penalty_verified') is False for c in chunks)
    x=subprocess.run([sys.executable,str(ROOT/'scripts/release_gate.py')],capture_output=True,text=True)
    assert x.returncode==2, 'Unexpected release-gate result — inspect immediately'
    print('PASS: all 138 chunks quarantined; production release blocked as required')
    return 0
if __name__=='__main__':raise SystemExit(main())
