import json
import pathlib
import unittest

import numpy as np
import ontolutils
import rdflib
import ssnolib
from ontolutils import namespaces, urirefs, Thing
from ontolutils.ex import dcat
from ontolutils.namespacelib import M4I
from ontolutils.namespacelib import SCHEMA
from ontolutils.utils.qudt_units import qudt_lookup
from rdflib import DCAT
from rdflib.namespace import SKOS

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import __version__
from h5rdmtoolbox.ld import hdf2jsonld, hdf2ttl
from h5rdmtoolbox.ld import rdf
from h5rdmtoolbox.ld.rdf import RDFError, RDF_FILE_PREDICATE_ATTR_NAME, RDF_TYPE_ATTR_NAME
from h5rdmtoolbox.wrapper import jsonld

logger = h5tbx.logger

__this_dir__ = pathlib.Path(__file__).parent

EXCEPTION_PROPERTIES_NAMESPACES = {
    str(rdflib.OWL),
    str(rdflib.RDF),
    str(rdflib.RDFS),
    str(rdflib.XSD)
}


def _raise_on_blank_nodes(
        ttl,
        exception_properties=None) -> rdflib.Graph:
    """Raises an error if the given RDF file contains blank nodes."""
    if exception_properties is None:
        exception_properties = EXCEPTION_PROPERTIES_NAMESPACES

    temp_graph = rdflib.Graph()
    temp_graph.parse(data=ttl, format='ttl')

    # Check if there are any blank nodes
    has_blank_nodes = any(
        isinstance(term, rdflib.BNode)
        for triple in temp_graph
        for term in triple
    )
    if has_blank_nodes:
        for s, p, o in temp_graph:
            if isinstance(s, rdflib.BNode) or isinstance(p, rdflib.BNode) or isinstance(o, rdflib.BNode):
                # allow all owl properties:
                for ep in exception_properties:
                    if str(p).startswith(ep):
                        break
                else:
                    raise ValueError(f"Blank nodes are not supported: {s}, {p}, {o}")
    return temp_graph


class TestLinkedData(unittest.TestCase):

    def setUp(self):
        LEVEL = 'WARNING'
        logger.setLevel(LEVEL)
        for h in logger.handlers:
            h.setLevel(LEVEL)

    def tearDown(self):
        pathlib.Path('test.hdf').unlink(missing_ok=True)

    def test_dump_type(self):
        with h5tbx.File() as h5:
            h5.attrs["__version__"] = __version__
            h5.create_group("__version__")
            grp = h5.create_group('grp')
            grp.attrs["group_attr"] = 2.4
            grp.rdf.type = 'https://example.org/MyGroup'
            data = json.loads(h5.dump_jsonld(indent=2, file_uri="https://example.org#"))
            graph = data["@graph"]
            version_attr_id = None
            version_group_id = None
            for g in graph:
                if g.get("hdf:name", None) == "__version__" and g.get("@type", None) == "hdf:StringAttribute":
                    version_attr_id = g.get("@id")
                elif g.get("hdf:name", None) == "/__version__" and g.get("@type", None) == "hdf:Group":
                    version_group_id = g.get("@id")
            self.assertTrue(version_attr_id is not None)
            self.assertTrue(version_group_id is not None)
            self.assertNotEqual(version_attr_id, version_group_id)

        # reopen:
        with h5tbx.File(h5.hdf_filename) as h5:
            data_reopened = json.loads(h5.dump_jsonld(indent=2, file_uri="https://example.org#"))

        self.assertDictEqual(
            data, data_reopened
        )

        # reopen2:
        with h5tbx.File(h5.hdf_filename) as h5:
            data_reopened2 = json.loads(h5.dump_jsonld(indent=2, file_uri=None))

        g = rdflib.Graph().parse(data=data_reopened, format='json-ld')
        res = g.query("""PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>
        SELECT ?id
        WHERE {
            ?id a hdf:File .
        }""")
        bindings_reopened = res.bindings

        g = rdflib.Graph().parse(data=data_reopened2, format='json-ld')
        res = g.query("""PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>
        SELECT ?id
        WHERE {
            ?id a hdf:File .
        }""")
        bindings_reopened2 = res.bindings
        self.assertEqual(len(bindings_reopened2), 1)
        self.assertNotEqual(
            bindings_reopened[0][rdflib.Variable("id")],
            bindings_reopened2[0][rdflib.Variable("id")]
        )

    def test_dump_dataset_data_using_serialize_0D_datasets(self):
        with h5tbx.File() as h5:
            ds = h5.create_dataset('ds0', data=5.4, attrs={"units": "m/s"})
            ds.rdf.subject = M4I.NumericalVariable
            h5.create_dataset('ds_str0', data="Hello")
            h5.create_string_dataset('ds_str1', data=["Hello", "World"])
            h5.create_dataset('ds1', data=[1, 2, 3])
            h5.create_dataset('ds2', data=[[1, 2], [3, 4]])
            ttl = h5.serialize(fmt="ttl", skipND=1, file_uri="https://example.org#")
        print(ttl)
        g = rdflib.Graph().parse(data=ttl, format="ttl")
        sparql_str = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>

