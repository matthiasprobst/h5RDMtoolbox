import rdflib
import unittest
from rdflib import URIRef

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import use
from h5rdmtoolbox.namespace import M4I, OBO


class TestIRI(unittest.TestCase):

    def setUp(self) -> None:
        """setup"""
        use(None)

    def test_multiple_subjects_or_objects(self):
        with h5tbx.File() as h5:
            h5.attrs['title', 'hasTitle'] = 'test'

            h5.iri['title'].object = 'first object'
            self.assertEqual(h5.attrs['title'], 'test')
            self.assertEqual(h5.iri['title'].object, URIRef('first object'))
            h5.iri['title'].object = 'overwritten object'
            self.assertEqual(h5.attrs['title'], 'test')
            self.assertEqual(h5.iri['title'].object, URIRef('overwritten object'))

            h5.iri['title'].object = ['one', 'two']
            self.assertEqual(h5.attrs['title'], 'test')
            self.assertEqual(h5.iri['title'].object, [URIRef('one'), URIRef('two')])
            h5.iri['title'].append_object('three')
            self.assertEqual(h5.iri['title'].object, [URIRef('one'), URIRef('two'), URIRef('three')])

            h5['/'].iri.subject = 'is group'
            self.assertEqual(h5.iri.subject, URIRef('is group'))

            h5['/'].iri.subject = 'is root group'
            self.assertEqual(h5.iri.subject, URIRef('is root group'))

            h5['/'].iri.append_subject('is group')
            self.assertEqual(h5.iri.subject, [URIRef('is root group'), URIRef('is group')])

            h5['/'].iri.subject = ['root', 'group']
            self.assertEqual(h5.iri.subject, [URIRef('root'), URIRef('group')])

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
            self.assertIsInstance(h5.ds.iri.object['quantity_kind'], rdflib.URIRef)
            self.assertEqual(str(h5.ds.iri.object['quantity_kind']), 'https://qudt.org/vocab/quantitykind/Velocity')

            h5.ds.attrs['units'] = 'm/s'
            h5.ds.iri['units'].predicate = M4I.hasUnit
            h5.ds.iri['units'].object = 'https://qudt.org/vocab/unit/M-PER-SEC'
            self.assertEqual(str(h5.ds.iri.predicate['units']), str(M4I.hasUnit))
            self.assertEqual(str(h5.ds.iri.object['units']), 'https://qudt.org/vocab/unit/M-PER-SEC')

        with h5tbx.File(h5.hdf_filename) as h5:
            self.assertIsInstance(h5.ds.iri.predicate['quantity_kind'], rdflib.URIRef)
            self.assertEqual(str(h5.ds.iri.predicate['quantity_kind']), str(M4I.hasKindOfQuantity))
            self.assertIsInstance(h5.ds.iri.object['quantity_kind'], rdflib.URIRef)
            self.assertEqual(str(h5.ds.iri.object['quantity_kind']), 'https://qudt.org/vocab/quantitykind/Velocity')

        with h5tbx.File() as h5:
            from rdflib.namespace import FOAF

            grp = h5.create_group('contact_person')
            grp.iri = FOAF.Person
            grp.iri.subject = FOAF.Person

            method_grp = h5.create_group('a_method')
            method_grp.iri = M4I.Method
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
            self.assertEqual(grp.iri.predicate['firstName'], FOAF.firstName)
            self.assertIsInstance(grp.iri.predicate['firstName'], rdflib.URIRef)

            self.assertTrue(grp.iri == FOAF.Person)

        with h5tbx.File() as h5:
            grp = h5.create_group('contact_person')
            grp.iri = FOAF.Person
            grp.attrs['firstName', FOAF.firstName] = 'John'
            grp.attrs['lastName', FOAF.lastName] = 'Doe'

            self.assertEqual(grp.attrs['firstName'], 'John')
            self.assertEqual(grp.iri, FOAF.Person)
            self.assertEqual(grp.iri['firstName'].predicate, FOAF.firstName)
            self.assertEqual(grp.iri['lastName'].predicate, FOAF.lastName)

            grp.iri = [FOAF.Person,
                       'http://w3id.org/nfdi4ing/metadata4ing#ContactPerson']
            self.assertTrue(FOAF.Person in grp.iri)
            self.assertTrue('http://w3id.org/nfdi4ing/metadata4ing#ContactPerson' in grp.iri)
