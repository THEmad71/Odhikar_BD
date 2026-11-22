"""Compare existing Banglish baseline against isolated Qdrant dense / hybrid retrieval.
Tiny 12-query heading-based diagnostic only, not legal correctness or generalization.
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from banglish_retriever import BanglishRetriever
from qdrant_safe_v2 import search as dense_search


def metrics(rows, expected):
    sections = [r['section'] for r in rows]
    return int(bool(sections) and sections[0] == expected), int(expected in sections[:5])


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--db',type=Path,default=ROOT/'local_indexes'/'qdrant_v2_DRAFT')
    p.add_argument('--output',type=Path,default=ROOT/'evaluation'/'qdrant_v2_comparison.csv')
    args=p.parse_args()
    cases=json.loads((ROOT/'evaluation'/'test_queries.json').read_text(encoding='utf-8'))
    baseline=BanglishRetriever()
    results=[]
    for case in cases:
        q=case['query']; expect=case['expected_section']
        b=metrics(baseline.search(q,5),expect)
        d=metrics(dense_search(args.db,q,5,mode='dense'),expect)
        h=metrics(dense_search(args.db,q,5,mode='hybrid'),expect)
        results.append({'language':case['language'],'query':q,'expected_section':expect,
                        'baseline_top1':b[0],'baseline_recall5':b[1],
                        'dense_top1':d[0],'dense_recall5':d[1],
                        'hybrid_top1':h[0],'hybrid_recall5':h[1]})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    for lang in ('bn','banglish','explicit'):
        subset=[r for r in results if r['language']==lang]
        print(f'{lang} ({len(subset)} queries):')
        for name in ('baseline','dense','hybrid'):
            print(f'  {name}: top1={sum(r[name+"_top1"] for r in subset)}/{len(subset)}; '
                  f'Recall@5={sum(r[name+"_recall5"] for r in subset)}/{len(subset)}')
    print('WARNING: heading-based 12-query exploratory benchmark; no legal accuracy validation')
    print('Saved:',args.output)
if __name__=='__main__': main()
