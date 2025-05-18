import json
import unittest

import ontolutils
from ontolutils.namespacelib import M4I, OBO
from rdflib import FOAF

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import Attribute
from h5rdmtoolbox import jsonld
from h5rdmtoolbox import use
from h5rdmtoolbox.ld.rdf import RDFError
from h5rdmtoolbox.ld.rdf import RDF_PREDICATE_ATTR_NAME
from h5rdmtoolbox.wrapper.h5attr import AttrDescriptionError


class TestRDF(unittest.TestCase):

    def setUp(self) -> None:
        """setup"""
        use(None)

    def test_RDF(self):
        rdfobj = Attribute('0000-0001-8729-0482', rdf_object='https://orcid.org/0000-0001-8729-0482')
        self.assertEqual(rdfobj.value, '0000-0001-8729-0482')
        self.assertEqual(rdfobj.rdf_predicate, None)
        self.assertEqual(rdfobj.rdf_object, 'https://orcid.org/0000-0001-8729-0482')

        with self.assertRaises(AttrDescriptionError):
            Attribute('0000-0001-8729-0482', rdf_predicate='000-0001-8729-0482')

        with h5tbx.File(mode='w') as h5:
            with self.assertRaises(KeyError):
                h5.rdf.type123 = 'https://example.org/validURI'
            with self.assertRaises(KeyError):
                h5.rdf['not_existing'].predicate = 'https://example.org/notExisting'
            h5.attrs['orcid', M4I.orcidId] = rdfobj
            self.assertEqual(h5.rdf.object['orcid'], 'https://orcid.org/0000-0001-8729-0482')

        self.assertEqual(rdfobj.__repr__(),
                         'Attribute(0000-0001-8729-0482, ' \
                         'rdf_object=https://orcid.org/0000-0001-8729-0482)')

    def test_Attribute(self):
        with h5tbx.File() as h5:
            h5.attrs['title'] = Attribute(
                value="test",
                frdf_object="https://example.org/hasTitle",
            )
            self.assertEqual(h5.frdf['title'].object, "https://example.org/hasTitle")
            self.assertEqual(h5.rdf['title'].object, None)

        with h5tbx.File() as h5:
            h5.attrs['title'] = Attribute(
                value="test",
                rdf_object="https://example.org/hasTitle",
            )
            self.assertEqual(h5.rdf['title'].object, "https://example.org/hasTitle")
            self.assertEqual(h5.frdf['title'].object, None)

        with h5tbx.File() as h5:
            with self.assertRaises(ValueError):
                h5.attrs['title'] = Attribute(
                    value="test",
                    rdf_object="https://example.org/hasTitle",
                    frdf_object="https://example.org/hasTitle",
                )

    def test_rdf_special_values(self):
        """e.g. lists, ..."""
        with h5tbx.File() as h5:
            h5.attrs['flags'] = Attribute([1, 2, 3], rdf_predicate='https://example.org/hasFlags')
            self.assertEqual(h5.rdf['flags'].predicate, 'https://example.org/hasFlags')
            self.assertListEqual(list(h5.attrs['flags']), [1, 2, 3])

        with h5tbx.File() as h5:
            h5.attrs['flags'] = Attribute({'valid': 1, 'invalid': 2}, rdf_predicate='https://example.org/hasFlags')
            self.assertEqual(h5.rdf['flags'].predicate, 'https://example.org/hasFlags')
            self.assertDictEqual(h5.attrs['flags'], {'valid': 1, 'invalid': 2})

    def test_rdf_object_thing(self):
        """A RDF object can be an URI or RDF object or a ontolutils.Thing object.
        Idea behind it is to assign complex object through a single attribute, like a standard names that
        are defined in a standard name table and have no distinct IRI themselves
        """

        with h5tbx.File(mode='w') as h5:
            from ssnolib import SSNO
            ds = h5.create_dataset('u', data=4.5)
            # ds.attrs['standard_name', SSNO.hasStandardName] = 'x_velocity'
            ds.attrs['standard_name', SSNO.hasStandardName] = 'x_velocity'
            ds.rdf.object['standard_name'] = ontolutils.Thing(label='x_velocity')
            print(ds.rdf.object['standard_name'])
            h5.dumps()

    def test_rdf_error(self):
        with h5tbx.File() as h5:
            with self.assertRaises(RDFError):
                h5.attrs['title', 'hasTitle'] = 'test'
            h5.attrs['title', FOAF.title] = 'test'
            self.assertIsInstance(h5.rdf['title'].predicate, str)
            self.assertEqual(h5.rdf['title'].predicate, str(FOAF.title))

            with self.assertRaises(RDFError):
                h5.attrs['titles', [FOAF.title, FOAF.member]] = 'titles'

            h5.attrs['title'] = 'test'
            with self.assertRaises(RDFError):
                h5.rdf['title'].object = 'first object'

            with self.assertRaises(RDFError):
                # not a valid URI
                h5.rdf.subject = 'invalid URI'

            with self.assertRaises(TypeError):
                # a list is not allowed
                h5.rdf.subject = ['invalid URI', 'invalid URI 2']

            with self.assertRaises(RDFError):
                h5.rdf.type = ['invalid URI', 'invalid URI 2']

            with self.assertRaises(RDFError):
                h5.rdf.type = ['invalid URI', 'https://example.org/validURI']

            h5.rdf.subject = 'https://example.org/validURI'
            self.assertEqual(h5.rdf.subject, 'https://example.org/validURI')

            h5.rdf.type = ['https://example.org/validURI', 'https://example.org/validURI2']
            self.assertEqual(h5.rdf.type, ['https://example.org/validURI', 'https://example.org/validURI2'])

            # note, that the following will not overwrite, but append the value:
            h5.rdf.type = 'https://example.org/validURI3'
            self.assertEqual(sorted(h5.rdf.type),
                             sorted(['https://example.org/validURI',
                                     'https://example.org/validURI2',
                                     'https://example.org/validURI3']))

            # the list of values are unique, so adding the same URI will not change the list
            h5.rdf.type = 'https://example.org/validURI3'
            self.assertEqual(sorted(h5.rdf.type),
                             sorted(['https://example.org/validURI',
                                     'https://example.org/validURI2',
                                     'https://example.org/validURI3']))

    def test_group_predicate(self):
        with h5tbx.File() as h5:
            grp = h5.create_group('has_contact')
            # assign parent group
            with self.assertRaises(TypeError):
                grp.rdf.predicate = ['1.4', ]

            grp.rdf.predicate = 'https://schema.org/author'
            self.assertEqual(grp.rdf.predicate[None], 'https://schema.org/author')

            del grp.rdf.predicate
            self.assertEqual(grp.rdf.predicate[None], None)

            del grp.rdf.predicate
            self.assertEqual(grp.rdf.predicate[None], None)

            grp.rdf.predicate = 'https://schema.org/author'
            self.assertEqual(grp.rdf.predicate[None], 'https://schema.org/author')

            grp.rdf.subject = 'http://xmlns.com/foaf/0.1/Person'

        print(
            jsonld.dumps(
                h5.hdf_filename,
                indent=2,
                context={'m4i': 'http://w3id.org/nfdi4ing/metadata4ing#',
                         'foaf': 'http://xmlns.com/foaf/0.1/',
                         'local': 'http://example.com/'}
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

    def test_multiple_objects(self):
        with h5tbx.File() as h5:
            h5.attrs["contacts"] = ["john", "jane"]
            h5.frdf["contacts"].predicate = "https://example.org/hasContacts"
            h5.frdf["contacts"].object = ["https://example.org/john", "https://example.org/jane"]
            self.assertEqual(h5.frdf["contacts"].object, ["https://example.org/john", "https://example.org/jane"])

    def test_assign_id_to_hdf_file(self):
        with h5tbx.File() as h5:
            h5.frdf.subject = "https://example.org/123123"
            h5.frdf.type = "https://example.org/HDFFile"
            self.assertEqual('\n<https://example.org/123123> a <https://example.org/HDFFile> .\n\n',
                             h5.serialize(fmt="ttl", structural=False))

            expected_ttl = """@prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://example.org/123123> a hdf:File,
        <https://example.org/HDFFile> ;
    hdf:rootGroup [ a hdf:Group ;
            hdf:name "/"^^xsd:string ] .

"""
            self.assertEqual(h5.serialize(fmt="ttl", structural=True), expected_ttl)

    def test_multiple_objects_2(self):
        person1 = ontolutils.Thing(label="John Doe")
        person2 = ontolutils.Thing(label="Jane Wane")
        with h5tbx.File() as h5:
            h5.attrs["contacts"] = ["john", "jane"]
            h5.frdf["contacts"].predicate = "https://example.org/hasContacts"
            h5.frdf["contacts"].object = person1
            h5.frdf["contacts"].object = person2
            print(h5.serialize(fmt="ttl", structural=False))

    def test_multiple_types_or_objects(self):
        with h5tbx.File() as h5:
            h5.attrs['title', 'https://example.org/hasTitle'] = 'test'

            self.assertEqual(h5.rdf['title'].object, None)

            with self.assertRaises(RDFError):
                h5.rdf['title'].object = 1.34

            self.assertEqual(h5.rdf.parent, h5)

            h5.rdf['title'].object = 'https://example.org/object'
            self.assertEqual(h5.attrs['title'], 'test')
            self.assertEqual(h5.rdf['title'].object, 'https://example.org/object')

            h5.rdf['title'].object = 'https://example.org/object2'
            self.assertEqual(h5.rdf['title'].object, ['https://example.org/object', 'https://example.org/object2'])
            self.assertEqual(h5.attrs['title'], 'test')
            self.assertEqual(h5.rdf['title'].object, ['https://example.org/object', 'https://example.org/object2'])

        with h5tbx.File() as h5:
            h5.attrs['title', 'https://example.org/hasTitle'] = 'test'
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

    def test_delete_rdf_properties(self):
        with h5tbx.File() as h5:
            h5['/'].rdf.subject = 'https://example.org/is root group'
            del h5['/'].rdf.subject
            self.assertEqual(h5.rdf.subject, None)

            h5['/'].rdf.type = 'https://example.org/is root group'
            del h5['/'].rdf.type
            self.assertEqual(h5.rdf.type, None)

            h5['/'].rdf.type = 'https://example.org/is root group'
            h5['/'].rdf.pop_type('https://example.org/is root group')
            self.assertEqual(h5.rdf.type, None)

            h5['/'].rdf.type = ['https://example.org/1', 'https://example.org/2', 'https://example.org/3']
            h5['/'].rdf.pop_type('https://example.org/1')
            self.assertEqual(h5.rdf.type, ['https://example.org/2', 'https://example.org/3'])
            h5['/'].rdf.pop_type('https://example.org/3')
            self.assertEqual(h5.rdf.type, 'https://example.org/2')

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

            self.assertEqual(method_grp.attrs['has_participants'], h5['contact_person'].name)

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

            grp.rdf.type = [FOAF.Person,
                            'http://w3id.org/nfdi4ing/metadata4ing#ContactPerson']
            self.assertTrue(str(FOAF.Person) in grp.rdf.type)
            self.assertTrue('http://w3id.org/nfdi4ing/metadata4ing#ContactPerson' in grp.rdf.type)

    def test_set_type(self):
        with h5tbx.File() as h5:
            h5.create_group('contact_person')
            h5.contact_person.rdf.type = FOAF.Person
            self.assertEqual(h5.contact_person.rdf.type, str(FOAF.Person))
            h5.contact_person.rdf.type = 'http://w3id.org/nfdi4ing/metadata4ing#ContactPerson'
            self.assertListEqual(sorted(h5.contact_person.rdf.type),
                                 sorted([str(FOAF.Person), 'http://w3id.org/nfdi4ing/metadata4ing#ContactPerson']))

            h5.contact_person.rdf.type = [str(FOAF.Person), 'http://w3id.org/nfdi4ing/metadata4ing#ContactPerson']
            self.assertListEqual(sorted(h5.contact_person.rdf.type),
                                 sorted([str(FOAF.Person), 'http://w3id.org/nfdi4ing/metadata4ing#ContactPerson']))

        with h5tbx.File() as h5:
            h5.create_group('contact_person')
            h5.contact_person.rdf.type = FOAF.Person

            h5.contact_person.rdf.type = [str(FOAF.Person), 'http://w3id.org/nfdi4ing/metadata4ing#ContactPerson']
            self.assertListEqual(sorted(h5.contact_person.rdf.type),
                                 sorted([str(FOAF.Person), 'http://w3id.org/nfdi4ing/metadata4ing#ContactPerson']))

            h5.contact_person.rdf.pop_type('http://w3id.org/nfdi4ing/metadata4ing#ContactPerson')
            self.assertEqual(h5.contact_person.rdf.type, str(FOAF.Person))

            h5.contact_person.rdf.pop_type(str(FOAF.Person))
            self.assertEqual(h5.contact_person.rdf.type, None)

    def test_rdf_find(self):
        with h5tbx.File() as h5:
            h5.create_dataset('ds', data=1)
            h5.ds.attrs['quantity_kind', M4I.hasKindOfQuantity] = 'x_velocity'
            h5.ds.rdf.object['quantity_kind'] = 'https://qudt.org/vocab/quantitykind/Velocity'
            h5.ds.attrs['units', M4I.hasUnit] = 'm/s'

            self.assertEqual(sorted(h5.ds.rdf.predicate.keys()),
                             sorted(['quantity_kind', 'units']))
            self.assertDictEqual(dict(h5.ds.rdf.predicate.items()),
                                 {'quantity_kind': str(M4I.hasKindOfQuantity),
                                  'units': str(M4I.hasUnit)})
            for k in h5.ds.rdf.predicate:
                self.assertIsInstance(k, str)
                self.assertIn(k, ['quantity_kind', 'units'])

            ds = h5.create_dataset('sub_grp/another_dataset', data=2)
            ds.attrs['quantity_kind', M4I.hasKindOfQuantity] = 'y_velocity'
            h5.sub_grp.attrs['random', M4I.hasKindOfQuantity] = 'y_velocity'

            grp = h5.create_group('contact_person')
            grp.rdf.subject = 'http://orcid.org/XXXX-XXXX-XXXX-XXXX'
            grp.rdf.type = FOAF.Person
            grp.attrs['firstName', FOAF.firstName] = 'John'

            grp = h5.create_group('sub_grp/another_sub/another_person')
            grp.rdf.type = FOAF.Person

            person_res = sorted(h5.sub_grp.another_sub.rdf.find(rdf_type=FOAF.Person))
            self.assertEqual(person_res[0].name, '/sub_grp/another_sub/another_person')

            person_res = sorted(h5.rdf.find(rdf_predicate=FOAF.firstName))
            self.assertEqual(person_res[0].name, '/contact_person')

            person_res = sorted(h5.rdf.find(rdf_type=FOAF.Person))
            self.assertEqual(person_res[0].name, '/contact_person')
            self.assertEqual(person_res[1].name, '/sub_grp/another_sub/another_person')

            person_res = sorted(h5.rdf.find(rdf_type=FOAF.Person, recursive=False))
            self.assertEqual(len(person_res), 0)
            person_res = sorted(h5.contact_person.rdf.find(rdf_type=FOAF.Person, recursive=False))
            self.assertEqual(person_res[0].name, '/contact_person')

            person_res = sorted(h5.rdf.find(rdf_predicate=FOAF.firstName, rdf_type=FOAF.Person))
            self.assertEqual(person_res[0].name, '/contact_person')

            person_res = sorted(h5.rdf.find(rdf_predicate=FOAF.firstName, rdf_type=FOAF.Person, recursive=False))
            self.assertEqual(len(person_res), 0)

            person_res = h5.rdf.find(rdf_subject='http://orcid.org/XXXX-XXXX-XXXX-XXXX', recursive=False)
            self.assertEqual(len(person_res), 0)

            person_res = h5.rdf.find(rdf_subject='http://orcid.org/XXXX-XXXX-XXXX-XXXX', recursive=True)
            self.assertEqual(len(person_res), 1)
            self.assertEqual(person_res[0].name, '/contact_person')

    def test_find_object(self):
        with h5tbx.File() as h5:
            h5.attrs['title'] = 'test'
            h5.rdf['title'].object = 'https://example.org/object'

            res = h5.rdf.find(rdf_object='https://example.org/object')

            self.assertEqual(len(res), 1)

    def test_definition(self):
        with h5tbx.File() as h5:
            h5.attrs['title'] = 'test'
            h5.rdf['title'].definition = 'This is the title of the dataset'
            self.assertEqual(h5.rdf['title'].definition, 'This is the title of the dataset')

            h5.attrs['name'] = h5tbx.Attribute('Matthias', definition='This is the name of the person to contact')
            self.assertEqual(h5.rdf['name'].definition, 'This is the name of the person to contact')

            h5.dumps()

    def test_rm_attr_with_rdf(self):
        with h5tbx.File() as h5:
            h5.attrs['test', 'https://example.org/test'] = 'test'
            test_rdf = h5.rdf['test'].predicate
            self.assertEqual(test_rdf, 'https://example.org/test')
            self.assertEqual(json.loads(h5.attrs.raw.get(h5.rdf.predicate.IRI_ATTR_NAME, None)),
                             {'test': 'https://example.org/test'})
            del h5.attrs['test']
            self.assertEqual(json.loads(h5.attrs.raw.get(h5.rdf.predicate.IRI_ATTR_NAME, None)), {})

    def test_using_plain_jsonld(self):
        sn_xvel = """{
            "@context": {
                "ssno": "https://matthiasprobst.github.io/ssno#",
                "ex": "https://example.org/"
            },
            "@id": "https://www.example.org/standard_name/x_velocity",
            "@type": "ssno:StandardName",
            "ssno:standardName": "x_velocity",
            "ssno:unit": "http://qudt.org/vocab/unit/M-PER-SEC",
            "ssno:description": "X-component of a velocity vector.",
            "ssno:standardNameTable": "https://doi.org/10.5281/zenodo.122658"
        }"""
        with h5tbx.File() as h5:
            h5.create_dataset("u", data=[1, 2, 3], attrs={"standard_name": "x_velocity"})
            h5.u.rdf["standard_name"].predicate = "https://matthiasprobst.github.io/ssno#hasStandardName"
            h5.u.rdf["standard_name"].object = sn_xvel
            # from ssnolib import StandardName
            # h5.u.rdf["standard_name"].object = StandardName(standard_name="x_velocity", unit="m/s")
            h5.dump(False)
            h5jld = h5.dump_jsonld(indent=2, structural=False,
                                   context={"ssno": "https://matthiasprobst.github.io/ssno#",
                                            "ex": "https://example.org/"})
            h5jld_dict = json.loads(h5jld)
            self.assertDictEqual(
                h5jld_dict["@context"],
                {"rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                 "ssno": "https://matthiasprobst.github.io/ssno#",
                 "ex": "https://example.org/"}
            )
