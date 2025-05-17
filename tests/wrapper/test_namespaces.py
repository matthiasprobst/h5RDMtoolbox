import json
import logging
import pathlib
import unittest

import rdflib
from ontolutils import namespacelib
from rdflib import URIRef

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.utils import download_context

logger = logging.getLogger('h5rdmtoolbox')

logger.setLevel(logging.DEBUG)
for h in logger.handlers:
    h.setLevel(logging.DEBUG)

__this_dir__ = pathlib.Path(__file__).parent


class TestNamespaces(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_download_context(self):
        code_meta_context = download_context(
            'https://raw.githubusercontent.com/codemeta/codemeta/2.0/codemeta.jsonld').to_dict()
        self.assertIsInstance(code_meta_context, dict)
        self.assertEqual(code_meta_context['type'], "@type")
        self.assertEqual(code_meta_context['id'], "@id")
        self.assertEqual(code_meta_context['schema'], "http://schema.org/")
        self.assertEqual(code_meta_context['codemeta'], "https://codemeta.github.io/terms/")

    def test_codemeta(self):
        self.assertIsInstance(namespacelib.SCHEMA.contributor, URIRef)
        f = __this_dir__ / '../../codemeta.json'
        # print(f.resolve().absolute())
        self.assertTrue(f.exists())
        with open(f, 'r', encoding='utf-8') as f:
            codemeta_json_dict = json.load(f)
            cm = rdflib.Graph().parse(data=codemeta_json_dict,
                                      format='json-ld',
                                      compact=False,
                                      context={'schema': 'http://schema.org/'})
