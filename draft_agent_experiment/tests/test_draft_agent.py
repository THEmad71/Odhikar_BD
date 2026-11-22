import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import draft_agent as a

class TestDraftAgent(unittest.TestCase):
    def test_gate(self): a.assert_gate_blocked()
    def test_valid_question(self): self.assertEqual(a.validate_question('  abc '), 'abc')
    def test_empty_rejected(self):
        with self.assertRaises(ValueError): a.validate_question('  ')
    def test_penalty_refusal_without_index(self):
        x=a.retrieve({'query':'fine koto taka?'})
        self.assertEqual(x['blocked_reason'], 'penalty_or_punishment_query')
        self.assertEqual(a.guard(x), 'refuse')
    def test_no_hit_refusal(self): self.assertEqual(a.guard({'hits':[]}), 'refuse')
    def test_gemini_consent_required(self):
        r=a.gemini({'mode':'gemini','hits':[{'id':'A'}], 'allow_external_draft':False})
        self.assertIn('blocked',r['answer'])
    def test_gemini_key_required(self):
        with patch.dict('os.environ', {'GEMINI_API_KEY':''}):
            r=a.gemini({'mode':'gemini','hits':[], 'allow_external_draft':True})
        self.assertIn('missing',r['answer'])
    def test_preview_citation(self):
        rows=[dict(id='RTA2018-S004-P01',section=4,pdf_page_start=8,pdf_page_end=9,source_pdf='gazette.pdf',
                   verification_state='DRAFT_UNVERIFIED_FULL_TEXT',text_bn='উদাহরণ তথ্য',production_approved=False)]
        r=a.preview({'hits':rows})
        self.assertIn('DRAFT_ONLY',r['answer'])
        self.assertEqual(r['citations'][0]['section'],4)
    def test_real_retrieval(self):
        result=a.retrieve({'query':'license chara gari chalano jabe?'})
        self.assertTrue(result.get('hits'))
        self.assertEqual(result['hits'][0]['section'],4)
        self.assertTrue(all(h['production_approved'] is False for h in result['hits']))

if __name__=='__main__': unittest.main()
