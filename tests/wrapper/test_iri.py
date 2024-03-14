import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import consts
from h5rdmtoolbox import use
from ontolutils.namespacelib import M4I, OBO


class TestIRI(unittest.TestCase):

    def setUp(self) -> None:
        """setup"""
        use(None)

    def test_group_predicate(self):
        with h5tbx.File() as h5:
            grp = h5.create_group('has_contact')
            # assign parent group
            grp.iri.predicate = 'https://schema.org/author'
            grp.iri.subject = 'http://xmlns.com/foaf/0.1/Person'
            print(grp.iri.subject)

            from h5rdmtoolbox import jsonld

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
            h5.attrs['title', 'hasTitle'] = 'test'
            self.assertEqual(h5.iri['title'].predicate, 'hasTitle')

        with h5tbx.File() as h5:
            h5.attrs['title'] = 'test'
            self.assertEqual(h5.iri['title'].predicate, None)
            h5.attrs['title', None] = 'test2'
            self.assertEqual(len(h5.attrs[consts.IRI_PREDICATE_ATTR_NAME]), 1)
            h5.attrs['title', 'hasTitle'] = 'test2'
            self.assertEqual(len(h5.attrs[consts.IRI_PREDICATE_ATTR_NAME]), 2)
            self.assertEqual(h5.iri['title'].predicate, 'hasTitle')

    def test_multiple_subjects_or_objects(self):
        with h5tbx.File() as h5:
            h5.attrs['title', 'hasTitle'] = 'test'

            h5.iri['title'].object = 'first object'
            self.assertEqual(h5.attrs['title'], 'test')
            self.assertEqual(h5.iri['title'].object, 'first object')
            h5.iri['title'].object = 'overwritten object'
            self.assertEqual(h5.attrs['title'], 'test')
            self.assertEqual(h5.iri['title'].object, 'overwritten object')

            h5.iri['title'].object = ['one', 'two']
            self.assertEqual(h5.attrs['title'], 'test')
            self.assertEqual(h5.iri['title'].object, ['one', 'two'])
            h5.iri['title'].append_object('three')
            self.assertEqual(h5.iri['title'].object, ['one', 'two', 'three'])

            h5['/'].iri.subject = 'is group'
            self.assertEqual(h5.iri.subject, 'is group')

            h5['/'].iri.subject = 'is root group'
            self.assertEqual(h5.iri.subject, 'is root group')

            h5['/'].iri.append_subject('is group')
            self.assertEqual(h5.iri.subject, ['is root group', 'is group'])

            h5['/'].iri.subject = ['root', 'group']
            self.assertEqual(h5.iri.subject, ['root', 'group'])

    def test_set_single_PSO(self):
        """IRI can be assigned to attributes. A protected attribute IRI is created for each dataset or groups"""

        with h5tbx.File() as h5:
            h5.create_dataset('ds', data=1)
            h5.ds.attrs.create('quantity_kind',
                               data='velocity',
                               predicate=M4I.hasKindOfQuantity,
                               object='https://qudt.org/vocab/quantitykind/Velocity')
            # self.assertIsInstance(h5.ds.iri.predicate, rdflib.URIRef)
            self.assertEqual(str(h5.ds.iri.predicate['quantity_kind']), str(M4I.hasKindOfQuantity))
            self.assertIsInstance(h5.ds.iri.object['quantity_kind'], str)
            self.assertEqual(str(h5.ds.iri.object['quantity_kind']), 'https://qudt.org/vocab/quantitykind/Velocity')

            h5.ds.attrs['units'] = 'm/s'
            h5.ds.iri['units'].predicate = M4I.hasUnit
            h5.ds.iri['units'].object = 'https://qudt.org/vocab/unit/M-PER-SEC'
            self.assertEqual(str(h5.ds.iri.predicate['units']), str(M4I.hasUnit))
            self.assertEqual(str(h5.ds.iri.object['units']), 'https://qudt.org/vocab/unit/M-PER-SEC')

        with h5tbx.File(h5.hdf_filename) as h5:
            self.assertIsInstance(h5.ds.iri.predicate['quantity_kind'], str)
            self.assertEqual(str(h5.ds.iri.predicate['quantity_kind']), str(M4I.hasKindOfQuantity))
            self.assertIsInstance(h5.ds.iri.object['quantity_kind'], str)
            self.assertEqual(str(h5.ds.iri.object['quantity_kind']), 'https://qudt.org/vocab/quantitykind/Velocity')

        with h5tbx.File() as h5:
            from rdflib.namespace import FOAF

            grp = h5.create_group('contact_person')
            grp.iri.subject = FOAF.Person

            method_grp = h5.create_group('a_method')
            method_grp.iri.subject = M4I.Method
            method_grp.attrs['has_participants', OBO.RO_0000057] = h5['contact_person']  # has participants

            self.assertEqual(method_grp.attrs['has_participants'], h5['contact_person'])

            grp.attrs['arbitrary'] = 'arbitrary'
            self.assertEqual(grp.iri.predicate.get('arbitrary', 'invalid'), 'invalid')

            with self.assertRaises(KeyError):
                grp.iri.predicate['firstName'] = FOAF.firstName
            with self.assertRaises(KeyError):
                grp.iri.predicate['lastName'] = FOAF.lastName
            grp.attrs['firstName'] = 'John'
            grp.iri.predicate['firstName'] = FOAF.firstName
            self.assertEqual(grp.attrs['firstName'], 'John')
            self.assertEqual(grp.iri.predicate['firstName'], str(FOAF.firstName))
            self.assertIsInstance(grp.iri.predicate['firstName'], str)

            self.assertTrue(grp.iri == FOAF.Person)
            self.assertTrue(grp.iri.subject == str(FOAF.Person))

        with h5tbx.File() as h5:
            grp = h5.create_group('contact_person')
            grp.iri.subject = FOAF.Person
            grp.attrs['firstName', FOAF.firstName] = 'John'
            grp.attrs['lastName', FOAF.lastName] = 'Doe'

            self.assertEqual(grp.attrs['firstName'], 'John')
            self.assertEqual(grp.iri, FOAF.Person)
            self.assertEqual(grp.iri['firstName'].predicate, str(FOAF.firstName))
            self.assertEqual(grp.iri['lastName'].predicate, str(FOAF.lastName))

            grp.iri.subject = [FOAF.Person,
                               'http://w3id.org/nfdi4ing/metadata4ing#ContactPerson']
            self.assertTrue(str(FOAF.Person) in grp.iri.subject)
            self.assertTrue('http://w3id.org/nfdi4ing/metadata4ing#ContactPerson' in grp.iri.subject)
