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
            ds2 = h5.create_dataset("nochunk", data=[[1, 2], [3, 4]], chunks=None)
            ds.rdf.type = M4I.NumericalVariable
            ds.attrs["standard_name", SSNO.hasStandardName] = "x_velocity"
            ds.rdf["standard_name"].object = ssnolib.ssno.standard_name.StandardName(id="_:123",
                                                                                     standardName="x_velocity",
                                                                                     unit="m/s")
        self.hdf_filename = h5.hdf_filename

    def test_process_attributes(self):
        graph = rdflib.Graph()
        graph.bind("hdf5", str(HDF5))
        graph.bind("ssno", str(SSNO))
        with h5tbx.File(self.hdf_filename) as h5:
            process_attribute(h5["a/b/ds"], "standard_name", h5["a/b/ds"].attrs["standard_name"], graph, None)
        serialization = graph.serialize(format="turtle", indent=2)

        exception_serialization = """@prefix ssno: <https://matthiasprobst.github.io/ssno#> .

[] a <http://w3id.org/nfdi4ing/metadata4ing#NumericalVariable> ;
    ssno:hasStandardName [ a ssno:StandardName ;
            ssno:standardName "x_velocity" ;
            ssno:unit "http://qudt.org/vocab/unit/M-PER-SEC" ] .
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
            process_file_attribute(h5, "mod_time", h5.attrs["mod_time"], graph, None, rdflib.BNode("1234"))
        serialization = graph.serialize(format="turtle")
        exception_serialization = """@prefix schema: <https://schema.org/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

[] schema:dateModified "today"^^xsd:string ."""
        self.assertEqual(
            rdflib.Graph().parse(data=serialization, format="turtle").serialize(format="turtle"),
            rdflib.Graph().parse(data=exception_serialization, format="turtle").serialize(format="turtle")
        )


