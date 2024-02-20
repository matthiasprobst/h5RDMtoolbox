import json
import pathlib
import rdflib
import unittest
from rdflib import URIRef

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.namespace import CODEMETA, M4I
from h5rdmtoolbox.utils import download_context
from h5rdmtoolbox.wrapper import jsonld

__this_dir__ = pathlib.Path(__file__).parent


class TestNamespaces(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_attr_obj_references(self):
        with h5tbx.File() as h5:
            # del h5.attrs['__h5rdmtoolbox_version__']
            ds = h5.create_dataset('test', data=1,
                                   attrs={'units': 'm/s',
                                          'a number': 3})
            ds.attrs['dsref'] = ds
            d = jsonld.dumpd(
                h5,
                compact=True,
                context={'units': URIRef('http://w3id.org/nfdi4ing/metadata4ing#hasUnit'),
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
        self.assertIsInstance(CODEMETA.contributor, URIRef)
        f = __this_dir__ / '../../codemeta.json'
        print(f.resolve().absolute())
        self.assertTrue(f.exists())
        cm = rdflib.Graph().parse(location=f, format='json-ld')
        print(len(cm))
        print(cm.serialize(format='json-ld'))
        for s, p, o in cm:
            print(s, p, o)
        return

        ref_dict = {
            # "@context": "https://doi.org/10.5063/schema/codemeta-2.0",
            "@type": "SoftwareSourceCode",
            "license": "https://spdx.org/licenses/MIT",
            "codeRepository": "git+https://github.com/matthiasprobst/h5RDMtoolbox.git",
            "name": "h5RDMtoolbox",
            "version": "1.2.2",
            "author": [
                {
                    "@type": "Person",
                    "@id": "https://orcid.org/0000-0001-8729-0482",
                    "givenName": "Matthias",
                    "familyName": "Probst",
                },
                {
                    "@type": "Person",
                    "@id": "https://orcid.org/0000-0002-4116-0065",
                    "givenName": "Lucas",
                    "familyName": "Büttner",
                }
            ]
        }

        with h5tbx.File() as h5:
            del h5.attrs['__h5rdmtoolbox_version__']
            grp = h5.create_group('h5dmtoolbox')
            grp.iri = CODEMETA.SoftwareSourceCode

            grp.attrs['license', CODEMETA.license] = "https://spdx.org/licenses/MIT"
            grp.attrs['codeRepository', CODEMETA.codeRepository] = "git+" \
                                                                   "https://github.com/matthiasprobst/h5RDMtoolbox.git"
            grp.attrs['name', CODEMETA.name] = "h5RDMtoolbox"
            grp.attrs['version', CODEMETA.version] = "1.2.2"

            authors = grp.create_group('author')

            # authors.iri = CODEMETA.author
            author1 = authors.create_group('author1')
            author2 = authors.create_group('author2')

            # use @id, not group name!
            grp.attrs['author', CODEMETA.author] = [
                "https://orcid.org/0000-0001-8729-0482",
                "https://orcid.org/0000-0002-4116-0065"
            ]

            author1.iri = CODEMETA.Person
            author1.attrs['givenName', CODEMETA.givenName] = "Matthias"
            author1.attrs['familyName', CODEMETA.familyName] = "Probst"
            author1.attrs['orcidid', M4I.orcidId] = "https://orcid.org/0000-0001-8729-0482"
            author1.attrs['@id'] = "https://orcid.org/0000-0001-8729-0482"

            author2.iri = CODEMETA.Person
            author2.attrs['givenName', CODEMETA.givenName] = "Lucas"
            author2.attrs['familyName', CODEMETA.familyName] = "Büttner"
            author2.attrs['orcidid', M4I.orcidId] = "https://orcid.org/0000-0002-4116-0065"
            author2.attrs['@id'] = "https://orcid.org/0000-0002-4116-0065"

            code_meta_context = download_context(
                'https://raw.githubusercontent.com/codemeta/codemeta/2.0/codemeta.jsonld').to_dict()
            m4i_context = download_context(
                'https://git.rwth-aachen.de/nfdi4ing/metadata4ing/metadata4ing/-/raw/master/m4i_context.jsonld'
            ).to_dict()
            context = {
                # 'orcidid': 'http://w3id.org/nfdi4ing/metadata4ing#orcidId',
                # 'version': 'http://schema.org/version',
                # 'codeRepository': 'http://schema.org/codeRepository',
                # 'license': 'http://schema.org/license',
                # 'name': 'http://schema.org/name',
                # 'schema': 'http://schema.org/',
                # 'SoftwareSourceCode': 'http://schema.org/SoftwareSourceCode',
                # "@import": "https://w3id.org/nfdi4ing/metadata4ing/m4i_context.jsonld",
                'local': '_:'
            }
            context.update(code_meta_context)
            context.update(m4i_context)

            with open('codemeta_test.json', 'w', encoding='utf-8') as f:
                d = jsonld.dumpd(
                    h5.hdf_filename,
                    compact=True,
                    context=context)

                json.dump(
                    d,
                    f,
                    indent=2,
                    ensure_ascii=False
                )
                # jsonld.dump(h5.hdf_filename,
                #             f,
                #             indent=2,
                #             compact=True,
                #             ensure_ascii=False)

            # pathlib.Path('codemeta_test.json').unlink(missing_ok=True)

            entries = jsonld.dumpd(
                h5.hdf_filename,
                compact=True,
                context={}
            )
            self.assertIsInstance(entries, list)
            self.assertIsInstance(d, list)

            for e in sorted(entries):
                self.assertTrue('@id' in e)

            # _entries = entries.copy()
            #
            # def pop_schema_and_id(_entry):
            #     centry = _entry.copy()
            #     for k, v in _entry.items():
            #         if k == '@id':
            #             if 'orcid' not in v:
            #                 centry.pop(k)
            #                 continue
            #         if 'schema.org' in k:
            #             new_key = k.rsplit('/', 1)[-1]
            #             centry[new_key] = centry.pop(k)
            #         else:
            #             new_key = k
            #         if isinstance(v, str):
            #             if 'schema.org' in v:
            #                 new_value = v.rsplit('/', 1)[-1]
            #                 centry[new_key] = new_value
            #         if isinstance(v, dict):
            #             centry[new_key] = pop_schema_and_id(v)
            #         if isinstance(v, list):
            #             centry[new_key] = [pop_schema_and_id(e) for e in v]
            #     return centry
            #
            # entries = pop_schema_and_id(entries)
            # self.assertDictEqual(entries, ref_dict)
