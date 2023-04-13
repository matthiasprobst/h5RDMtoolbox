import pathlib
import unittest

import h5py

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox.conventions import layout
from h5rdmtoolbox.conventions.layout.file import LayoutRegistry
from h5rdmtoolbox.conventions.layout.validation import Any
from h5rdmtoolbox.conventions.layout.validation import Message
from h5rdmtoolbox.conventions.layout.validation.attribute import AnyAttribute, AttributeValidator


class TestLayout(unittest.TestCase):

    def tearDown(self) -> None:
        pathlib.Path('test.pickle').unlink(missing_ok=True)
        pathlib.Path('test.hdf').unlink(missing_ok=True)

    def test_registry(self):
        self.assertIsInstance(layout.File.Registry(), LayoutRegistry)

    def test_root_attributes(self):
        lay = layout.File()
        lay['/'].attrs['version'] = h5tbx.__version__
        lay['/'].attrs['version'] = h5tbx.__version__
        self.assertEqual(len(lay.validators), 1)
        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            res = lay.validate(h5)
        self.assertEqual(res.total_issues(), 1)

    def test_attribute_user_defined_validator(self):
        class StartsWithValidator(AttributeValidator):

            def __init__(self, reference):
                super().__init__(reference, False)

            def validate(self, key, target):
                if not self.is_optional:
                    if key not in target.attrs:
                        self.failure_message = Message(f'Attribute "{key}" does not exist in {target.name}')
                        return False
                if target.attrs[key].startswith(self.reference):
                    return True
                return False

        lay = layout.File()
        lay['/'].attrs['my_attribute'] = StartsWithValidator('test')
        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            h5.attrs['my_attribute'] = 'test_this_is'
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 0)
            h5.attrs['my_attribute'] = 'my attribute'
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 1)

    def test_wildcard_attributes(self):
        lay = layout.File()
        with self.assertRaises(TypeError):
            lay['*'].attrs['long_name'] = Any
        lay['*'].attrs['long_name'] = Any()
        self.assertEqual(len(lay.validators), 1)
        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            res = lay.validate(h5)
        self.assertEqual(res.total_issues(), 0)
        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            h5.create_group('grp')
            res = lay.validate(h5)
        self.assertEqual(res.total_issues(), 1)
        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            h5.create_group('grp')
            h5.create_group('grp2')
            g = h5.create_group('grp2/subgrp')
            g.attrs['long_name'] = 'my long name'
            res = lay.validate(h5)
        self.assertEqual(res.total_issues(), 2)

    def test_layout_part1(self):
        lay = layout.File()
        lay['/'].attrs['title'] = AnyAttribute()  # title must exist at root level
        self.assertEqual(len(lay.validators), 1)
        lay['*'].group().attrs['long_name'] = AnyAttribute()  # any group must have a long_name
        self.assertEqual(len(lay.validators), 2)
        lay['*'].group().attrs['long_name'] = AnyAttribute()  # any group must have a long_name
        self.assertEqual(len(lay.validators), 2)

        pickle_filename = generate_temporary_filename(suffix='.pickle')
        lay.save(pickle_filename, overwrite=True)
        lay_loaded = layout.File.load(pickle_filename)

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            h5.attrs['title2'] = 'test'  # issues=1
            h5.create_group('grp')  # issues=2
            h5.create_group('grp2')  # issues=3
            g = h5.create_group('grp2/subgrp')
            g.attrs['long_name'] = 'long name of the subgroup'
            h5.create_dataset('ds', shape=(3, 4))

        r = lay_loaded.validate(filename)

        self.assertEqual(r.total_issues(), 3)

        # long name is optional
        lay = layout.File()
        lay['/'].attrs['title'] = Any()  # title must exist at root level
        lay['*'].group().attrs['long_name'] = Any(optional=True)  # any group must have a long_name
        self.assertEqual(len(lay.validators), 2)
        lay['*'].group().attrs['long_name'] = Any(optional=True)  # any group must have a long_name
        self.assertEqual(len(lay.validators), 2)

        pickle_filename = generate_temporary_filename(suffix='.pickle')
        lay.save(pickle_filename, overwrite=True)
        lay_loaded = layout.File.load(pickle_filename)

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            h5.attrs['title2'] = 'test'  # issues=1
            h5.create_group('grp')  # issues=2
            h5.create_group('grp2')  # issues=3
            g = h5.create_group('grp2/subgrp')
            g.attrs['long_name'] = 'long name of the subgroup'
            h5.create_dataset('ds', shape=(3, 4))

        r = lay_loaded.validate(filename)

        self.assertEqual(r.total_issues(), 1)

    def test_layout_part2(self):
        lay = layout.File()
        lay['devices/*'].group().attrs['manufacturer'] = Any()  # any group must have a long_name
        self.assertEqual(len(lay.validators), 1)
        lay['devices/*'].group().attrs['manufacturer'] = Any()  # any group must have a long_name
        self.assertEqual(len(lay.validators), 1)
        lay.save('test.pickle', overwrite=True)
        lay_loaded = layout.File.load('test.pickle')

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            g = h5.create_group('grp')
            g.create_dataset('ds', shape=(3, 4))

            d = h5.create_group('devices')
            dev1 = d.create_group('dev1')
            dev1.attrs['manufacturer'] = 'manufacturer1'
            dev1 = d.create_group('dev2')
            dev1.attrs['long_name'] = 'manufacturer2'

        r = lay_loaded.validate(filename)
        self.assertEqual(r.total_issues(), 1)

    def test_layout_part_datasets_3(self):
        lay = layout.File()
        lay['*'].dataset().attrs['long_name'] = Any()  # any group must have a long_name
        lay.save('test.pickle', overwrite=True)
        lay_loaded = layout.File.load('test.pickle')

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            g = h5.create_group('grp')
            g.create_dataset('ds', shape=(3, 4))

            d = h5.create_group('devices')
            dev1 = d.create_group('dev1')
            dev1.attrs['manufacturer'] = 'manufacturer1'

        r = lay_loaded.validate(filename)

        self.assertEqual(r.total_issues(), 1)

    def test_layout_part_datasets_4(self):
        """check if all datasets are 3D and have a long_name attribute"""
        lay = layout.File()
        lay['*'].dataset(ndim=3).attrs['long_name'] = Any()
        lay.save('test.pickle', overwrite=True)
        lay_loaded = layout.File.load('test.pickle')

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            h5.create_dataset('ds', shape=(3, 4))  # not dim=3 and no long_name --> 2 issues
            h5.create_dataset('a/b/c/data', shape=(3, 4, 4))  # dim==3 but no long_name --> 1 issue
            h5.create_dataset('a/b/c/d/e/data', shape=(3, 4, 4, 2))  # not dim=3 and no long_name --> 2 issues
            d = h5.create_dataset('a/b/c/d/e/data2', shape=(3, 4, 4, 2))  # not dim=3 but long_name --> 1 issue
            d.attrs['long_name'] = 'long name of the dataset'
        r = lay_loaded.validate(filename)

        self.assertEqual(r.total_issues(), 6)

    def test_layout_part_datasets_5(self):
        """check if all datasets "velocity" are 3D and have a long_name attribute"""
        lay = layout.File()
        lay['/'].dataset(name='velocity', ndim=3)
        lay.save('test.pickle', overwrite=True)
        lay_loaded = layout.File.load('test.pickle')

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            h5.create_dataset('ds', shape=(3, 4))  # not dim=3 and no long_name
            h5.create_dataset('ds2', shape=(3, 4))  # not dim=3 and no long_name
            h5.create_dataset('grp/velocity', shape=(3, 4, 5))  # not at root level

        r = lay_loaded.validate(filename)

        # velocity not in file will raise one issue
        self.assertEqual(r.total_issues(), 1)

    def test_layout_part_datasets_6(self):
        # now with a velocity dataset and correct shape
        lay = layout.File()
        lay['/'].dataset(name='velocity', ndim=3)
        lay.save('test.pickle', overwrite=True)
        lay_loaded = layout.File.load('test.pickle')

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            h5.create_dataset('velocity', shape=(3, 4, 5))  # not at root level

        r = lay_loaded.validate(filename)

        # velocity not in file will raise one issue
        self.assertEqual(r.total_issues(), 0)

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            h5.create_dataset('velocity', shape=(3, 4, 5, 1))  # not at root level

        r = lay_loaded.validate(filename)

        # velocity not in file will raise one issue
        self.assertEqual(r.total_issues(), 1)

    def test_layout_part_datasets_7(self):
        """same as before, but now with wildcard"""
        lay = layout.File()
        lay['grp/*'].dataset(name='velocity', ndim=3)
        lay.save('test.pickle', overwrite=True)
        lay_loaded = layout.File.load('test.pickle')

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            h5.create_dataset('ds', shape=(3, 4))  # not dim=3 and no long_name
            h5.create_dataset('grp/not_a_velocity', shape=(3, 4, 5))  # not at root level
            h5.create_dataset('grp/velocity', shape=(3, 4, 5))  # not at root level
            h5.create_dataset('grp/subgrp/velocity', shape=(3, 4, 5))  # not at root level
            h5.create_dataset('grp/subgrp/b/velocity', shape=(3, 4))  # not at root level

        r = lay_loaded.validate(filename)

        # velocity not in file will raise one issue
        self.assertEqual(r.total_issues(), 1)

    def test_layout_regex(self):
        lay = layout.File()
        lay['/'].dataset(name=layout.Regex('^[x-z]_coordinate'),
                         ndim=1)  # e.g. x_coordinate, y_coordinate, z_coordinate shall be 1D

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            h5.create_dataset('x_coordinate', shape=(3,))

        lay.validate(filename).print()

    def test_group_1(self):
        lay = layout.File()
        lay['/'].group('device')  # group /device must exist
        print(lay)

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 1)
            h5.create_group('device1')
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 1)
            h5.create_group('device')
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 0)
            h5.create_group('subgrp/device')
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 0)

    def test_group_2(self):
        lay = layout.File()
        lay['*'].group('device')  # group "device" expected at any position in the file
        print(lay)

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 0)

            h5.create_group('device1')
            h5.create_group('subgrp/devices')
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 0)

            h5.create_group('device')
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 0)
            del h5['device']
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 0)

            h5.create_group('subgrp/device')
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 0)

    # def test_layout_(self):
    #     lay = layout.File()
    #     lay['/'].attrs['title'] = Any()
    #     lay['/'].attrs['comment'] = Optional[Any()]
    #     lay['/'].attrs['version'] = Optional[Rule.Equal('v0.0.0')]
    #
    #     # the orcid is optional, but if present, it must be a valid orcid
    #     orcid_pattern = '^[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]$'
    #     lay['/'].attrs['orcid'] = Optional[Rule.Regex(orcid_pattern)]
    #     # lay['/'].attrs['orcid'] = Optional[Rule(re.match())]  # lambda function for user-defined?!
    #
    #     # *=any group in the file from '/' onwards
    #     lay['*'].dataset(name='velocity',
    #                      shape=(3, 4))
    #
    #     lay['/grp/subgrp/*'] = Optional[LayoutDataset(name='velocity',
    #                                                   shape=(20, 10))]
    #     # equal to: any dataset in group below grp/subgrp which's name is velocity shall have this shape:
    #     # note: if optional=False, then any group MUST have a dataset velocity
    #     # note2: if the dataset name does not matter, pass name='*'
    #     lay['/grp/subgrp/*'] = LayoutDataset(name='velocity',
    #                                          shape=(20, 10),
    #                                          optional=True)
    #
    #     grp = lay['devices']
    #     grp.attrs['long_name'] = Any()  # '*.'  # any
    #     grp.dataset(name='device1')
    #     # lay[Target.AnyDataset].attrs['long_name'] = Any()
    #     # lay[Target.AnyDataset].shape = (3, 4)
    #
    #     with h5py.File(filename, 'w') as h5:
    #         h5.create_dataset('velocity', shape=(3, 5))
    #         # lay.validate(h5.filename)
