import unittest
from ontolutils.namespacelib import M4I, OBO
from rdflib import FOAF

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import jsonld
from h5rdmtoolbox import use
from h5rdmtoolbox.wrapper.rdf import RDFError
from h5rdmtoolbox.wrapper.rdf import RDF_PREDICATE_ATTR_NAME


class TestRDF(unittest.TestCase):

    def setUp(self) -> None:
        """setup"""
        use(None)

    def test_rdf_error(self):
        with h5tbx.File() as h5:
            with self.assertRaises(RDFError):
                h5.attrs['title', 'hasTitle'] = 'test'
            h5.attrs['title', FOAF.title] = 'test'
            self.assertIsInstance(h5.rdf['title'].predicate, str)
            self.assertEqual(h5.rdf['title'].predicate, str(FOAF.title))
            h5.attrs['title'] = 'test'
            with self.assertRaises(RDFError):
                h5.rdf['title'].object = 'first object'

            with self.assertRaises(RDFError):
                h5.rdf.subject = 'invalid URI'

            with self.assertRaises(RDFError):
                h5.rdf.subject = ['invalid URI', 'invalid URI 2']

            with self.assertRaises(RDFError):
                h5.rdf.subject = ['invalid URI', 'https://example.org/validURI']
            h5.rdf.subject = 'https://example.org/validURI'
            self.assertEqual(h5.rdf.subject, 'https://example.org/validURI')

            h5.rdf.subject = ['https://example.org/validURI', 'https://example.org/validURI2']
            self.assertEqual(h5.rdf.subject, ['https://example.org/validURI', 'https://example.org/validURI2'])

    def test_group_predicate(self):
        with h5tbx.File() as h5:
            grp = h5.create_group('has_contact')
            # assign parent group
            grp.rdf.predicate = 'https://schema.org/author'
            grp.rdf.subject = 'http://xmlns.com/foaf/0.1/Person'
            print(grp.rdf.subject)

        print(
            jsonld.dumps(
                h5.hdf_filename,
                indent=2,
                context={'m4i': 'http://w3id.org/nfdi4ing/metadata4ing#',
                         'foaf': 'http://xmlns.com/foaf/0.1/',
                         'local': 'http://example.com/',
                         }
            )
        )

    def test_none_value(self):
        with h5tbx.File() as h5:
            h5.attrs['title', 'https://example.org/hasTitle'] = 'test'
            self.assertEqual(h5.rdf['title'].predicate, 'https://example.org/hasTitle')
            # self.assertEqual(h5.rdf['title'].predicate, 'https://example.org/hasTitle')

        with h5tbx.File() as h5:
            h5.attrs['title'] = 'test'
            self.assertEqual(h5.rdf['title'].predicate, None)
            h5.attrs['title', None] = 'test2'
            self.assertEqual(len(h5.attrs.get(RDF_PREDICATE_ATTR_NAME, {})), 0)
            h5.attrs['title', 'https://example.org/hasTitle'] = 'test2'
            self.assertEqual(len(h5.attrs.get(RDF_PREDICATE_ATTR_NAME, None)), 1)
            self.assertEqual(h5.rdf['title'].predicate, 'https://example.org/hasTitle')

    def test_multiple_subjects_or_objects(self):
        with h5tbx.File() as h5:
            h5.attrs['title', 'https://example.org/hasTitle'] = 'test'

            h5.rdf['title'].object = 'https://example.org/object'
            self.assertEqual(h5.attrs['title'], 'test')
            self.assertEqual(h5.rdf['title'].object, 'https://example.org/object')

            h5.rdf['title'].object = 'https://example.org/object2'
            self.assertEqual(h5.rdf['title'].object, 'https://example.org/object2')

            self.assertEqual(h5.attrs['title'], 'test')
            self.assertEqual(h5.rdf['title'].object, 'https://example.org/object2')

            h5.rdf['title'].object = ['https://example.org/objectURI1', 'https://example.org/objectURI2']
            self.assertEqual(h5.attrs['title'], 'test')

            self.assertEqual(h5.rdf['title'].object,
                             ['https://example.org/objectURI1', 'https://example.org/objectURI2'])
            h5.rdf['title'].append_object('https://example.org/objectURI3')
            self.assertListEqual(h5.rdf['title'].object,
                                 ['https://example.org/objectURI1',
                                  'https://example.org/objectURI2',
                                  'https://example.org/objectURI3'])

            h5['/'].rdf.subject = 'https://example.org/is group'
            self.assertEqual(h5.rdf.subject, 'https://example.org/is group')

            h5['/'].rdf.subject = 'https://example.org/is root group'
            self.assertEqual(h5.rdf.subject, 'https://example.org/is root group')

            h5['/'].rdf.append_subject('https://example.org/is group')
            self.assertEqual(h5.rdf.subject, ['https://example.org/is root group',
                                              'https://example.org/is group'])

            h5['/'].rdf.subject = ['https://example.org/is root group 1',
                                   'https://example.org/is group 2']
            self.assertEqual(h5.rdf.subject, ['https://example.org/is root group 1',
                                              'https://example.org/is group 2'])

    def test_set_single_PSO(self):
        """IRI can be assigned to attributes. A protected attribute IRI is created for each dataset or groups"""

        with h5tbx.File() as h5:
            h5.create_dataset('ds', data=1)
            h5.ds.attrs.create('quantity_kind',
                               data='velocity',
                               rdf_predicate=M4I.hasKindOfQuantity,
                               rdf_object='https://qudt.org/vocab/quantitykind/Velocity')
            # self.assertIsInstance(h5.ds.rdf.predicate, rdflib.URIRef)
            self.assertEqual(str(h5.ds.rdf.predicate['quantity_kind']), str(M4I.hasKindOfQuantity))
            self.assertIsInstance(h5.ds.rdf.object['quantity_kind'], str)
            self.assertEqual(str(h5.ds.rdf.object['quantity_kind']), 'https://qudt.org/vocab/quantitykind/Velocity')

            h5.ds.attrs['units'] = 'm/s'
            h5.ds.rdf['units'].predicate = M4I.hasUnit
            h5.ds.rdf['units'].object = 'https://qudt.org/vocab/unit/M-PER-SEC'
            self.assertEqual(str(h5.ds.rdf.predicate['units']), str(M4I.hasUnit))
            self.assertEqual(str(h5.ds.rdf.object['units']), 'https://qudt.org/vocab/unit/M-PER-SEC')

        with h5tbx.File(h5.hdf_filename) as h5:
            self.assertIsInstance(h5.ds.rdf.predicate['quantity_kind'], str)
            self.assertEqual(str(h5.ds.rdf.predicate['quantity_kind']), str(M4I.hasKindOfQuantity))
            self.assertIsInstance(h5.ds.rdf.object['quantity_kind'], str)
            self.assertEqual(str(h5.ds.rdf.object['quantity_kind']), 'https://qudt.org/vocab/quantitykind/Velocity')

        with h5tbx.File() as h5:
            from rdflib.namespace import FOAF

            grp = h5.create_group('contact_person')
            grp.rdf.subject = FOAF.Person

            method_grp = h5.create_group('a_method')
            method_grp.rdf.subject = M4I.Method
            method_grp.attrs['has_participants', OBO.RO_0000057] = h5['contact_person']  # has participants

            self.assertEqual(method_grp.attrs['has_participants'], h5['contact_person'])

            grp.attrs['arbitrary'] = 'arbitrary'
            self.assertEqual(grp.rdf.predicate.get('arbitrary', 'invalid'), 'invalid')

            with self.assertRaises(KeyError):
                grp.rdf.predicate['firstName'] = FOAF.firstName
            with self.assertRaises(KeyError):
                grp.rdf.predicate['lastName'] = FOAF.lastName
            grp.attrs['firstName'] = 'John'
            grp.rdf.predicate['firstName'] = FOAF.firstName
            self.assertEqual(grp.attrs['firstName'], 'John')
            self.assertEqual(grp.rdf.predicate['firstName'], str(FOAF.firstName))
            self.assertIsInstance(grp.rdf.predicate['firstName'], str)

            self.assertTrue(grp.rdf == FOAF.Person)
            self.assertTrue(grp.rdf.subject == str(FOAF.Person))

        with h5tbx.File() as h5:
            grp = h5.create_group('contact_person')
            grp.rdf.subject = FOAF.Person
            grp.attrs['firstName', FOAF.firstName] = 'John'
            grp.attrs['lastName', FOAF.lastName] = 'Doe'

            self.assertEqual(grp.attrs['firstName'], 'John')
            self.assertEqual(grp.rdf, FOAF.Person)
            self.assertEqual(grp.rdf['firstName'].predicate, str(FOAF.firstName))
            self.assertEqual(grp.rdf['lastName'].predicate, str(FOAF.lastName))

            grp.rdf.subject = [FOAF.Person,
                               'http://w3id.org/nfdi4ing/metadata4ing#ContactPerson']
            self.assertTrue(str(FOAF.Person) in grp.rdf.subject)
            self.assertTrue('http://w3id.org/nfdi4ing/metadata4ing#ContactPerson' in grp.rdf.subject)
