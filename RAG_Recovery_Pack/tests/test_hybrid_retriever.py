import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from hybrid_retriever import HybridRetriever, BM25Index, reciprocal_rank_fusion, load_chunks

class TestHybrid(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.retriever=HybridRetriever()
    def test_all_source_chunks_loaded(self): self.assertEqual(len(self.retriever.docs),138)
    def test_section_4_explicit_query(self):
        results=self.retriever.search('ধারা ৪ ড্রাইভিং লাইসেন্স',5)
        self.assertTrue(results)
        self.assertEqual(results[0]['section'],4)
    def test_query_returns_citations(self):
        for r in self.retriever.search('ড্রাইভিং লাইসেন্স', 5):
            self.assertTrue(r['source_pdf'])
            self.assertTrue(1<=r['pdf_page_start']<=r['pdf_page_end']<=47)
            self.assertFalse(r['production_approved'])
    def test_no_hallucinated_legal_answer(self):
        r=self.retriever.search('জরিমানা',3)
        self.assertNotIn('answer',r[0])
    def test_no_matching_words(self): self.assertEqual(self.retriever.search('',5),[])
    def test_release_gate_intact(self):
        gate=json.loads((ROOT/'reports'/'release_gate.json').read_text(encoding='utf-8'))
        self.assertEqual(gate['unresolved_review_count'],84)
        self.assertNotEqual(gate['release_status'],'PRODUCTION_APPROVED')
    def test_corrupt_corpus_rejected(self):
        import tempfile
        rows=[dict(self.retriever.docs[0])]
        rows[0]['text_bn']='tampered'
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'invalid.jsonl'
            path.write_text(json.dumps(rows[0],ensure_ascii=False)+'\n',encoding='utf8')
            with self.assertRaises(ValueError): load_chunks(path)

if __name__=='__main__': unittest.main()
