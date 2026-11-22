"""Evaluate BM25+TF-IDF draft ranking on fixed heading-based questions. Never release legal corpus."""
import csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from hybrid_retriever import HybridRetriever

def main():
    cases=json.loads((Path(__file__).parent/'test_queries.json').read_text(encoding='utf8'))
    engine=HybridRetriever()
    rows=[]
    for c in cases:
        hits=engine.search(c['query'],top=5)
        rank=next((i+1 for i,h in enumerate(hits) if h['section']==c['expected_section']),None)
        rows.append({'language':c['language'],'query':c['query'],'expected_section':c['expected_section'], 'found_rank':rank or '', 'hit_at_1':int(rank==1),'hit_at_5':int(rank is not None),'top_sections':';'.join(str(h['section']) for h in hits)})
    for lang in sorted({r['language'] for r in rows}):
        sub=[r for r in rows if r['language']==lang]
        print(f"{lang}: top1={sum(r['hit_at_1'] for r in sub)}/{len(sub)}; Recall@5={sum(r['hit_at_5'] for r in sub)}/{len(sub)}")
    print('WARNING: DRAFT heading-based benchmark only; not legal accuracy validation.')
    out=Path(__file__).parent/'evaluation_results.csv'
    with out.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f, fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    print('Saved:',out)
if __name__=='__main__':main()
