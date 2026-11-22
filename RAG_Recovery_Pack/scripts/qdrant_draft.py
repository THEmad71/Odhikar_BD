"""OPTIONAL Qdrant local-mode dense index of quarantined OCR drafts.

Requires pip install qdrant-client sentence-transformers; downloads an embedding
model on first use. Uses local on-disk Qdrant, NOT production server.
Do not invoke from the live API. Never changes corpus release flags.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from hybrid_retriever import ROOT, load_chunks, BM25Index, reciprocal_rank_fusion, SECTION_RE, DIGIT_MAP

COLLECTION = 'odhikar_draft_quarantine_v1'
MODEL = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'


def components():
    try:
        from qdrant_client import QdrantClient, models
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise SystemExit('Optional deps missing: pip install qdrant-client sentence-transformers') from exc
    return QdrantClient, models, SentenceTransformer


def build(db: Path):
    QdrantClient, models, SentenceTransformer = components()
    docs = load_chunks()
    model = SentenceTransformer(MODEL)
    vectors = model.encode([d['text_bn'] for d in docs], normalize_embeddings=True, show_progress_bar=False)
    db.mkdir(parents=True, exist_ok=True)
    client = QdrantClient(path=str(db))
    if client.collection_exists(COLLECTION):
        raise SystemExit(f'Collection {COLLECTION} already exists. Refusing silent overwrite.')
    client.create_collection(COLLECTION, vectors_config=models.VectorParams(size=int(vectors.shape[1]), distance=models.Distance.COSINE))
    for start in range(0, len(docs), 25):
        batch = [models.PointStruct(id=i+1, vector=vectors[i].tolist(), payload={
            'id': docs[i]['id'], 'corpus_sha256': docs[i]['text_sha256'],
            'verification_state': docs[i]['verification_state'], 'production_approved': False,
            'section': docs[i]['section'], 'pdf_page_start': docs[i]['pdf_page_start'],
            'pdf_page_end': docs[i]['pdf_page_end']})
            for i in range(start, min(len(docs), start+25))]
        client.upsert(COLLECTION, points=batch, wait=True)
    client.close()
    print(f'Created LOCAL draft Qdrant collection with {len(docs)} chunks: {db}')


def search(db: Path, query: str, top=5):
    QdrantClient, models, SentenceTransformer = components()
    docs = load_chunks()
    if not db.exists():
        raise SystemExit('No draft index found: run build first')
    client = QdrantClient(path=str(db))
    if not client.collection_exists(COLLECTION):
        raise SystemExit('Quarantined collection missing')
    if client.count(COLLECTION, exact=True).count != len(docs):
        raise SystemExit('Draft index size mismatch; refusing search')
    model = SentenceTransformer(MODEL)
    vec = model.encode(query, normalize_embeddings=True).tolist()
    hits = client.query_points(COLLECTION, query=vec, limit=min(len(docs), max(top*4, 20))).points
    id_to_idx = {d['id']:i for i,d in enumerate(docs)}
    dense = []
    for hit in hits:
        payload = hit.payload or {}
        i = id_to_idx.get(payload.get('id'))
        if i is None or payload.get('corpus_sha256') != docs[i]['text_sha256'] or payload.get('production_approved') is not False:
            raise SystemExit('Index provenance or quarantine flag mismatch')
        dense.append((i, float(hit.score)))
    lexical = BM25Index([d['text_bn'] for d in docs]).rank(query)
    scores = reciprocal_rank_fusion([lexical, dense])
    match = SECTION_RE.search(query)
    if match:
        target = int(match.group(1).translate(DIGIT_MAP))
        for i,d in enumerate(docs):
            if d['section'] == target: scores[i] = scores.get(i,0) + 1.0
    top_indices = sorted(scores, key=lambda x: (-scores[x], x))[:max(1,min(top,20))]
    result = [{'id':docs[i]['id'], 'section':docs[i]['section'],
               'pdf_page_start':docs[i]['pdf_page_start'], 'pdf_page_end':docs[i]['pdf_page_end'],
               'verification_state': docs[i]['verification_state'], 'production_approved': False,
               'score':round(scores[i],6), 'text_bn':docs[i]['text_bn'][:500]} for i in top_indices]
    client.close()
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('operation',choices=['build','search'])
    p.add_argument('query',nargs='?')
    p.add_argument('--db',default=str(ROOT/'local_indexes'/'qdrant_DRAFT'))
    p.add_argument('--top',type=int,default=5)
    a=p.parse_args()
    if a.operation=='build': build(Path(a.db))
    else:
        if not a.query: p.error('query required for search')
        print('⚠️ DRAFT ONLY / NOT LEGAL ADVICE')
        print(json.dumps(search(Path(a.db),a.query,a.top),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
