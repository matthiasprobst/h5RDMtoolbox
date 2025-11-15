import datetime
import pathlib
import unittest

import rdflib
import ssnolib
from ontolutils.namespacelib import M4I, SCHEMA
from ontolutils.namespacelib.hdf5 import HDF5
from ssnolib.namespace import SSNO

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox.ld.user.attributes import process_attribute, process_file_attribute

logger = h5tbx.set_loglevel('ERROR')

__this_dir__ = pathlib.Path(__file__).parent


class TestUserGraph(unittest.TestCase):

    def setUp(self):
        with h5tbx.File() as h5:
            grp = h5.create_group("h5rdmtoolbox")
            grp.rdf.type = SCHEMA.SoftwareSourceCode
            grp.attrs["version", SCHEMA.version] = "1.2.3"

            ds = h5.create_dataset("a/b/ds", data=[[1, 2], [3, 4]],
                                   chunks=(1, 2), compression="gzip", compression_opts=2)
            self.assertEqual(ds.chunks, (1, 2))
            ds2 = h5.create_dataset("nochunk", data=[[1, 2], [3, 4]], chunks=None)
            self.assertEqual(ds2.chunks, None)
            ds.rdf.type = M4I.NumericalVariable
            ds.attrs["standard_name", SSNO.hasStandardName] = "x_velocity"
            ds.rdf["standard_name"].object = ssnolib.ssno.standard_name.StandardName(
                id="https://example.org/123",
                standardName="x_velocity",
                unit="m/s"
            )
        self.hdf_filename = h5.hdf_filename

    def test_process_attributes(self):
        graph = rdflib.Graph()
        graph.bind("hdf5", str(HDF5))
        graph.bind("ssno", str(SSNO))
        with h5tbx.File(self.hdf_filename) as h5:
            process_attribute(h5["a/b/ds"], "standard_name", h5["a/b/ds"].attrs["standard_name"], graph, None)
        serialization = graph.serialize(format="turtle", indent=2)

        exception_serialization = """@prefix ssno: <https://matthiasprobst.github.io/ssno#> .

<https://example.org/123> a ssno:StandardName ;
    ssno:standardName "x_velocity" ;
    ssno:unit <http://qudt.org/vocab/unit/M-PER-SEC> .

[] a <http://w3id.org/nfdi4ing/metadata4ing#NumericalVariable> ;
    ssno:hasStandardName <https://example.org/123> .

"""
        self.assertEqual(
            rdflib.Graph().parse(data=serialization, format="turtle").serialize(format="turtle"),
            rdflib.Graph().parse(data=exception_serialization, format="turtle").serialize(format="turtle")
        )

    def test_process_file_attributes(self):
        graph = rdflib.Graph()
        graph.bind("hdf5", str(HDF5))
        graph.bind("ssno", str(SSNO))
        with h5tbx.File() as h5:
            h5.attrs["mod_time"] = "today"
            h5.frdf["mod_time"].predicate = SCHEMA.dateModified
            process_file_attribute(h5, "mod_time", h5.attrs["mod_time"], graph, rdflib.BNode("1234"),
                                   blank_node_iri_base=None)
        serialization = graph.serialize(format="turtle")
        exception_serialization = """@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

[] schema:dateModified "today" ."""
        self.assertEqual(
            rdflib.Graph().parse(data=serialization, format="turtle").serialize(format="turtle"),
            rdflib.Graph().parse(data=exception_serialization, format="turtle").serialize(format="turtle")
        )

    def test_literals_as_rdf_object(self):
        with h5tbx.File() as h5:
            h5.attrs["description"] = "An english description"
            h5.frdf["description"].predicate = SCHEMA.description
            h5.frdf["description"].object = rdflib.Literal("An english description", "en")

            self.assertEqual("An english description", h5.attrs["description"])
            ttl = h5.serialize(fmt="ttl", contextual=True, structural=False)

        self.assertEqual(ttl, """@prefix schema: <https://schema.org/> .

[] schema:description "An english description"@en .

""")

    def test_literals_as_rdf_object2(self):
        with h5tbx.File() as h5:
            h5.attrs["description"] = "An english description"
            h5.frdf["description"].predicate = SCHEMA.description
            h5.frdf["description"].object = [rdflib.Literal("An english description", "en"),
                                             rdflib.Literal("Eine deutsche Beschreibung", "de")]

            self.assertEqual("An english description", h5.attrs["description"])
            ttl = h5.serialize(fmt="ttl", contextual=True, structural=False)

        self.assertEqual(ttl, """@prefix schema: <https://schema.org/> .

[] schema:description "Eine deutsche Beschreibung"@de,
        "An english description"@en .

""")

    def test_literals_as_rdf_object_shortcut(self):
        """assigning a literal directly to the attribute should work as well"""
        with h5tbx.File() as h5:
            h5.attrs["description"] = rdflib.Literal("An english description", "en")
            # h5.frdf["description"].predicate = SCHEMA.additionalProperty
            # h5.frdf["description"].object = Thing(id="https://evalue=rdf_user_object")# rdflib.Literal("An english description", "en")

            # self.assertEqual("An english description", h5.attrs["description"])
            ttl = h5.serialize(fmt="ttl", contextual=True, structural=False)
        print(ttl)
        self.assertEqual(ttl, """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .

[] rdf:value "An english description"@en .

""")

    def test_literals_as_rdf_group_object(self):
        with h5tbx.File() as h5:
            g = h5.create_group("group")
            g.attrs["description"] = "A description"
            g.rdf["description"].predicate = SCHEMA.description
            g.rdf["description"].object = rdflib.Literal("An english description", "en")

            print(g.rdf["description"].object)
            self.assertEqual(rdflib.Literal("An english description", "en"), g.rdf["description"].object)
            self.assertEqual("A description", g.attrs["description"])
            ttl = h5.serialize(fmt="ttl", contextual=True, structural=False)

        self.assertEqual(ttl, """@prefix schema: <https://schema.org/> .

[] schema:description "An english description"@en .

""")

    def test_literals_as_rdf_dataset_object(self):
        with h5tbx.File() as h5:
            ds = h5.create_dataset("ds", data=[1, 2, 3])
            ds.attrs["description"] = "A description"
            ds.rdf["description"].predicate = SCHEMA.description
            ds.rdf["description"].object = rdflib.Literal("An english description", "en")

            print(ds.rdf["description"].object)
            self.assertEqual(rdflib.Literal("An english description", "en"), ds.rdf["description"].object)
            self.assertEqual("A description", ds.attrs["description"])
            ttl = h5.serialize(fmt="ttl", contextual=True, structural=False)

        self.assertEqual(ttl, """@prefix schema: <https://schema.org/> .

[] schema:description "An english description"@en .

""")

    def test_multiple_literals_as_rdf_object(self):
        with h5tbx.File() as h5:
            ds = h5.create_dataset("ds", data=[1, 2, 3])
            ds.attrs["description"] = "A description"
            ds.rdf["description"].predicate = SCHEMA.description
            ds.rdf["description"].object = rdflib.Literal("Eine deutsche Beschreibung", "de")
            ds.rdf["description"].object = rdflib.Literal("An english description", "en")

            print(ds.rdf["description"].object)
            self.assertEqual(
                [
                    rdflib.Literal("Eine deutsche Beschreibung", "de"),
                    rdflib.Literal("An english description", "en")
                ],
                ds.rdf["description"].object)
            self.assertEqual("A description", ds.attrs["description"])
            ttl = h5.serialize(fmt="ttl", contextual=True, structural=False)

        self.assertEqual(ttl, """@prefix schema: <https://schema.org/> .

[] schema:description "Eine deutsche Beschreibung"@de,
        "An english description"@en .

""")

    def test_parse_datetime_literal(self):
        with h5tbx.File() as h5:
            h5.attrs["created"] = "2025-01-10"
            h5.frdf["created"].predicate = "http://purl.org/dc/terms/created"

            self.assertEqual("2025-01-10", h5.attrs["created"])
            ttl = h5.serialize(fmt="ttl", contextual=True, structural=False)
            self.assertEqual(ttl, """@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

[] dcterms:created "2025-01-10"^^xsd:date .

""")
        with h5tbx.File() as h5:
            h5.attrs["created"] = datetime.datetime(year=2025, month=1, day=10)
            h5.frdf["created"].predicate = "http://purl.org/dc/terms/created"

            self.assertEqual("2025-01-10T00:00:00000000", h5.attrs["created"])
            ttl = h5.serialize(fmt="ttl", contextual=True, structural=False)
            self.assertEqual(ttl, """@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

[] dcterms:created "2025-01-10T00:00:00"^^xsd:dateTime .

""")

    def test_group_predicate2(self):
        """now relating it to the file"""
        with h5tbx.File("deleteme.hdf", "w") as h5:
            grp = h5.create_group(
                'contact',
                attrs=dict(orcid='https://orcid.org/0000-0001-8729-0482')
            )
            grp.attrs['first_name', rdflib.FOAF.givenName] = 'Matthias'
            grp.attrs['last_name', rdflib.FOAF.familyName] = 'Probst'
            grp.rdf['orcid'].predicate = 'http://w3id.org/nfdi4ing/metadata4ing#orcidId'  # relates this to the file

            grp.rdf.type = 'http://xmlns.com/foaf/0.1/Person'  # what the content of group is, namely a foaf:Person
            grp.rdf.file_predicate = rdflib.DCTERMS.creator  # relates the file to "contact" via dcterms:creator
            self.assertEqual(grp.rdf.file_predicate, str(rdflib.DCTERMS.creator))
            del grp.rdf.file_predicate
            self.assertIsNone(grp.rdf.file_predicate)
            grp.rdf.file_predicate = rdflib.DCTERMS.creator
            grp.rdf.subject = 'https://orcid.org/0000-0001-8729-0482'  # corresponds to @ID in JSON-LD

            ttl = h5.serialize("ttl", file_uri="http://example.com#")
            self.assertEqual(ttl, """@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix foaf: <http://xmlns.com/foaf/0.1/> .
@prefix hdf: <http://purl.allotrope.org/ontologies/hdf5/1.8#> .
@prefix m4i: <http://w3id.org/nfdi4ing/metadata4ing#> .
@prefix schema: <https://schema.org/> .

<http://example.com#deleteme.hdf> a hdf:File ;
    hdf:rootGroup <http://example.com#deleteme.hdf/> ;
    dcterms:creator <https://orcid.org/0000-0001-8729-0482> .

<http://example.com#deleteme.hdf/> a hdf:Group ;
    hdf:member <http://example.com#deleteme.hdf/contact> ;
    hdf:name "/" .

<http://example.com#deleteme.hdf/contact> a hdf:Group ;
    hdf:attribute <http://example.com#deleteme.hdf/contact@first_name>,
        <http://example.com#deleteme.hdf/contact@last_name>,
        <http://example.com#deleteme.hdf/contact@orcid> ;
    hdf:name "/contact" ;
    schema:about <https://orcid.org/0000-0001-8729-0482> .

<http://example.com#deleteme.hdf/contact@first_name> a hdf:StringAttribute ;
    hdf:data "Matthias" ;
    hdf:name "first_name" .

<http://example.com#deleteme.hdf/contact@last_name> a hdf:StringAttribute ;
    hdf:data "Probst" ;
    hdf:name "last_name" .

<http://example.com#deleteme.hdf/contact@orcid> a hdf:StringAttribute ;
    hdf:data "https://orcid.org/0000-0001-8729-0482" ;
    hdf:name "orcid" .

<https://orcid.org/0000-0001-8729-0482> a foaf:Person ;
    m4i:orcidId <https://orcid.org/0000-0001-8729-0482> ;
    foaf:familyName "Probst" ;
    foaf:givenName "Matthias" .

""")
        if h5.hdf_filename.exists():
            h5.hdf_filename.unlink()
