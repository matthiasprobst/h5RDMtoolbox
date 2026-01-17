import unittest

import numpy as np
import rdflib

import h5rdmtoolbox as h5tbx


class TestReadme(unittest.TestCase):

    def test_quick_start(self):
        M4I = rdflib.Namespace("http://w3id.org/nfdi4ing/metadata4ing#")

        # Create a new HDF5 file with FAIR metadata
        with h5tbx.File("example.h5", "w") as h5:
            h5.create_dataset("temperature", data=np.array([20, 21, 19, 22]))
            h5.attrs["units", M4I.hasUnit] = "degree_Celsius"
            h5.rdf["units"].object = "http://qudt.org/vocab/unit/DEG_C"
            h5.attrs["description", "https://schema.org/description"] = "Room temperature measurements"

            ttl = h5.serialize("ttl")
        print(ttl)
