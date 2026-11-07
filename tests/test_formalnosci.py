"""Regresja kluczowych zachowań Asystenta Formalności."""
import base64
import json
import os
import sys
import unittest
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'serwer'))
import server


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode('utf-8')


class FormalnosciTests(unittest.TestCase):
    def test_relevant_official_request_is_matched(self):
        query = 'Chcę uzyskać odpis aktu urodzenia dziecka'
        sources = server._formalnosci_sources(query)
        self.assertTrue(server._case_has_relevant_source(query, sources))

    def test_unrelated_request_is_rejected_without_model(self):
        query = 'Jak ugotować naleśniki?'
        sources = server._formalnosci_sources(query)
        self.assertFalse(server._case_has_relevant_source(query, sources))

    def test_offline_plan_uses_official_source_and_is_marked_demo(self):
        query = 'Chcę uzyskać odpis aktu urodzenia dziecka'
        with patch.dict(os.environ, {'DOC_AI_API_KEY': '', 'OPENAI_API_KEY': ''}), patch.object(server, 'k', return_value=None):
            result = server.analizuj_pismo({'mode': 'case_plan', 'text': query})
        self.assertTrue(result['demo'])
        self.assertTrue(result['steps'])
        self.assertTrue(result['sources'])

    @unittest.skipUnless(__import__('importlib').util.find_spec('pymupdf'), 'PyMuPDF is optional')
    def test_several_pdfs_are_sent_as_one_analysis(self):
        import pymupdf as fitz

        def pdf_with(text):
            document = fitz.open()
            page = document.new_page()
            page.insert_text((72, 72), text)
            raw = document.tobytes()
            document.close()
            return raw

        captured = {}
        def fake_open(request, timeout):
            body = json.loads(request.data.decode('utf-8'))
            captured['text'] = body['messages'][1]['content']
            result = {'about': 'Test', 'request': '', 'actions': [], 'deadlines': [], 'documents': [],
                      'consequences': '', 'summary': 'Test', 'excerpts': []}
            return FakeResponse({'model': 'bielik-test', 'choices': [{'message': {'content': json.dumps(result)}}]})

        documents = [
            {'name': 'pierwsze.pdf', 'mime': 'application/pdf', 'data': base64.b64encode(pdf_with('PIERWSZY DOKUMENT zawiera tekst do analizy.')).decode('ascii')},
            {'name': 'drugie.pdf', 'mime': 'application/pdf', 'data': base64.b64encode(pdf_with('DRUGI DOKUMENT również zawiera tekst do analizy.')).decode('ascii')},
        ]
        with patch.dict(os.environ, {
            'DOC_AI_API_KEY': 'test-only', 'DOC_AI_BASE_URL': 'https://fabryka.ai/v1', 'DOC_AI_MODEL': 'bielik-test'
        }), patch.object(server, 'log', lambda _entry: None), patch.object(server.urllib.request, 'urlopen', fake_open):
            result = server.analizuj_pismo({'mode': 'analysis', 'files': documents})

        self.assertEqual(result['summary'], 'Test')
        self.assertIn('PIERWSZY DOKUMENT', captured['text'])
        self.assertIn('DRUGI DOKUMENT', captured['text'])


if __name__ == '__main__':
    unittest.main()
