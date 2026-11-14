import datetime
import numpy as np
import unittest
import xarray as xr

import h5rdmtoolbox as h5tbx

# noinspection PyUnresolvedReferences
from h5rdmtoolbox.science import units
from h5rdmtoolbox.extensions import onto


class TestExtension(unittest.TestCase):
    # Note: setUp removed - reset_convention fixture in conftest.py handles this

    def test_onto(self):
        with h5tbx.File() as h5:
            h5.onto.create_person(
                orcid_id="https://orcid.org/0000-0001-8729-0482",
                first_name="Matthias",
                last_name="Probst",
            )
            self.assertEqual(
                h5["Matthias_Probst"].attrs["orcid_id"],
                "https://orcid.org/0000-0001-8729-0482",
            )
            self.assertEqual(h5["Matthias_Probst"].attrs["first_name"], "Matthias")
            self.assertEqual(h5["Matthias_Probst"].attrs["last_name"], "Probst")
            self.assertEqual(
                h5["Matthias_Probst"].rdf.subject,
                "https://orcid.org/0000-0001-8729-0482",
            )

            h5.dumps()




    def test_units_to(self):
        with h5tbx.File(mode="w") as h5:
            ds = h5.create_dataset(
                "x", data=[1, 2, 3], make_scale=True, attrs={"units": "m"}
            )
            y = h5.create_dataset(
                "y", data=[1, 0, 1], attach_scale="x", attrs={"units": "mm"}
            )
            ds_cm = ds.to_units("cm")[()]
            self.assertEqual("cm", ds_cm.attrs["units"])

            y_cm = y.to_units("cm")[()]
            self.assertEqual("cm", y_cm.attrs["units"])

            y_xcm = y.to_units({"x": "cm"})[()]
            self.assertEqual("mm", y_xcm.attrs["units"])
            self.assertEqual("cm", y_xcm.x.attrs["units"])

            y_xcm = y.to_units(x="cm")[()]
            self.assertEqual("mm", y_xcm.attrs["units"])
            self.assertEqual("cm", y_xcm.x.attrs["units"])
