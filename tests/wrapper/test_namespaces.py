import json
import logging
import pathlib
import rdflib
import unittest
from rdflib import URIRef

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.utils import download_context
from h5rdmtoolbox.wrapper import jsonld
from ontolutils import namespacelib

logger = logging.getLogger('h5rdmtoolbox')

logger.setLevel(logging.DEBUG)

logger.setLevel(logging.DEBUG)
for h in logger.handlers:
    h.setLevel(logging.DEBUG)

__this_dir__ = pathlib.Path(__file__).parent


class TestNamespaces(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_attr_obj_references(self):
        with h5tbx.File() as h5:
            ds = h5.create_dataset('test', data=1,
                                   attrs={'units': 'm/s',
                                          'a number': 3})
            ds.attrs['dsref'] = ds
            d = jsonld.dumpd(
                h5,
                compact=True,
                context={'units': namespacelib.M4I.hasUnit,
                         'local': '_:'}
            )
            self.assertIsInstance(d, dict)
            graph_data = sorted(d['@graph'], key=lambda x: x['@id'])
            self.assertEqual(graph_data[1]['a number'], "3")
            dd = json.loads(json.dumps(d))
            graph_data = sorted(d['@graph'], key=lambda x: x['@id'])
            self.assertEqual(graph_data[1]['a number'], "3")

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
        cm = rdflib.Graph().parse(location=f, format='json-ld')
        print(len(cm))
        print(cm.serialize(format='json-ld'))
        for s, p, o in cm:
            print(s, p, o)
