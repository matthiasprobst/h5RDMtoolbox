import unittest

import numpy as np
import rdflib

import h5rdmtoolbox as h5tbx


class TestReadme(unittest.TestCase):

    def test_quick_start(self):
        M4I = rdflib.Namespace("http://w3id.org/nfdi4ing/metadata4ing#")

        # Create a new HDF5 file with FAIR metadata
        with h5tbx.File("example.h5", "w") as h5:
            ds = h5.create_dataset("temperature", data=np.array([20, 21, 19, 22]))
            ds.attrs["units"] = h5tbx.Attribute(
                value="degree_Celsius",
                rdf_predicate=M4I.hasUnit,
                rdf_object="http://qudt.org/vocab/unit/DEG_C",
            )
            ds.attrs["description", "https://schema.org/description"] = "Room temperature measurements"

            ds_mean = h5.create_dataset("mean_temperature", data=np.mean(h5["temperature"][()]))
            ds_mean.attrs["units", M4I.hasUnit] = "degree_Celsius"
            ds_mean.rdf["units"].object = "http://qudt.org/vocab/unit/DEG_C"
            ds_mean.attrs["description", "https://schema.org/description"] = "Mean room temperature measurements"

            ds_mean.rdf.type = M4I.NumericalVariable
            ds_mean.rdf.data_predicate = M4I.hasNumericalValue

            ttl = h5.serialize("ttl", structural=True, contextual=False)
            print(ttl)
