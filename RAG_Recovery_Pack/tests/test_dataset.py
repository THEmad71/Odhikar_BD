import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from search_draft import search
class TestData(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.data=[json.loads(s) for s in (ROOT/'rag_data'/'chunks_DRAFT.jsonl').read_text(encoding='utf8').splitlines() if s]
 def test_47_pages(self):
  self.assertEqual(len(list((ROOT/'source_pages').glob('page_*.txt'))),47)
 def test_all_126_sections(self):
  self.assertEqual(set(x['section'] for x in self.data),set(range(1,127)))
 def test_no_approved_chunks(self):
  self.assertTrue(all(not x['production_approved'] and x['verification_state'].startswith('DRAFT') for x in self.data))
 def test_section_page_provenance(self):
  for c in self.data:
   self.assertTrue(1<=c['pdf_page_start']<=c['pdf_page_end']<=47)
   self.assertEqual(hashlib.sha256(c['text_bn'].encode()).hexdigest(),c['text_sha256'])
 def test_pending_audit_not_silently_cleared(self):
  gate=json.loads((ROOT/'reports'/'release_gate.json').read_text(encoding='utf8'))
  self.assertEqual(gate['release_status'],'BLOCKED_NOT_PRODUCTION_RAG_READY')
  self.assertEqual(gate['unresolved_review_count'],84)
 def test_search_has_provenance(self):
  results=search('ড্রাইভিং লাইসেন্স')
  self.assertGreater(len(results),0)
  self.assertIn('pdf_page_start',results[0][1])
if __name__=='__main__':unittest.main()