SELECT ?values
WHERE {
    ?id a hdf:Dataset .
    ?id hdf:name "/ds1" .
    ?id hdf:value ?values .
}
"""
        res = g.query(sparql_str)
        bindings = res.bindings
        self.assertEqual(0, len(bindings))

        _raise_on_blank_nodes(ttl)

    def test_serialize_multiple_types(self):
        with h5tbx.File() as h5:
            h5.rdf.type = [M4I.Tool, 'https://www.wikidata.org/wiki/Q1058834']
        ttl = h5tbx.serialize(h5.hdf_filename, fmt="ttl", structural=False)
        sparql_query = """SELECT ?type
        WHERE {
            ?s a ?type
        }
        """
        g = rdflib.Graph()
        g.parse(data=ttl, format="ttl")
        res = g.query(sparql_query)
        self.assertEqual(
            sorted(b[rdflib.Variable("type")] for b in res.bindings),
            sorted([rdflib.URIRef(uri) for uri in [M4I.Tool, 'https://www.wikidata.org/wiki/Q1058834']])
        )

    def test_dump_dataset_data(self):
        with h5tbx.File() as h5:
            h5.create_dataset('ds0', data=5.4)
            h5.create_dataset('ds_str0', data="Hello")
            h5.create_string_dataset('ds_str1', data=["Hello", "World"])
            h5.create_dataset('ds1', data=[1, 2, 3])
            h5.create_dataset('ds2', data=[[1, 2], [3, 4]])
            ttl = h5.serialize(fmt="ttl", skipND=2)

        g = rdflib.Graph().parse(data=ttl, format="ttl")
        sparql_str = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>

SELECT ?values
WHERE {
    ?id a hdf:Dataset .
    ?id hdf:name "/ds1" .
    ?id hdf:value ?values .
}
"""
        res = g.query(sparql_str)
        bindings = res.bindings
        self.assertEqual('[1, 2, 3]', bindings[0][rdflib.Variable('values')].value)

        sparql_str = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>

SELECT ?values
WHERE {
    ?id a hdf:Dataset .
    ?id hdf:name "/ds_str0" .
    ?id hdf:value ?values .
}
"""
        res = g.query(sparql_str)
        bindings = res.bindings
        self.assertEqual('Hello', bindings[0][rdflib.Variable('values')].value)

        sparql_str = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>

SELECT ?values
WHERE {
    ?id a hdf:Dataset .
    ?id hdf:name "/ds_str1" .
    ?id hdf:value ?values .
}
"""
        res = g.query(sparql_str)
        bindings = res.bindings
        self.assertEqual("['Hello', 'World']", bindings[0][rdflib.Variable('values')].value)

    def test_dump_with_blank_node_iri_base(self):
        with h5tbx.File() as h5:
            h5.attrs["__version__"] = __version__
            jsonld = h5.dump_jsonld(
                file_uri="https://example.org/#",
                context={"local": "https://example.org/#"},
                indent=2
            )
            jsonld_dict = json.loads(jsonld)
            self.assertEqual(jsonld_dict['@context']['local'], 'https://example.org/#')
            found_local = False
            for e in jsonld_dict["@graph"]:
                if e.get("@id", "").startswith("local:"):
                    found_local = True
                    break

            self.assertTrue(found_local)

    #     def test_build_node_list(self):
    #
    #         g = rdflib.Graph()
    #         base_node = rdflib.BNode()
    #         g.add((base_node, rdflib.RDF.type, HDF5.Attribute))
    #         list_node_int = build_node_list(g, [1, 2, 3], use_simple_bnode_value=True, blank_node_iri_base=None)
    #         g.add((base_node, HDF5.value, list_node_int))
    #
    #         with self.assertRaises(TypeError):
    #             build_node_list(g, [1, dict(a='1'), 3], use_simple_bnode_value=True, blank_node_iri_base=None)
    #
    #         print(g.serialize(format='json-ld', indent=2))
    #         sparql_str = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    # PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>
    #
    # SELECT ?item
    # WHERE {
    #     ?id a hdf:Attribute .
    #     ?id hdf:value ?list .
    #     ?list rdf:rest*/rdf:first ?item
    # }"""
    #         qres = g.query(sparql_str)
    #         list_values = [int(row[0]) for row in qres]
    #         self.assertEqual(list_values, [1, 2, 3])
    #
    #         g = rdflib.Graph()
    #         base_node = rdflib.BNode()
    #         g.add((base_node, rdflib.RDF.type, HDF5.Attribute))
    #         list_node = build_node_list(g, [1, 'str', 3.4, True], use_simple_bnode_value=True, blank_node_iri_base=None)
    #         g.add((base_node, HDF5.value, list_node))
    #
    #         print(g.serialize(format='json-ld', indent=2))
    #         sparql_str = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    # PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>
    #
    # SELECT ?item
    # WHERE {
    #     ?id a hdf:Attribute .
    #     ?id hdf:value ?list .
    #     ?list rdf:rest*/rdf:first ?item
    # }"""
    #         qres = g.query(sparql_str)
    #         list_values = [row[0].value for row in qres]
    #         self.assertEqual(list_values, [1, 'str', 3.4, True])

    def test_serialize(self):
        with h5tbx.File() as h5:
            h5.attrs["a", "https://matthiasprobst.github.io/ssno#test"] = 3
            ttl = h5.serialize(fmt="ttl")
        g = rdflib.Graph().parse(data=ttl, format="ttl")
        res = g.query("""PREFIX ssno: <https://matthiasprobst.github.io/ssno#>
        SELECT ?value
        WHERE {
            ?s ssno:test ?value .
            }""")
        self.assertEqual(len(res.bindings), 1)

    def test_dump_hdf_to_json(self):
        """similar yet different to https://hdf5-json.readthedocs.io/en/latest/index.html"""
        with h5tbx.File(name=None, mode='w') as h5:
            ds = h5.create_dataset('grp/test_dataset',
                                   data=[1, 2, 3],
                                   attrs={'standard_name': 'x_velocity',
                                          'standard_name_non_iri': 'x_velocity',
                                          'unit': 'm/s'})
            ds.rdf.subject = str(M4I.NumericalVariable)
            ds.rdf.predicate['standard_name'] = 'https://matthiasprobst.github.io/ssno#standardName'
            ds.rdf.object['standard_name'] = 'https://matthiasprobst.github.io/pivmeta#x_velocity'
            ds.rdf.object['standard_name_non_iri'] = 'https://matthiasprobst.github.io/pivmeta#x_velocity'

            ds.attrs['a list'] = [0, 1, 2, 3]
            ds.attrs['a 1D list'] = (-2.3,)

        # def dump_hdf_to_json(h5_filename):
        with h5tbx.File(h5.hdf_filename, 'r') as h5:
            json_str = jsonld.dumps(h5, indent=2, compact=False)

        get_all_datasets_with_standard_name = """PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>
        PREFIX ssno: <https://matthiasprobst.github.io/ssno#>
        
        SELECT  ?name ?sn
        {
            ?obj a hdf:Dataset .
            ?obj hdf:name ?name .
            ?obj ssno:standardName ?sn .
        }"""
        g = rdflib.Graph().parse(data=json_str, format='json-ld')
        qres = g.query(get_all_datasets_with_standard_name)
        self.assertEqual(len(qres), 1)
        for name, sn in qres:
            self.assertEqual(str(name), '/grp/test_dataset')
            self.assertEqual(str(sn), 'https://matthiasprobst.github.io/pivmeta#x_velocity')

        # get list 1
        sparql_str = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX pivmeta: <https://matthiasprobst.github.io/pivmeta#>
PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>

SELECT ?item
WHERE {
  ?id a hdf:Attribute .
  ?id hdf:value ?list .
  ?id hdf:name "a list" .
  ?list rdf:rest*/rdf:first ?item
}"""
        qres = g.query(sparql_str)
        for i, row in enumerate(qres):
            self.assertEqual(int(row[0]), i)

        # get list 2
        sparql_str = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX pivmeta: <https://matthiasprobst.github.io/pivmeta#>
PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>

SELECT ?item
WHERE {
  ?id a hdf:Attribute .
  ?id hdf:value ?list .
  ?id hdf:name "a 1D list" .
  ?list rdf:rest*/rdf:first ?item
}"""
        qres = g.query(sparql_str)
        for i, row in enumerate(qres):
            self.assertEqual(float(row[0]), -2.3)

    def test_model_dump_jsonld_resolve_keys(self):
        @namespaces(prov='http://www.w3.org/ns/prov#',
                    schema='http://www.schema.org/')
        @urirefs(Affiliation='prov:Affiliation',
                 name='schema:name')
        class Affiliation(Thing):
            name: str

        @namespaces(foaf='http://xmlns.com/foaf/0.1/',
                    prov='http://www.w3.org/ns/prov#')
        @urirefs(Person='prov:Person',
                 name='foaf:firstName',
                 lastName='foaf:lastName',
                 affiliation='prov:affiliation')
        class Person(Thing):
            name: str = None
            lastName: str
            affiliation: Affiliation

        p = Person(id="https://orcid.org/123",
                   name='John', lastName='Doe',
                   affiliation=dict(name='MyCompany'))
        jdict = json.loads(p.model_dump_jsonld(resolve_keys=False))
        self.assertEqual(jdict['@type'], 'prov:Person')
        self.assertEqual(jdict['name'], 'John')
        self.assertIsInstance(jdict['prov:affiliation'], dict)
        affiliation = jdict['prov:affiliation']
        self.assertEqual(affiliation['@type'], 'prov:Affiliation')
        self.assertEqual(affiliation['schema:name'], 'MyCompany')

        with h5tbx.File() as h5:
            jsonld.to_hdf(h5, data=jdict)
            self.assertTrue(h5.rdf.subject, 'https://orcid.org/123')
            self.assertTrue(h5.rdf.type, 'http://www.w3.org/ns/prov#Person')
            self.assertTrue(h5.attrs['name'], 'John')
            self.assertEqual(h5.rdf.predicate['name'], 'http://xmlns.com/foaf/0.1/firstName')
            self.assertTrue(h5['affiliation'].attrs['name'], 'MyCompany')
            self.assertEqual(h5['affiliation'].rdf.predicate['name'], 'http://www.schema.org/name')

        jdict_resolved = json.loads(p.model_dump_jsonld(resolve_keys=True))
        self.assertEqual(jdict_resolved['foaf:firstName'], 'John')

        with h5tbx.File() as h5:
            jsonld.to_hdf(h5, data=jdict_resolved)
            self.assertTrue(h5.attrs['firstName'], 'John')
            self.assertEqual(h5.rdf.predicate['firstName'], 'http://xmlns.com/foaf/0.1/firstName')
            self.assertTrue(h5['affiliation'].attrs['name'], 'MyCompany')
            self.assertEqual(h5['affiliation'].rdf.predicate['name'], 'http://www.schema.org/name')

    def test_json_to_hdf(self):

        @namespaces(foaf='http://xmlns.com/foaf/0.1/',
                    prov='http://www.w3.org/ns/prov#',
                    schema='http://www.schema.org/')
        @urirefs(Affiliation='prov:Affiliation',
                 name='schema:name')
        class Affiliation(Thing):
            name: str

        @namespaces(foaf='http://xmlns.com/foaf/0.1/',
                    prov='http://www.w3.org/ns/prov#')
        @urirefs(Person='prov:Person',
                 name='foaf:firstName',
                 lastName='foaf:lastName',
                 affiliation='prov:affiliation')
        class Person(Thing):
            name: str = None
            lastName: str
            affiliation: Affiliation

        p = Person(name='John', lastName='Doe',
                   affiliation=dict(name='MyCompany'))

        # def dump_hdf_to_json(h5_filename):
        with h5tbx.File('test.hdf', 'w') as h5:
            jsonld.to_hdf(h5.create_group('contact'),
                          data=json.loads(p.model_dump_jsonld(resolve_keys=False)),
                          predicate='m4i:contact')
            self.assertTrue('contact' in h5)
            self.assertEqual(h5['contact'].attrs['name'], 'John')
            self.assertEqual(h5['contact'].attrs['lastName'], 'Doe')
            self.assertEqual(h5['contact'].rdf['name'].predicate, 'http://xmlns.com/foaf/0.1/firstName')
            self.assertEqual(h5['contact'].rdf['lastName'].predicate, 'http://xmlns.com/foaf/0.1/lastName')
            self.assertEqual(h5['contact/affiliation'].attrs['name'], 'MyCompany')
            h5.dumps()

        # def dump_hdf_to_json(h5_filename):
        with h5tbx.File('test.hdf', 'w') as h5:
            jsonld.to_hdf(h5.create_group('contact'),
                          data=p.model_dump_jsonld(resolve_keys=False),
                          predicate='m4i:contact')
            h5.dumps()
            self.assertTrue('contact' in h5)
            self.assertEqual(h5['contact'].attrs['name'], 'John')
            self.assertEqual(h5['contact'].attrs['lastName'], 'Doe')
            self.assertEqual(h5['contact'].rdf['name'].predicate, 'http://xmlns.com/foaf/0.1/firstName')
            self.assertEqual(h5['contact'].rdf['lastName'].predicate, 'http://xmlns.com/foaf/0.1/lastName')

        # def dump_hdf_to_json(h5_filename):
        with h5tbx.File('test.hdf', 'w') as h5:
            jsonld.to_hdf(h5.create_group('contact'),
                          source=p,
                          predicate='m4i:contact',
                          resolve_keys=False)
            self.assertTrue('contact' in h5)
            self.assertEqual(h5['contact'].attrs['name'], 'John')
            self.assertEqual(h5['contact'].attrs['lastName'], 'Doe')
            self.assertEqual(h5['contact'].rdf['name'].predicate, 'http://xmlns.com/foaf/0.1/firstName')
            self.assertEqual(h5['contact'].rdf['lastName'].predicate, 'http://xmlns.com/foaf/0.1/lastName')
            h5.dumps()

    def test_jsonld_dumps(self):
        sn_iri = 'https://matthiasprobst.github.io/ssno#standardName'
        with h5tbx.File(mode='w') as h5:
            h5.create_dataset('test_dataset', shape=(3,))
            grp = h5.create_group('grp')
            grp.attrs['test', sn_iri] = 'test'
            grp.attrs['description', SCHEMA.commentCount] = 5.3
            self.assertIsInstance(grp.attrs['description'], np.floating)

            sub_grp = grp.create_group('Fan')
            ds = sub_grp.create_dataset('D3', data=np.array([[1, 2], [3, 4], [5.4, 1.9]]), chunks=(1, 2))
            sub_grp['D3'].attrs['units', 'http://w3id.org/nfdi4ing/metadata4ing#hasUnits'] = 'mm'
            sub_grp['D3'].rdf['units'].object = 'https://qudt.org/vocab/unit/MilliM'
            sub_grp['D3'].attrs['standard_name', sn_iri] = 'blade_diameter3'
            ds.rdf.type = 'http://w3id.org/nfdi4ing/metadata4ing#NumericalVariable'
            self.assertEqual(ds.rdf.type, 'http://w3id.org/nfdi4ing/metadata4ing#NumericalVariable')
            self.assertEqual(ds.attrs[RDF_TYPE_ATTR_NAME], 'http://w3id.org/nfdi4ing/metadata4ing#NumericalVariable')
            h5.dumps()

        jsonld_str = h5tbx.dump_jsonld(
            h5.hdf_filename,
            context={'schema': 'http://schema.org/',
                     "ssno": "https://matthiasprobst.github.io/ssno#",
                     "m4i": "http://w3id.org/nfdi4ing/metadata4ing#"},
            file_uri="https://example.org#",
            indent=2
        )
        self.assertTrue("_:" not in jsonld_str)

        g = rdflib.Graph()
        g.parse(data=jsonld_str, format='json-ld')
        sparql_query = """
        PREFIX m4i: <http://w3id.org/nfdi4ing/metadata4ing#>
        PREFIX ssno: <https://matthiasprobst.github.io/ssno#>
        
        SELECT ?s ?sn ?units
        WHERE {
            ?s a m4i:NumericalVariable .
            ?s ssno:standardName ?sn . 
            ?s m4i:hasUnits ?units .
        }
        """
        res = g.query(sparql_query)
        bindings = res.bindings
        self.assertEqual(len(bindings), 1)
        self.assertEqual(bindings[0][rdflib.Variable('units')],
                         rdflib.term.URIRef('https://qudt.org/vocab/unit/MilliM'))
        self.assertEqual(bindings[0][rdflib.Variable('sn')], rdflib.term.Literal('blade_diameter3'))

    def test_person(self):
        with h5tbx.File() as h5:
            h5.create_group('person')
            h5['person'].attrs['name'] = 'John'
            h5['person'].attrs['age'] = 21
            h5.person.rdf.type = 'http://w3id.org/nfdi4ing/metadata4ing#Person'
            h5.person.rdf.subject = 'https://orcid.org/XXXX-XXXX-XXXX-XXXX'

    def test_jsonld_dumps_NDdataset(self):
        with h5tbx.File(mode='w') as h5:
            _ = h5.create_dataset('test_dataset', data=np.array([[1, 2], [3, 4], [5.4, 1.9]]))
            h5.attrs['name'] = 'test attr'
            # _ = h5.create_dataset('test_dataset', data=5.4)
            jd = jsonld.dumpd(h5, structural=True)

    def test_to_hdf_with_graph(self):
        test_data = """{
  "@context": {
    "foaf": "http://xmlns.com/foaf/0.1/",
    "prov": "http://www.w3.org/ns/prov#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "schema": "http://schema.org/",
    "local": "http://example.org/"
  },
  "@graph": [
    {
      "@id": "local:testperson1",
      "@type": "prov:Person",
      "foaf:firstName": "John",
      "foaf:lastName": "Doe",
      "age": 21,
      "schema:affiliation": {
        "@id": "Nef657ff40e464dd09580db3f32de2cf1",
        "@type": "schema:Organization",
        "rdfs:label": "MyAffiliation"
      }
    },
    {
      "@id": "local:testperson2",
      "@type": "prov:Person",
      "foaf:firstName": "Jane",
      "foaf:lastName": "Doe",
      "age": 20,
      "schema:affiliation": {
        "@type": "schema:Organization",
        "rdfs:label": "MyAffiliation"
      }
    }
  ]
}"""
        with open('graph.json', 'w') as f:
            f.write(test_data)
        jsondict = json.loads(test_data)
        self.assertTrue(jsondict['@graph'][0]['@id'].startswith('local:testperson'))
        with h5tbx.File('graph.hdf', 'w') as h5:
            grp = h5.create_group('person')
            jsonld.to_hdf(grp=grp, source='graph.json')
            self.assertTrue('@graph' not in grp)
            self.assertTrue('Person' in grp)
            self.assertTrue('Person2' in grp)
            h5.dumps()
        # cleanup:
        pathlib.Path('graph.json').unlink(missing_ok=True)
        h5.hdf_filename.unlink(missing_ok=True)

    def test_download_context(self):
        from h5rdmtoolbox.utils import download_context
        from h5rdmtoolbox import UserDir
        url = "https://w3id.org/nfdi4ing/metadata4ing/m4i_context.jsonld"
        cache_dir = UserDir['cache']
        UserDir.clear_cache(delta_days=0)
        self.assertEqual(len(list(cache_dir.glob('*'))), 0)
        ctx = download_context(url)
        self.assertEqual(ctx.vocab, "http://w3id.org/nfdi4ing/metadata4ing#")
        self.assertEqual(len(list(cache_dir.glob('*'))), 1)
        ctx = download_context(url)
        self.assertEqual(ctx.vocab, "http://w3id.org/nfdi4ing/metadata4ing#")

    def test_to_hdf_with_graph2(self):
        test_data = """{
  "@context": {
    "@import": "https://w3id.org/nfdi4ing/metadata4ing/m4i_context.jsonld",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "prov": "http://www.w3.org/ns/prov#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "schema": "http://schema.org/",
    "local": "http://example.org/"
  },
  "@graph": [
    {
      "@id": "local:preparation_0001",
      "@type": "processing step",
      "label": "Sample preparation and parameter definition",
      "has participant": "local:testperson1",
      "start time": "2022-09-22T10:31:22"
    },
    {
      "@id": "local:testperson1",
      "@type": "prov:Person",
      "foaf:firstName": "John",
      "foaf:lastName": "Doe",
      "age": 21,
      "schema:affiliation": {
        "@id": "Nef657ff40e464dd09580db3f32de2cf1",
        "@type": "schema:Organization",
        "rdfs:label": "MyAffiliation"
      }
    },
    {
      "@id": "local:testperson2",
      "@type": "prov:Person",
      "rdfs:label": "Jane Doe",
      "foaf:firstName": "Jane",
      "foaf:lastName": "Doe",
      "age": 20,
      "schema:affiliation": {
        "@type": "schema:Organization",
        "rdfs:label": "MyAffiliation"
      }
    }
  ]
}"""
        with open('graph.json', 'w') as f:
            f.write(test_data)
        jsondict = json.loads(test_data)
        assert isinstance(jsondict, dict)

        with h5tbx.File('graph.hdf', 'w') as h5:
            grp = h5.create_group('person')
            jsonld.to_hdf(grp=grp, source='graph.json')
            self.assertTrue('@graph' not in grp)
            self.assertTrue('Person' in grp)
            self.assertTrue('Jane Doe' in grp)
            self.assertEqual(grp['Jane Doe'].attrs['age'], 20)
            h5.dumps()
        # cleanup:
        pathlib.Path('graph.json').unlink(missing_ok=True)
        h5.hdf_filename.unlink(missing_ok=True)

    def test_to_hdf(self):
        test_data = """{"@context": {"foaf": "http://xmlns.com/foaf/0.1/", "prov": "http://www.w3.org/ns/prov#",
"rdfs": "http://www.w3.org/2000/01/rdf-schema#",
 "schema": "http://schema.org/",
 "local": "http://example.org/"},
"@id": "local:testperson",
"@type": "prov:Person",
"foaf:firstName": "John",
"foaf:lastName": "Doe",
"age": 21,
"schema:affiliation": {
    "@id": "local:KIT",
    "@type": "schema:Organization",
    "rdfs:label": "MyAffiliation"
    }
}"""
        with open('test.json', 'w') as f:
            f.write(test_data)

        with h5tbx.File('test.hdf', 'w') as h5:
            jsonld.to_hdf(grp=h5.create_group('person'), source='test.json')
            self.assertTrue('person' in h5)
            self.assertTrue('firstName' in h5['person'].attrs)
            self.assertTrue('lastName' in h5['person'].attrs)
            self.assertEqual(h5['person'].attrs['firstName'], 'John')
            self.assertEqual(h5['person'].attrs['age'], 21)
            self.assertEqual("http://example.org/testperson", h5.person.rdf.subject)
            self.assertEqual("http://example.org/KIT", h5.person.affiliation.rdf.subject)

        h5tbx.dumps('test.hdf')
        pathlib.Path('test.json').unlink(missing_ok=True)
        h5.hdf_filename.unlink(missing_ok=True)

    def test_codemeta_to_hdf(self):
        codemeta_filename = __this_dir__ / '../../codemeta.json'

        data = ontolutils.dquery(
            'schema:SoftwareSourceCode',
            codemeta_filename,
            context={'schema': 'http://schema.org/'})  # Note, that codemeta uses the unsecure http

        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['version'].replace("-rc.", "rc"), __version__)
        self.assertTrue('author' in data[0])
        self.assertIsInstance(data[0]['author'], list)
        with h5tbx.File('test.hdf', 'w') as h5:
            jsonld.to_hdf(grp=h5.create_group('person'), data=data[0],
                          context={'@import': "https://doi.org/10.5063/schema/codemeta-2.0"})
            self.assertEqual(h5['person']['author1'].attrs[rdf.RDF_PREDICATE_ATTR_NAME]['SELF'],
                             'http://schema.org/author')

        h5tbx.dumps('test.hdf')

        h5.hdf_filename.unlink(missing_ok=True)

    def test_jsonld_with_attrs_definition(self):
        with h5tbx.File() as h5:
            h5.attrs['name'] = h5tbx.Attribute('Matthias', definition='My first name')
            jstr = h5.dump_jsonld()

        sparql_str = """SELECT ?n ?v ?d
{
    ?id <http://purl.allotrope.org/ontologies/hdf5/1.8#attribute> ?a .
    ?a <http://purl.allotrope.org/ontologies/hdf5/1.8#name> ?n .
    ?a <http://purl.allotrope.org/ontologies/hdf5/1.8#value> ?v .
    ?a <http://www.w3.org/2004/02/skos/core#definition> ?d .
}"""
        g = rdflib.Graph().parse(data=jstr, format='json-ld')
        qres = g.query(sparql_str)
        for row in qres:
            self.assertEqual(str(row[0]), 'name')
            self.assertEqual(str(row[1]), 'Matthias')
            self.assertEqual(str(row[2]), 'My first name')

    def test_hdf2jsonld(self):
        test_data = """{"@context": {"foaf": "http://xmlns.com/foaf/0.1/", "prov": "http://www.w3.org/ns/prov#",
"rdfs": "http://www.w3.org/2000/01/rdf-schema#",
 "schema": "http://schema.org/",
 "local": "http://example.org/"},
"@id": "local:testperson",
"@type": "prov:Person",
"foaf:firstName": "John",
"foaf:lastName": "Doe",
"age": 21,
"schema:affiliation": {
    "@id": "Nef657ff40e464dd09580db3f32de2cf1",
    "@type": "schema:Organization",
    "rdfs:label": "MyAffiliation"
    }
}"""
        with open('test.json', 'w') as f:
            f.write(test_data)
        with h5tbx.File('test.hdf', 'w') as h5:
            jsonld.to_hdf(grp=h5.create_group('person'), source='test.json')

        jsonld_filename = hdf2jsonld('test.hdf', skipND=1)
        self.assertTrue(jsonld_filename.exists())
        self.assertTrue(jsonld_filename.suffix == '.jsonld')
        jsonld_filename.unlink()

        ttl_filename = hdf2ttl('test.hdf', skipND=1)
        self.assertTrue(ttl_filename.exists())
        self.assertTrue(ttl_filename.suffix == '.ttl')
        ttl_filename.unlink()

    def test_hdf2jsonld_with_standard_name_table(self):
        with h5tbx.File() as h5:
            h5.attrs["snt_file"] = "https://sandbox.zenodo.org/uploads/125545"
            h5.frdf["snt_file"].predicate = ssnolib.namespace.SSNO.usesStandardNameTable
            h5["/"].attrs["snt_rootgroup"] = "https://sandbox.zenodo.org/uploads/12554567"
            h5["/"].rdf["snt_rootgroup"].predicate = ssnolib.namespace.SSNO.usesStandardNameTable

        jdict = json.loads(
            h5tbx.dump_jsonld(h5.hdf_filename, indent=2, contextual=True, structural=True,
                              context={"ssno": "https://matthiasprobst.github.io/ssno#"}))
        jdict["ssno:usesStandardNameTable"] = "https://sandbox.zenodo.org/uploads/125545"

        with h5tbx.File() as h5:
            h5.create_group('grp')
            h5.attrs["snt_file"] = "https://sandbox.zenodo.org/uploads/125545"
            h5["grp"].frdf["snt_file"].predicate = ssnolib.namespace.SSNO.usesStandardNameTable
            h5["grp"].frdf["snt_file"].object = DCAT.Dataset
            self.assertEqual(
                h5["/"].attrs[RDF_FILE_PREDICATE_ATTR_NAME]["snt_file"],
                str(ssnolib.namespace.SSNO.usesStandardNameTable)
            )

    def test_frdf(self):
        with h5tbx.File() as h5:
            h5.frdf.type = "dcat:Dataset"
            self.assertEqual(
                h5.frdf.type,
                "http://www.w3.org/ns/dcat#Dataset"
            )

            with self.assertRaises(RDFError):
                h5.frdf.type = "unknown:Dataset"
            self.assertEqual(
                h5.frdf.type,
                "http://www.w3.org/ns/dcat#Dataset"
            )

            jdict = json.loads(h5tbx.dump_jsonld(h5.hdf_filename, structural=True, indent=2))
            self.assertDictEqual({
                "dcat": "http://www.w3.org/ns/dcat#",
                "hdf": "http://purl.allotrope.org/ontologies/hdf5/1.8#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            },
                jdict["@context"]
            )
            self.assertEqual(len(jdict["@graph"]), 2)
            self.assertEqual(sorted(jdict["@graph"][0]["@type"]),
                             sorted(["hdf:File", "dcat:Dataset"]))

            jdict = json.loads(h5.dump_jsonld(structural=False, indent=2))
            self.assertDictEqual({
                "dcat": "http://www.w3.org/ns/dcat#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
            },
                jdict["@context"]
            )
            self.assertEqual(
                sorted(jdict.get("@type")),
                sorted("dcat:Dataset")
            )

    def test_frdf_multiple_object(self):
        with h5tbx.File() as h5:
            h5.attrs["thing"] = "Thing"
            h5.frdf["thing"].predicate = SCHEMA.about
            h5.frdf["thing"].object = "https://example.org/Thing1"
            h5.attrs["another_thing"] = "Thing 2"
            h5.frdf["another_thing"].predicate = SCHEMA.about
            h5.frdf["another_thing"].object = "https://example.org/Thing2"

            print(h5.serialize("ttl", structural=False))

    def test_only_subject(self):
        with h5tbx.File() as h5:
            g = h5.create_group("contact")
            g.attrs["id"] = "0000-0001-8729-0482"
            g.rdf.subject = "https://orcid.org/0000-0001-8729-0482"
            ttl = h5.serialize(fmt="ttl", structural=True)
            print(ttl)
            # write sparql that gets the dcterms:relation of a hdf:Group:
            g = rdflib.Graph().parse(data=ttl, format="ttl")
            sparql_str = """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#>
PREFIX schema: <https://schema.org/>

SELECT ?s ?relation
WHERE {
    ?s a hdf:Group .
    ?s schema:about ?relation .
}   
"""
            res = g.query(sparql_str)
            bindings = res.bindings
            self.assertEqual(len(bindings), 1)
            self.assertEqual(str(bindings[0][rdflib.Variable("relation")]), "https://orcid.org/0000-0001-8729-0482")

    def test_setting_nested_objects(self):
        filename = h5tbx.utils.generate_temporary_filename(suffix=".hdf")
        with h5tbx.File(filename, "w") as h5:
            h5.attrs["snt"] = "123"
            h5.frdf["snt"].predicate = "https://matthiasprobst.github.io/ssno#usesStandardNameTable"
            h5.frdf["snt"].object = "https://zenodo.org/records/17572275/files/opencefadb_standard_name_table.jsonld"
            del h5.frdf["snt"].object
            h5.frdf["snt"].object = ssnolib.StandardNameTable(
                id="https://doi.org/10.5281/zenodo.17572275#StandardNameTable",
                dataset=dcat.Dataset(
                    id="https://doi.org/10.5281/zenodo.17572275",
                    distribution=dcat.Distribution(
                        id="https://doi.org/10.5281/zenodo.17572275#Distribution",
                        download_URL="https://zenodo.org/records/17572275/files/opencefadb_standard_name_table.jsonld"
                    )
                )
            )
            ttl = f"""@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix ssno: <https://matthiasprobst.github.io/ssno#> .

<https://example.org#{filename.name}> ssno:usesStandardNameTable <https://doi.org/10.5281/zenodo.17572275#StandardNameTable> .

<https://doi.org/10.5281/zenodo.17572275> a dcat:Dataset ;
    dcat:distribution <https://doi.org/10.5281/zenodo.17572275#Distribution> .

<https://doi.org/10.5281/zenodo.17572275#Distribution> a dcat:Distribution ;
    dcat:downloadURL <https://zenodo.org/records/17572275/files/opencefadb_standard_name_table.jsonld> .

<https://doi.org/10.5281/zenodo.17572275#StandardNameTable> a ssno:StandardNameTable ;
    ssno:dataset <https://doi.org/10.5281/zenodo.17572275> .

"""
            g1 = rdflib.Graph().parse(data=ttl, format="ttl")
            actual_ttl = h5.serialize("ttl", structural=False, file_uri=f"https://example.org#")
            g2 = rdflib.Graph().parse(data=actual_ttl,
                                      format="ttl")
            g1ttl = g1.serialize(format="ttl")
            g2ttl = g2.serialize(format="ttl")
            self.assertEqual(g1ttl, g2ttl)

    def test_rdf_mappings(self):
        _filename = pathlib.Path("deleteme.hdf")
        with h5tbx.File(_filename, mode="w") as h5:
            ds = h5.create_dataset("u", data=[1, 2, 3])
            ds.attrs["units"] = "m/s"
            ds.attrs["standard_name"] = "x_velocity"
            g = h5.create_group("grp")
            g.attrs["long_name"] = "velocity"

        def _get_qudt_unit(value, _):
            return qudt_lookup.get(value, None)

        def _make_standard_name(value, ctx):
            _unit = ctx.get("units", None)
            if _unit is not None:
                units = _get_qudt_unit(_unit, None)
                if units is not None:
                    return ssnolib.StandardName(
                        standard_name=value,
                        unit=units)  # units should be canonical, so this is not yet totally correct
            return None

        rdf_mappings = {
            "units": {
                "predicate": M4I.hasUnit,
                "object": _get_qudt_unit,
            },
            "long_name": {
                "predicate": SKOS.altLabel
            },
            "standard_name": {
                "predicate": ssnolib.SSNO.hasStandardName,
                "object": _make_standard_name
            }
        }
        ttl = h5tbx.serialize(
            h5.hdf_filename,
            fmt="ttl",
            rdf_mappings=rdf_mappings,
            file_uri="https://example.org#"
        )
        print(ttl)
        self.assertEqual("""@prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .
@prefix m4i: <http://w3id.org/nfdi4ing/metadata4ing#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ssno: <https://matthiasprobst.github.io/ssno#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://example.org#deleteme.hdf> a hdf:File ;
    hdf:rootGroup <https://example.org#deleteme.hdf/> .

hdf:H5T_INTEL_I64 a hdf:Datatype .

<https://example.org#deleteme.hdf/> a hdf:Group ;
    hdf:member <https://example.org#deleteme.hdf/grp>,
        <https://example.org#deleteme.hdf/u> ;
    hdf:name "/" .

<https://example.org#deleteme.hdf/grp> a hdf:Group ;
    hdf:attribute <https://example.org#deleteme.hdf/grp@long_name> ;
    hdf:name "/grp" ;
    skos:altLabel "velocity" .

<https://example.org#deleteme.hdf/grp@long_name> a hdf:StringAttribute ;
    hdf:data "velocity" ;
    hdf:name "long_name" .

<https://example.org#deleteme.hdf/u> a hdf:Dataset ;
    hdf:attribute <https://example.org#deleteme.hdf/u@standard_name>,
        <https://example.org#deleteme.hdf/u@units> ;
    hdf:dataspace <https://example.org#deleteme.hdf/u__dataspace> ;
    hdf:datatype hdf:H5T_INTEGER,
        hdf:H5T_INTEL_I64 ;
    hdf:layout hdf:H5D_CONTIGUOUS ;
    hdf:maximumSize 3 ;
    hdf:name "/u" ;
    hdf:rank 1 ;
    hdf:size 3 ;
    m4i:hasUnit <http://qudt.org/vocab/unit/M-PER-SEC> ;
    ssno:hasStandardName <x_velocity> .

<https://example.org#deleteme.hdf/u@standard_name> a hdf:StringAttribute ;
    hdf:data "x_velocity" ;
    hdf:name "standard_name" .

<https://example.org#deleteme.hdf/u@units> a hdf:StringAttribute ;
    hdf:data "m/s" ;
    hdf:name "units" .

<https://example.org#deleteme.hdf/u__dataspace> a hdf:SimpleDataspace ;
    hdf:dimension <https://example.org#deleteme.hdf/u__dataspace_dimension_0> .

<https://example.org#deleteme.hdf/u__dataspace_dimension_0> a hdf:DataspaceDimension ;
    hdf:dimensionIndex 0 ;
    hdf:size 3 .

""".replace("tmp0.hdf", _filename.name), ttl)
        _filename.unlink(missing_ok=True)

    def test_quote(self):
        with h5tbx.File() as h5:
            h5.attrs['quote_test'] = 'This is a "quote" test'
            ttl = h5.serialize("ttl")
        self.assertEqual(ttl, """@prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .

[] a hdf:File ;
    hdf:rootGroup [ a hdf:Group ;
            hdf:attribute [ a hdf:StringAttribute ;
                    hdf:data "This is a \\"quote\\" test" ;
                    hdf:name "quote_test" ] ;
            hdf:name "/" ] .

""")