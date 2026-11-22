import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from qdrant_safe_v2 import corpus_digest, require_quarantine, check_manifest, COLLECTION, MODEL_ID
from hybrid_retriever import load_chunks

class TestQdrantSafeV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs=load_chunks()

    def test_quarantine(self):
        require_quarantine(self.docs)
        self.assertEqual(len(self.docs),138)

    def test_prevent_approved_chunks(self):
        d=[dict(self.docs[0],production_approved=True)]
        with self.assertRaises(ValueError): require_quarantine(d)

    def test_prevent_mutated_content(self):
        d=[dict(self.docs[0],text_bn='altered')]
        with self.assertRaises(ValueError): require_quarantine(d)

    def test_prevent_duplicate_id(self):
        d=[self.docs[0],self.docs[0]]
        with self.assertRaises(ValueError): require_quarantine(d)

    def test_reject_stale_manifest(self):
        m={'collection':COLLECTION,'model_id':MODEL_ID,'corpus_digest':'wrong',
           'chunk_count':len(self.docs),'production_approved':False}
        with self.assertRaises(ValueError): check_manifest(m,self.docs,MODEL_ID)

    def test_reject_model_swap(self):
        m={'collection':COLLECTION,'model_id':'different','corpus_digest':corpus_digest(self.docs),
           'chunk_count':len(self.docs),'production_approved':False}
        with self.assertRaises(ValueError): check_manifest(m,self.docs,MODEL_ID)

    def test_allow_matching_manifest(self):
        m={'collection':COLLECTION,'model_id':MODEL_ID,'corpus_digest':corpus_digest(self.docs),
           'chunk_count':len(self.docs),'production_approved':False}
        check_manifest(m,self.docs,MODEL_ID)

if __name__=='__main__': unittest.main()
