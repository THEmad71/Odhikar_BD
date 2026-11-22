"""Compare baseline and Banglish expansion on identical draft heading-based questions."""
import csv
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from hybrid_retriever import HybridRetriever
from banglish_retriever import BanglishRetriever,expand_query

def main():
    dataset=Path(__file__).parent/'test_queries.json'
    if not dataset.exists():
        raise FileNotFoundError('Expected evaluation/test_queries.json from earlier evaluation ZIP')
    cases=json.loads(dataset.read_text(encoding='utf-8'))
    baseline=HybridRetriever()
    improved=BanglishRetriever()
    rows=[]
    for c in cases:
        def rank(engine):
            hits=engine.search(c['query'],top=5)
            return next((i for i,h in enumerate(hits,1) if h['section']==c['expected_section']),None)
        b=rank(baseline); n=rank(improved)
        rows.append({'language':c['language'],'query':c['query'],'expected_section':c['expected_section'],
                     'expanded_query':expand_query(c['query']), 'baseline_rank':b or '', 'expanded_rank':n or '',
                     'baseline_top1':int(b==1),'expanded_top1':int(n==1),
                     'baseline_recall5':int(b is not None),'expanded_recall5':int(n is not None)})
    for lang in sorted(set(r['language'] for r in rows)):
        subset=[r for r in rows if r['language']==lang]
        n=len(subset)
        print(f"{lang}: TOP1 {sum(r['baseline_top1'] for r in subset)}/{n} -> {sum(r['expanded_top1'] for r in subset)}/{n}; "
              f"Recall@5 {sum(r['baseline_recall5'] for r in subset)}/{n} -> {sum(r['expanded_recall5'] for r in subset)}/{n}")
    path=Path(__file__).parent/'banglish_comparison.csv'
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    print('WARNING: tiny diagnostic set partly informs manual lexicon; not independent proof of generalization or legal accuracy.')
    print('Saved:',path)

if __name__=='__main__':main()
