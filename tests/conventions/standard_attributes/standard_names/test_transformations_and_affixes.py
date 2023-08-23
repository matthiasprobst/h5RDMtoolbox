import requests
import unittest
import warnings

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import tutorial
from h5rdmtoolbox.conventions.errors import AffixKeyError


class TestTransformationsAndAffixes(unittest.TestCase):

    def setUp(self) -> None:
        try:
            requests.get('https://git.scc.kit.edu', timeout=5)
            self.connected = True
        except (requests.ConnectionError,
                requests.Timeout) as e:
            self.connected = False
            warnings.warn('No internet connection', UserWarning)
        try:
            import pooch

            self.pooch_is_available = True
        except ImportError:
            self.pooch_is_available = False
            warnings.warn(f'Cannot test certain things about standard name table because "pooch" is not installed.')

        self.snt = h5tbx.tutorial.get_standard_name_table()

    def test_get_transformation(self):
        from h5rdmtoolbox.conventions.standard_names.affixes import _get_transformation, affix_transformations
        with self.assertRaises(KeyError):
            _get_transformation('invalid_transformation')
        self.assertEqual(affix_transformations['component'], _get_transformation('component'))

    def test_X_at_LOC(self):
        # X_at_LOC
        for sn in self.snt.standard_names:
            with self.assertRaises(AffixKeyError):
                self.snt[f'{sn}_at_fan']
        with self.assertRaises(AffixKeyError):
            self.snt['invalid_coordinate_at_fan']
        sn = self.snt['x_coordinate_at_fan_inlet']
        self.assertEqual(sn.units, self.snt['x_coordinate'].units)

    def test_difference_of_X_and_Y_between_LOC1_and_LOC2(self):
        # difference_of_X_and_Y_between_LOC1_and_LOC2
        self.snt['difference_of_x_coordinate_and_y_coordinate_between_fan_outlet_and_fan_inlet']

        affix = self.snt.affixes['location']
        self.assertEqual('location', affix.name)
        self.assertEqual(None, affix.description)
        affix._description = 'test_description'
        self.assertEqual('test_description', affix.description)

        for sn1 in self.snt.standard_names:
            for sn2 in self.snt.standard_names:
                for loc1 in self.snt.affixes['location'].values:
                    for loc2 in self.snt.affixes['location'].values:
                        if self.snt[sn1].units != self.snt[sn2].units:
                            with self.assertRaises(ValueError):
                                self.snt[f'difference_of_{sn1}_and_{sn2}_between_{loc1}_and_{loc2}']
                        else:
                            _sn = self.snt[f'difference_of_{sn1}_and_{sn2}_between_{loc1}_and_{loc2}']
                            self.assertEqual(_sn.units, self.snt[sn1].units)
                            self.assertEqual(_sn.units, self.snt[sn2].units)
                            self.assertEqual(_sn.description, f"Difference of {sn1} and {sn2} between {loc1} and "
                                                              f"{loc2}")
        with self.assertRaises(AffixKeyError):
            self.snt[f'difference_of_time_and_time_between_fan_inlet_and_INVALID']
        with self.assertRaises(AffixKeyError):
            self.snt[f'difference_of_time_and_time_between_INVALID_and_fan_outlet']

    def test_difference_of_X_and_Y_across_device(self):
        # difference_of_X_and_Y_across_device
        for sn1 in self.snt.standard_names:
            for sn2 in self.snt.standard_names:
                for dev in self.snt.affixes['device'].values:
                    if self.snt[sn1].units != self.snt[sn2].units:
                        with self.assertRaises(ValueError):
                            self.snt[f'difference_of_{sn1}_and_{sn2}_across_{dev}']
                    else:
                        _sn = self.snt[f'difference_of_{sn1}_and_{sn2}_across_{dev}']
                        self.assertEqual(_sn.units, self.snt[sn1].units)
                        self.assertEqual(_sn.units, self.snt[sn2].units)
                        if sn1 == sn2:
                            self.assertEqual(_sn.description, f"Difference of {sn1} and {sn2} across {dev}. "
                                                              f"{sn1}: {self.snt[sn1].description} "
                                                              f"{dev}: {self.snt.affixes['device'][dev]}")
                        else:
                            self.assertEqual(_sn.description, f"Difference of {sn1} and {sn2} across {dev}. "
                                                              f"{sn1}: {self.snt[sn1].description} "
                                                              f"{sn2}: {self.snt[sn2].description} "
                                                              f"{dev}: {self.snt.affixes['device'][dev]}")
        with self.assertRaises(AffixKeyError):
            self.snt[f'difference_of_time_and_time_across_INVALID']

    def test_ratio_of_X_and_Y(self):
        # ratio_of_X_and_Y
        for sn1 in self.snt.standard_names:
            for sn2 in self.snt.standard_names:
                _sn = self.snt[f'ratio_of_{sn1}_and_{sn2}']
                self.assertEqual(_sn.units, self.snt[sn1].units / self.snt[sn2].units)
                self.assertEqual(_sn.description, f"Ratio of {sn1} and {sn2}")

    def test_surface(self):
        from h5rdmtoolbox.conventions.standard_names.table import StandardNameTable
        snt = StandardNameTable.from_dict(
            {'name': 'test',
             'version': 'v1.2',
             'contact': h5tbx.__author_orcid__,
             'standard_names': {
                 'static_pressure': {'units': 'Pa',
                                     'description': 'Static pressure.'}
             },
             'affixes': {'surface': {
                 'wall': 'Wall.',
             }
             }
             }
        )
        with self.assertRaises(AffixKeyError):
            snt['invalid_static_pressure']
        _sn = snt['wall_static_pressure']
        self.assertEqual(_sn.units, snt['static_pressure'].units)
        self.assertEqual(_sn.description, f"Static pressure. Wall.")

    def test_derivative_of_X_with_respect_to_Y(self):
        uref = self.snt['x_velocity'].units / self.snt['x_coordinate'].units
        u = self.snt[f'derivative_of_x_velocity_wrt_x_coordinate'].units
        self.assertEqual(f'{uref}', f'{u}')

    def test_difference_of_X_across_device(self):
        # difference_of_X_across_device
        for sn in self.snt.standard_names:
            for dev in self.snt.affixes['device']:
                _sn = self.snt[f'difference_of_{sn}_across_{dev}']
                self.assertEqual(_sn.units, self.snt[sn].units)
                self.assertEqual(_sn.description, f"Difference of {sn} across {dev}")
        with self.assertRaises(AffixKeyError):
            self.snt[f'difference_of_{sn}_across_INVALID']

    def test_square_of_X(self):
        # square_of
        for sn in self.snt.standard_names:
            _sn = self.snt[f'square_of_{sn}']
            self.assertEqual(_sn.units, self.snt[sn].units * self.snt[sn].units)
            self.assertEqual(_sn.description, f"Square of {sn}")

    def test_standard_deviation_of(self):
        # standard_deviation_of
        for sn in self.snt.standard_names:
            _sn = self.snt[f'standard_deviation_of_{sn}']
            self.assertEqual(_sn.units, self.snt[sn].units)
            self.assertEqual(_sn.description, f"Standard deviation of {sn}")

    def test_arithmetic_mean_of(self):
        # arithmetic_mean_of
        for sn in self.snt.standard_names:
            _sn = self.snt[f'arithmetic_mean_of_{sn}']
            self.assertEqual(_sn.units, self.snt[sn].units)
            self.assertEqual(_sn.description, f"Arithmetic mean of {sn}")

    def test_magnitude_of(self):
        # magnitude_of
        for sn in self.snt.standard_names:
            _sn = self.snt[f'magnitude_of_{sn}']
            self.assertEqual(_sn.units, self.snt[sn].units)
            self.assertEqual(_sn.description, f"Magnitude of {sn}")

    def test_product_of_X_and_Y(self):
        # product_of_X_and_Y
        for sn1 in self.snt.standard_names:
            for sn2 in self.snt.standard_names:
                _sn = self.snt[f'product_of_{sn1}_and_{sn2}']
                self.assertEqual(_sn.units, self.snt[sn1].units * self.snt[sn2].units)
                self.assertEqual(_sn.description, f"Product of {sn1} and {sn2}")

    def test_in_frame(self):
        for sn in self.snt.standard_names:
            for frame in self.snt.affixes['reference_frame'].names:
                _sn = self.snt[f'{sn}_in_{frame}']
                self.assertEqual(_sn.units, self.snt[sn].units)
        with self.assertRaises(AffixKeyError):
            self.snt[f'{sn}_in_invalid_frame']
        with self.assertRaises(AffixKeyError):
            self.snt[f'{sn}_in_invalid_frame']