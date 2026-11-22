import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from banglish_retriever import BanglishRetriever, expand_query

class TestBanglishRetriever(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retriever=BanglishRetriever()
    def test_license_expansion(self):
        self.assertIn('লাইসেন্স',expand_query('license chara'))
    def test_preserves_unknown_words(self):
        self.assertIn('xyzabc',expand_query('xyzabc license'))
    def test_empty(self):
        self.assertEqual(expand_query(''), '')
    def test_draft_protection(self):
        self.assertTrue(all(r['production_approved'] is False for r in self.retriever.search('license chara gari',5)))
    def test_citation(self):
        self.assertTrue(all(r['source_pdf'] and r['pdf_page_start'] for r in self.retriever.search('driving license',3)))
    def test_explicit_section(self):
        self.assertEqual(self.retriever.search('ধারা ৪ ড্রাইভিং লাইসেন্স')[0]['section'],4)
if __name__=='__main__':unittest.main()
