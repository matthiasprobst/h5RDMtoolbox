import pathlib
import unittest

import rdflib
from pyshacl import validate

import h5rdmtoolbox as h5tbx

from h5rdmtoolbox.ld.shacl import validate_hdf
logger = h5tbx.set_loglevel('ERROR')

__this_dir__ = pathlib.Path(__file__).parent


class TestShacl(unittest.TestCase):

    def test_all_subjects_must_have_created(self):
        with h5tbx.File() as h5:
            h5.attrs["created"] = "2025-01-10"
            h5.frdf["created"].predicate = "http://purl.org/dc/terms/created"

            self.assertEqual("2025-01-10", h5.attrs["created"])
            ttl = h5.serialize(fmt="ttl", contextual=True, structural=False)

        shapes_ttl = '''
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix ex: <http://example.org/ns#> .

# Shape 1: Check that at least one dcterms:created triple exists in the dataset
ex:CreatedExistsShape
    a sh:NodeShape ;
    sh:targetNode ex:DummyTarget ;
    sh:sparql [
        a sh:SPARQLConstraint ;
        sh:message "The graph must contain at least one dcterms:created triple." ;
        sh:select """SELECT $this WHERE {
            FILTER NOT EXISTS { ?s dcterms:created ?o . }
        }""" ;
    ] .

# Shape 2: Check that all dcterms:created values are xsd:date
ex:CreatedDateShape
    a sh:NodeShape ;
    sh:targetSubjectsOf dcterms:created ;
    sh:property [
        sh:path dcterms:created ;
        sh:datatype xsd:date ;
        sh:message "Each dcterms:created must be of datatype xsd:date." ;
    ] .
'''
        # --- Validate ---
        data_g = rdflib.Graph().parse(data=ttl, format="turtle")
        shapes_g = rdflib.Graph().parse(data=shapes_ttl, format="turtle")

        conforms, results_graph, results_text = validate(
            data_graph=data_g,
            shacl_graph=shapes_g,
            inference='rdfs',
            abort_on_first=False,
            allow_infos=True,
            allow_warnings=True,
        )

        self.assertTrue(conforms)

        with h5tbx.File() as h5:
            h5.attrs["created"] = "2025-01-10"

            self.assertEqual("2025-01-10", h5.attrs["created"])
            ttl = h5.serialize(fmt="ttl", contextual=True, structural=False)

        # --- Validate ---
        data_g = rdflib.Graph().parse(data=ttl, format="turtle")
        shapes_g = rdflib.Graph().parse(data=shapes_ttl, format="turtle")
        conforms, results_graph, results_text = validate(
            data_graph=data_g,
            shacl_graph=shapes_g,
            inference='rdfs',
            abort_on_first=False,
            allow_infos=True,
            allow_warnings=True,
        )
        self.assertFalse(conforms)
        print(results_text)

        from rdflib.namespace import SH

        # SH = Namespace("http://www.w3.org/ns/shacl#")

        # Alle sh:message-Objekte als Strings
        messages = [str(m) for m in results_graph.objects(predicate=SH.message)]

        # Beispiel: als Assertion in einem Test verwenden
        self.assertTrue(messages, "Keine sh:message im results_graph gefunden")
        msg = messages[0]
        self.assertIn("dcterms:created", msg)  # optional: erwarteten Inhalt prüfen

        # oder nur ausgeben
        print(msg)

    def test_hdf_must_have_dcterms_created(self):
        with h5tbx.File() as h5:
            g = h5.create_group("grp")
            g.attrs["created"] = "2025-01-10"
            g.rdf["created"].predicate = "http://purl.org/dc/terms/created"

            self.assertEqual("2025-01-10", g.attrs["created"])
            ttl = h5.serialize(fmt="ttl", contextual=True, structural=True)

        shapes_ttl = '''@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .
@prefix ex: <http://example.org/ns#> .

ex:HDFFileCreatedShape
    a sh:NodeShape ;
    sh:targetClass hdf:File ;                # apply only to hdf:File instances
    sh:property [
        sh:path dcterms:created ;            # must have this property
        sh:datatype xsd:date ;               # value must be a date
        sh:minCount 1 ;                      # at least one occurrence
        sh:maxCount 1 ;                      # optional but recommended
        sh:message "Each hdf:File must have exactly one dcterms:created value of type xsd:date." ;
    ] .'''
        data_g = rdflib.Graph().parse(data=ttl, format="turtle")
        shapes_g = rdflib.Graph().parse(data=shapes_ttl, format="turtle")
        conforms, results_graph, results_text = validate(
            data_graph=data_g,
            shacl_graph=shapes_g,
            inference='rdfs',
            abort_on_first=False,
            allow_infos=True,
            allow_warnings=True,
        )
        self.assertFalse(conforms)

        with h5tbx.File() as h5:
            h5.attrs["created"] = "2025-01-10"
            h5.frdf["created"].predicate = "http://purl.org/dc/terms/created"

            self.assertEqual("2025-01-10", h5.attrs["created"])
            ttl = h5.serialize(fmt="ttl", contextual=True, structural=True)

        shapes_ttl = '''@prefix sh: <http://www.w3.org/ns/shacl#> .
    @prefix dcterms: <http://purl.org/dc/terms/> .
    @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
    @prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .
    @prefix ex: <http://example.org/ns#> .

    ex:HDFFileCreatedShape
        a sh:NodeShape ;
        sh:targetClass hdf:File ;                # apply only to hdf:File instances
        sh:property [
            sh:path dcterms:created ;            # must have this property
            sh:datatype xsd:date ;               # value must be a date
            sh:minCount 1 ;                      # at least one occurrence
            sh:maxCount 1 ;                      # optional but recommended
            sh:message "Each hdf:File must have exactly one dcterms:created value of type xsd:date." ;
        ] .'''
        data_g = rdflib.Graph().parse(data=ttl, format="turtle")
        shapes_g = rdflib.Graph().parse(data=shapes_ttl, format="turtle")
        conforms, results_graph, results_text = validate(
            data_graph=data_g,
            shacl_graph=shapes_g,
            inference='rdfs',
            abort_on_first=False,
            allow_infos=True,
            allow_warnings=True,
        )
        self.assertTrue(conforms)

    def test_validate_hdf(self):

        with h5tbx.File() as h5:
            h5.attrs["created"] = "2025-01-10"
            h5.frdf["created"].predicate = "http://purl.org/dc/terms/created"

            self.assertEqual("2025-01-10", h5.attrs["created"])

        shapes_ttl = '''@prefix sh: <http://www.w3.org/ns/shacl#> .
            @prefix dcterms: <http://purl.org/dc/terms/> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
            @prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .
            @prefix ex: <http://example.org/ns#> .

            ex:HDFFileCreatedShape
                a sh:NodeShape ;
                sh:targetClass hdf:File ;                # apply only to hdf:File instances
                sh:property [
                    sh:path dcterms:created ;            # must have this property
                    sh:datatype xsd:date ;               # value must be a date
                    sh:minCount 1 ;                      # at least one occurrence
                    sh:maxCount 1 ;                      # optional but recommended
                    sh:message "Each hdf:File must have exactly one dcterms:created value of type xsd:date." ;
                ] .'''

        res = validate_hdf(hdf_source=h5.hdf_filename, shacl_data=shapes_ttl)
        self.assertTrue(res.conforms)

        with open("shacl.ttl", "w") as f:
            f.write(shapes_ttl)
        res = validate_hdf(hdf_source=h5.hdf_filename, shacl_source="shacl.ttl")
        self.assertTrue(res.conforms)

        with h5tbx.File(h5.hdf_filename) as h5f:
            res = validate_hdf(hdf_source=h5f, shacl_source="shacl.ttl")
            self.assertTrue(res.conforms)

        pathlib.Path("shacl.ttl").unlink()

        self.assertEqual(res.conforms, True)
        self.assertEqual(res.messages, [])

        # failing case:
        with h5tbx.File() as h5:
            self.assertEqual(res.conforms, True)
            self.assertEqual(res.messages, [])
            res = validate_hdf(hdf_source=h5.hdf_filename, shacl_data=shapes_ttl)
            self.assertFalse(res.conforms)
            self.assertIn("Each hdf:File must have exactly one dcterms:created value of type xsd:date.", res.messages[0])