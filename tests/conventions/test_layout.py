import pathlib
import unittest

import h5py

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import generate_temporary_filename
from h5rdmtoolbox.conventions.layout import Layout
from h5rdmtoolbox.conventions.layout.attrs import LayoutAttributeManager, AttributeValidation
from h5rdmtoolbox.conventions.layout.group import Group
from h5rdmtoolbox.conventions.layout.path import LayoutPath
from h5rdmtoolbox.conventions.layout.registry import LayoutRegistry


class TestLayout(unittest.TestCase):

    def tearDown(self) -> None:
        pathlib.Path('test.pickle').unlink(missing_ok=True)
        pathlib.Path('test.hdf').unlink(missing_ok=True)

    def test_registry(self):
        self.assertIsInstance(Layout.Registry(), LayoutRegistry)

    def test_Layout(self):
        lay = Layout()
        self.assertIsInstance(lay, Layout)
        self.assertEqual(len(lay.validators), 0)

        grp = lay['/']
        self.assertIsInstance(grp, Group)
        self.assertEqual(grp.path, '/')
        self.assertIsInstance(grp.path, LayoutPath)
        self.assertEqual(grp.path.name, '')
        self.assertEqual(grp.path.parent, '/')

        grp2 = lay['/a/b/c']
        self.assertIsInstance(grp2, Group)
        self.assertEqual(grp2.path, '/a/b/c')
        self.assertIsInstance(grp2.path, LayoutPath)
        self.assertEqual(grp2.path.name, 'c')
        self.assertEqual(grp2.path.parent, '/a/b')

        self.assertEqual(len(lay.validators), 0)

    def test_root_attributes(self):
        lay = Layout()
        grp = lay['/']
        attrs = grp.attrs
        self.assertIsInstance(attrs, LayoutAttributeManager)

        attr_validator = attrs['version']
        self.assertIsInstance(attr_validator, AttributeValidation)
        self.assertEqual(attr_validator.key, 'version')
        self.assertEqual(attr_validator.validator, None)

        attr_validator.validator = h5tbx.__version__

        from h5rdmtoolbox.conventions.layout.attrs import AttributeEqual
        self.assertIsInstance(attr_validator.validator, AttributeEqual)
        self.assertEqual(len(lay.validations), 1)

        self.assertEqual(lay.validations[0], attr_validator)

        attrs['version2'] = h5tbx.__version__
        attrs['version2'] = h5tbx.__version__  # should not be added again!
        self.assertEqual(len(lay.validations), 2)

        print('\n', lay.validations)

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 2)

    # def test_root_attributes(self):
    #     lay = layout.File()
    #     lay['/'].attrs['version'] = h5tbx.__version__
    #     print(lay['/'].attrs['version'])
    #     lay['/'].attrs['version'] = h5tbx.__version__
    #     self.assertEqual(len(lay.validators), 1)
    #     with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
    #         res = lay.validate(h5)
    #     self.assertEqual(res.total_issues(), 1)

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

    def test_group_attributes_1(self):
        lay = layout.File()
        lay['/'].attrs['title'] = AnyAttribute()  # title must exist at root level
        self.assertEqual(len(lay.validators), 1)
        lay['*'].group().attrs['long_name'] = AnyAttribute()  # any group must have a long_name
        self.assertEqual(len(lay.validators), 2)
        lay['*'].group().attrs['long_name'] = AnyAttribute()  # any group must have a long_name
        self.assertEqual(len(lay.validators), 2)

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            h5.attrs['title2'] = 'test'  # issues=1
            h5.create_group('grp')  # no long_name --> issues=2
            h5.create_group('grp2')  # no long_name --> issues=3
            g = h5.create_group('grp2/subgrp')
            g.attrs['long_name'] = 'long name of the subgroup'
            h5.create_dataset('ds', shape=(3, 4))

        r = lay.validate(filename)
        r.report()
        self.assertEqual(r.total_issues(), 3)

    def test_group_attributes_2(self):
        lay = layout.File()
        lay['devices/*'].group().attrs['manufacturer'] = Any()  # any group must have a long_name
        self.assertEqual(len(lay.validators), 1)
        lay['devices/*'].group().attrs['manufacturer'] = Any()  # any group must have a long_name
        self.assertEqual(len(lay.validators), 1)

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            g = h5.create_group('grp')  # manufacture missing --> issues=1
            g.create_dataset('ds', shape=(3, 4))  # is a dataset, no issue --> issues=1

            d = h5.create_group('devices')  # manufacture missing --> issues=2
            dev1 = d.create_group('dev1')
            dev1.attrs['manufacturer'] = 'manufacturer1'  # manufacture existing --> issues=2

            dev1 = d.create_group('dev2')  # manufacture existing --> issues=3
            dev1.attrs['long_name'] = 'manufacturer2'

        r = lay.validate(filename)
        self.assertEqual(r.total_issues(), 3)

    def test_layout_part_datasets(self):
        lay = layout.File()
        lay['/'].dataset('velocity')  # .attrs['long_name'] = Any()  # any dataset must have a long_name
        # ds2 = lay['/'].dataset('velocity').shape = (3, 4)
        # ds2 = lay['/'].dataset('velocity').ndim = 2  # hardcode and then make it a variable implementation, only name needs some special treatment

        filename = generate_temporary_filename(suffix='.hdf')
        with h5py.File(filename, 'w') as h5:
            r = lay.validate(filename)
            r.report()
            self.assertEqual(r.total_issues(), 1)

            h5.create_dataset('velocity1', shape=(1, 2, 3))

            r = lay.validate(filename)
            r.report()
            self.assertEqual(r.total_issues(), 1)

            h5.create_dataset('velocity', shape=(1, 2, 3))

            r = lay.validate(filename)
            r.report()
            self.assertEqual(r.total_issues(), 0)

    def test_any_dataset(self):
        lay = layout.File()
        ds = lay['*'].dataset()
        # ds.attrs['standard_name'] = layout.Any()

        with h5py.File(generate_temporary_filename(suffix='.hdf'), 'w') as h5:
            h5.create_dataset('ds', shape=(3, 4))
            h5.create_dataset('a/b/c/data', shape=(3, 4, 4))
            d = h5.create_dataset('a/b/c/d/e/data', shape=(3, 4, 4, 2))
            d.attrs['standard_name'] = 'test'
            res = lay.validate(h5)
            self.assertEqual(res.total_issues(), 0)

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
