"""DRAFT-only Banglish query expansion for Odhikar BD.

Does not alter legal documents or approve chunks. A small manually maintained
lexicon is NOT a replacement for multilingual embedding evaluation.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from hybrid_retriever import HybridRetriever

# Search-oriented variants, not translations for use in legal answers.
# Intentionally conservative: unknown terms are preserved rather than guessed.
PHRASES = [
    (r'\bspeed\s+limit\b', 'গতিসীমা'),
    (r'\bdriving\s+licen[cs]e\b', 'ড্রাইভিং লাইসেন্স'),
    (r'\btraffic\s+sign\b', 'ট্রাফিক সংকেত'),
]
WORD_ALIASES = {
    'license':'লাইসেন্স', 'licence':'লাইসেন্স', 'laisens':'লাইসেন্স',
    'driving':'ড্রাইভিং', 'driver':'চালক', 'chara':'ব্যতীত', 'chhara':'ব্যতীত',
    'gari':'মোটরযান', 'gaari':'মোটরযান', 'garir':'মোটরযানের',
    'chalano':'চালনা', 'chalate':'চালাইতে', 'chalale':'চালাইলে',
    'jabe':'বিধি নিষেধ', 'parbo':'বিধি নিষেধ',
    'renew':'নবায়ন', 'renewal':'নবায়ন', 'nobayon':'নবায়ন',
    'korbo':'', 'kivabe':'', 'ki':'', 'koto':'', 'kotho':'',
    'speed':'গতি', 'limit':'সীমা', 'goti':'গতি',
    'helmet':'হেলমেট', 'signal':'সংকেত', 'sign':'সংকেত',
    'highway':'মহাসড়ক', 'rastay':'সড়কে',
}

def expand_query(query: str) -> str:
    """Add Bengali search terms while retaining original query and unknown words."""
    if not isinstance(query, str):
        raise TypeError('query must be a string')
    if not query.strip():
        return query
    working = query.lower()
    substitutions = []
    for pattern, replacement in PHRASES:
        if re.search(pattern, working, re.I):
            substitutions.append(replacement)
            working = re.sub(pattern, ' ', working, flags=re.I)
    for token in re.findall(r'[a-z]+', working):
        value = WORD_ALIASES.get(token)
        if value:
            substitutions.append(value)
    # Deduplicate expansions; keep source language in original query for hybrid lexical matching.
    additions = list(dict.fromkeys(substitutions))
    return (query.strip() + ' ' + ' '.join(additions)).strip()

class BanglishRetriever(HybridRetriever):
    def search(self, query: str, top: int = 5):
        return super().search(expand_query(query), top=top)

def main():
    p=argparse.ArgumentParser(description='Draft-only Banglish expansion + local hybrid retrieval')
    p.add_argument('query'); p.add_argument('--top',type=int,default=5); p.add_argument('--json',action='store_true')
    a=p.parse_args()
    expanded=expand_query(a.query)
    rows=BanglishRetriever().search(a.query,top=a.top)
    if a.json:
        print(json.dumps({'status':'DRAFT_ONLY_NOT_LEGAL_ADVICE','query':a.query,'expanded_query':expanded,'results':rows},ensure_ascii=False,indent=2))
    else:
        print('⚠️ DRAFT ONLY — NOT VERIFIED LEGAL ADVICE. NEVER USE FOR PENALTIES.')
        print('Search query:',expanded)
        for item in rows:
            print(f"{item['id']} | section {item['section']} | PDF p.{item['pdf_page_start']}-{item['pdf_page_end']} | RRF={item['score']:.5f}")
            print(item['text_bn'][:230].replace('\n',' '))
    return 0
if __name__=='__main__':
    sys.exit(main())
