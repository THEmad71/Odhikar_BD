"""Isolated, DRAFT-ONLY Qdrant dense retrieval for Odhikar BD.

No API integration or legal advice. Optional install: qdrant-client, sentence-transformers.
Fail-closed on corpus/model/index changes. Existing indexes are never overwritten.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

from hybrid_retriever import (ROOT, load_chunks, BM25Index,
                              reciprocal_rank_fusion, SECTION_RE, DIGIT_MAP)
from banglish_retriever import expand_query

COLLECTION = 'odhikar_draft_quarantine_v2'
MODEL_ID = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'


def corpus_digest(docs):
    payload = '\n'.join(f"{x['id']}\t{x['text_sha256']}\t{x['verification_state']}\t{x['section']}" for x in docs)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def require_quarantine(docs):
    if not docs:
        raise ValueError('Corpus is empty')
    for d in docs:
        if d.get('production_approved') is not False or not str(d.get('verification_state', '')).startswith('DRAFT'):
            raise ValueError('Mixed or non-draft chunk encountered')
        if hashlib.sha256(d['text_bn'].encode('utf-8')).hexdigest() != d['text_sha256']:
            raise ValueError(f"Chunk text changed without hash update: {d['id']}")
    if len(set(d['id'] for d in docs)) != len(docs):
        raise ValueError('Duplicate chunk ids')


def check_manifest(manifest, docs, model_id):
    if manifest.get('collection') != COLLECTION:
        raise ValueError('Collection mismatch')
    if manifest.get('model_id') != model_id:
        raise ValueError('Embedding model mismatch')
    if manifest.get('corpus_digest') != corpus_digest(docs):
        raise ValueError('Corpus changed: DO NOT search a stale index; build in a new directory')
    if manifest.get('chunk_count') != len(docs) or manifest.get('production_approved') is not False:
        raise ValueError('Count/quarantine mismatch')


def deps():
    try:
        from qdrant_client import QdrantClient, models
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SystemExit('Install optional dependencies: python -m pip install qdrant-client sentence-transformers') from exc
    return QdrantClient, models, SentenceTransformer


def build(db: Path, model_id=MODEL_ID):
    docs = load_chunks()
    require_quarantine(docs)
    # Refuse overwriting any existing directory, including an interrupted build.
    if db.exists():
        raise SystemExit(f'Directory exists; refusing overwrite: {db}')
    QdrantClient, qm, SentenceTransformer = deps()
    encoder = SentenceTransformer(model_id)
    vectors = encoder.encode([d['text_bn'] for d in docs], normalize_embeddings=True,
                             show_progress_bar=False)
    if len(vectors) != len(docs) or len(vectors[0]) == 0:
        raise RuntimeError('Invalid vector count or dimension')
    dim = len(vectors[0])
    db.mkdir(parents=True, exist_ok=False)
    client = QdrantClient(path=str(db))
    try:
        client.create_collection(COLLECTION, vectors_config=qm.VectorParams(size=dim, distance=qm.Distance.COSINE))
        for start in range(0, len(docs), 25):
            items = []
            for i in range(start, min(len(docs), start + 25)):
                d = docs[i]
                items.append(qm.PointStruct(id=i+1, vector=vectors[i].tolist(), payload={
                    'id': d['id'], 'text_sha256': d['text_sha256'], 'corpus_digest': corpus_digest(docs),
                    'verification_state': d['verification_state'], 'production_approved': False,
                    'section': d['section'], 'pdf_page_start': d['pdf_page_start'],
                    'pdf_page_end': d['pdf_page_end']}))
            client.upsert(COLLECTION, points=items, wait=True)
        if client.count(COLLECTION, exact=True).count != len(docs):
            raise RuntimeError('Index incomplete')
    finally:
        client.close()
    manifest = {'collection': COLLECTION, 'model_id': model_id, 'chunk_count': len(docs),
                'corpus_digest': corpus_digest(docs), 'production_approved': False,
                'purpose': 'OFFLINE_DRAFT_RETRIEVAL_EVALUATION_ONLY', 'dimension': dim}
    (db / 'draft_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def search(db: Path, query: str, top=5, model_id=MODEL_ID, mode='hybrid'):
    if not query.strip():
        return []
    docs = load_chunks()
    require_quarantine(docs)
    manifest_path = db / 'draft_manifest.json'
    if not manifest_path.is_file():
        raise ValueError('Missing index manifest; refusing unverified index')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    check_manifest(manifest, docs, model_id)
    QdrantClient, qm, SentenceTransformer = deps()
    encoder = SentenceTransformer(model_id)
    expanded = expand_query(query)
    vector = encoder.encode(expanded, normalize_embeddings=True).tolist()
    client = QdrantClient(path=str(db))
    try:
        if not client.collection_exists(COLLECTION):
            raise ValueError('Index collection missing')
        if client.count(COLLECTION, exact=True).count != len(docs):
            raise ValueError('Index count mismatch')
        # Retrieve the whole small draft corpus for reliable top-k validation and hybrid ranking.
        hits = client.query_points(COLLECTION, query=vector, limit=len(docs)).points
    finally:
        client.close()
    if len(hits) != len(docs):
        raise ValueError('Incomplete index results')
    by_id = {d['id']: (i, d) for i, d in enumerate(docs)}
    dense = []
    seen = set()
    for h in hits:
        p = h.payload or {}
        chunk_id = p.get('id')
        if chunk_id not in by_id or chunk_id in seen:
            raise ValueError('Unknown/duplicate chunk in Qdrant results')
        i, d = by_id[chunk_id]
        if (p.get('text_sha256') != d['text_sha256'] or
                p.get('corpus_digest') != manifest['corpus_digest'] or
                p.get('production_approved') is not False or
                p.get('verification_state') != d['verification_state']):
            raise ValueError('Provenance/quarantine mismatch in index payload')
        seen.add(chunk_id)
        dense.append((i, float(h.score)))
    rankings = [dense]
    if mode == 'hybrid':
        rankings.insert(0, BM25Index([d['text_bn'] for d in docs]).rank(expanded))
    scores = reciprocal_rank_fusion(rankings)
    section = SECTION_RE.search(query)
    if section:
        target = int(section.group(1).translate(DIGIT_MAP))
        for i, d in enumerate(docs):
            if d['section'] == target:
                scores[i] = scores.get(i, 0) + 1.0
    top_ids = sorted(scores, key=lambda i: (-scores[i], i))[:max(1,min(top,20))]
    return [{ 'id': docs[i]['id'], 'section': docs[i]['section'],
              'pdf_page_start': docs[i]['pdf_page_start'],
              'pdf_page_end': docs[i]['pdf_page_end'],
              'production_approved': False, 'verification_state': docs[i]['verification_state'],
              'score': round(scores[i],6), 'text_bn': docs[i]['text_bn'][:400]}
            for i in top_ids]


def main():
    p=argparse.ArgumentParser(description='Odhikar BD quarantined local Qdrant index')
    p.add_argument('operation', choices=['build','search'])
    p.add_argument('query', nargs='?')
    p.add_argument('--db', type=Path, default=ROOT/'local_indexes'/'qdrant_v2_DRAFT')
    p.add_argument('--top', type=int, default=5)
    p.add_argument('--mode', choices=['dense','hybrid'], default='hybrid')
    a=p.parse_args()
    if a.operation=='build':
        print(json.dumps(build(a.db), ensure_ascii=False, indent=2))
    else:
        if not a.query: p.error('search needs a query')
        print('DRAFT ONLY | NOT VERIFIED LEGAL ADVICE | NEVER USE FOR FINES')
        print(json.dumps(search(a.db, a.query, a.top, mode=a.mode), ensure_ascii=False, indent=2))

if __name__=='__main__': main()
