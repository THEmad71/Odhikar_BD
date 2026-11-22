"""Quarantined hybrid retriever for the Odhikar BD DRAFT corpus.

Offline baseline: BM25 (Bengali/English words) + character n-gram TF-IDF vectors,
combined with reciprocal rank fusion. Optional Qdrant dense retrieval in draft mode
uses SentenceTransformers; never writes to production collections or calls an LLM.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHUNKS = ROOT / 'rag_data' / 'chunks_DRAFT.jsonl'
DIGIT_MAP = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')
TOKEN_RE = re.compile(r'[\u0980-\u09ff]+|[a-z0-9]+', re.I)
SECTION_RE = re.compile(r'(?:ধারা|section|§)\s*([০-৯0-9]{1,3})', re.I)


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower().translate(DIGIT_MAP))


def load_chunks(path: Path = CHUNKS) -> list[dict[str, Any]]:
    data = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not data:
        raise ValueError('Empty draft corpus')
    ids = [r['id'] for r in data]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate chunk ids')
    for r in data:
        if r.get('production_approved') is not False or not r.get('verification_state','').startswith('DRAFT'):
            raise ValueError('Expected quarantined DRAFT chunks exclusively; refusing mixed corpus')
        if hashlib.sha256(r['text_bn'].encode('utf-8')).hexdigest() != r['text_sha256']:
            raise ValueError(f'Text checksum mismatch: {r["id"]}')
    return data


class BM25Index:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = .75):
        self.tokenized = [tokens(s) for s in docs]
        self.freqs = [Counter(t) for t in self.tokenized]
        self.lengths = [len(t) for t in self.tokenized]
        self.avgdl = sum(self.lengths) / max(len(docs), 1)
        self.n = len(docs)
        self.k1, self.b = k1, b
        self.df = Counter(term for d in self.freqs for term in d)

    def rank(self, question: str) -> list[tuple[int, float]]:
        q = list(dict.fromkeys(tokens(question)))
        out = []
        for i, freq in enumerate(self.freqs):
            score = 0.0
            for term in q:
                if not freq.get(term):
                    continue
                df = self.df[term]
                idf = math.log(1 + (self.n - df + .5) / (df + .5))
                f = freq[term]
                score += idf * (f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.lengths[i] / max(self.avgdl, 1))))
            if score > 0:
                out.append((i, score))
        return sorted(out, key=lambda t: (-t[1], t[0]))


class LocalVectorIndex:
    """TF-IDF char-vector baseline; NOT learned multilingual semantic embeddings."""
    def __init__(self, docs: list[str]):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 5), min_df=1, sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform([d.lower().translate(DIGIT_MAP) for d in docs])

    def rank(self, question: str) -> list[tuple[int, float]]:
        vec = self.vectorizer.transform([question.lower().translate(DIGIT_MAP)])
        scores = (self.matrix @ vec.T).toarray().ravel()
        return sorted(((i, float(v)) for i, v in enumerate(scores) if v > 0), key=lambda t: (-t[1], t[0]))


def reciprocal_rank_fusion(rankings: list[list[tuple[int, float]]], k: int = 60) -> dict[int, float]:
    combined = defaultdict(float)
    for ranking in rankings:
        for rank, (doc_index, _) in enumerate(ranking, start=1):
            combined[doc_index] += 1 / (k + rank)
    return dict(combined)


class HybridRetriever:
    def __init__(self, docs: list[dict[str, Any]] | None = None):
        self.docs = docs if docs is not None else load_chunks()
        texts = [r['text_bn'] for r in self.docs]
        self.bm25 = BM25Index(texts)
        self.vector = LocalVectorIndex(texts)

    def search(self, query: str, top: int = 5) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        lexical = self.bm25.rank(query)
        vector = self.vector.rank(query)
        scores = reciprocal_rank_fusion([lexical, vector])
        match = SECTION_RE.search(query)
        if match:
            section = int(match.group(1).translate(DIGIT_MAP))
            # Explicit section reference gets a modest but decisive boost over irrelevant chunks.
            for i, item in enumerate(self.docs):
                if item['section'] == section:
                    scores[i] = scores.get(i, 0.0) + 1.0
        selected = sorted(scores, key=lambda i: (-scores[i], i))[:max(1, min(top, 20))]
        return [dict(id=self.docs[i]['id'], section=self.docs[i]['section'],
                     pdf_page_start=self.docs[i]['pdf_page_start'],
                     pdf_page_end=self.docs[i]['pdf_page_end'],
                     source_pdf=self.docs[i]['source_pdf'],
                     official_reference_url=self.docs[i]['official_reference_url'],
                     verification_state=self.docs[i]['verification_state'],
                     production_approved=False, score=round(scores[i], 6),
                     text_bn=self.docs[i]['text_bn']) for i in selected]


def main() -> int:
    parser = argparse.ArgumentParser(description='Odhikar BD quarantined hybrid search preview')
    parser.add_argument('query')
    parser.add_argument('--top', type=int, default=5)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    results = HybridRetriever().search(args.query, args.top)
    if args.json:
        print(json.dumps({'status':'DRAFT_ONLY_NOT_LEGAL_ADVICE','results':results}, ensure_ascii=False, indent=2))
    else:
        print('⚠️ QUARANTINED DRAFT — NOT VERIFIED LEGAL ADVICE. NEVER USE FOR PENALTIES.')
        for r in results:
            print(f"\n{r['id']} | §{r['section']} | PDF p.{r['pdf_page_start']}–{r['pdf_page_end']} | RRF={r['score']:.5f}")
            print(r['text_bn'][:450].replace('\n', ' '))
    return 0

if __name__ == '__main__':
    sys.exit(main())
