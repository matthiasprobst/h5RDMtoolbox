import pathlib

import unittest
from rdflib import URIRef

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.namespace import CODEMETA
from h5rdmtoolbox.wrapper import jsonld


class TestNamespaces(unittest.TestCase):

    def setUp(self) -> None:
        h5tbx.use(None)

    def test_codemeta(self):
        self.assertIsInstance(CODEMETA.contributor, URIRef)

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
            grp.attrs[
                'codeRepository', CODEMETA.codeRepository] = "git+https://github.com/matthiasprobst/h5RDMtoolbox.git"
            grp.attrs['name', CODEMETA.name] = "h5RDMtoolbox"
            grp.attrs['version', CODEMETA.version] = "1.2.2"

            authors = grp.create_group('author')

            # authors.iri = CODEMETA.author
            author1 = authors.create_group('author1')
            author2 = authors.create_group('author2')

            # use @id, not group name!
            grp.attrs['author', CODEMETA.author] = ["https://orcid.org/0000-0001-8729-0482",
                                                    "https://orcid.org/0000-0002-4116-0065"]

            author1.iri = CODEMETA.Person
            author1.attrs['givenName', CODEMETA.givenName] = "Matthias"
            author1.attrs['familyName', CODEMETA.familyName] = "Probst"
            author1.attrs['@id'] = "https://orcid.org/0000-0001-8729-0482"

            author2.iri = CODEMETA.Person
            author2.attrs['givenName', CODEMETA.givenName] = "Lucas"
            author2.attrs['familyName', CODEMETA.familyName] = "Büttner"
            author2.attrs['@id'] = "https://orcid.org/0000-0002-4116-0065"

        # print(jsonld.dumps(h5.hdf_filename, indent=2))
        print(jsonld.dumps(h5.hdf_filename, indent=2, compact=True))

        with open('codemeta_test.json', 'w', encoding='utf-8') as f:
            jsonld.dump(h5.hdf_filename, f, indent=2, compact=True, ensure_ascii=False)

        pathlib.Path('codemeta_test.json').unlink(missing_ok=True)

        entries = jsonld.dumpd(h5.hdf_filename, compact=False)['@graph']
        _entries = entries.copy()

        def pop_schema_and_id(_entry):
            centry = _entry.copy()
            for k, v in _entry.items():
                if k == '@id':
                    if 'orcid' not in v:
                        centry.pop(k)
                        continue
                if 'schema.org' in k:
                    new_key = k.rsplit('/', 1)[-1]
                    centry[new_key] = centry.pop(k)
                else:
                    new_key = k
                if isinstance(v, str):
                    if 'schema.org' in v:
                        new_value = v.rsplit('/', 1)[-1]
                        centry[new_key] = new_value
                if isinstance(v, dict):
                    centry[new_key] = pop_schema_and_id(v)
                if isinstance(v, list):
                    centry[new_key] = [pop_schema_and_id(e) for e in v]
            return centry

        entries = pop_schema_and_id(entries)
        self.assertDictEqual(entries, ref_dict)
