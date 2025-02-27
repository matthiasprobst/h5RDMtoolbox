import unittest

import h5rdmtoolbox as h5tbx


class TestLazy(unittest.TestCase):

    def test_lazy_on_datasets_with_coords(self):
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[-1, 0, 1], make_scale=True)
            h5.create_dataset('y', data=5)
            h5.create_dataset('time', data=[0, 1, 2], make_scale=True)
            h5.create_dataset('data', data=[10, 20, 30],
                              attach_scale=(('x', 'time'),))
            h5.data.assign_coord(h5.y)
            h5tbx.lazy(h5.data)

    def test_lazyObject(self):
        self.assertEqual(h5tbx.lazy(None), None)

        with self.assertRaises(TypeError):
            h5tbx.lazy(1)

        with h5tbx.File() as h5:
            h5.attrs['name'] = 'test'
            h5.create_dataset('x', data=[-1, 0, 1], make_scale=True)
            h5.create_dataset('grp/test', data=[1, 2, 3], attach_scale=h5['x'])

            lroot_grp = h5tbx.lazy(h5)
            self.assertEqual(lroot_grp.name, '/')
            l_dataset = h5tbx.lazy(h5.grp.test)

        self.assertEqual(lroot_grp.name, '/')
        self.assertEqual(lroot_grp.filename, h5.hdf_filename)
        self.assertEqual(lroot_grp.attrs['name'], 'test')

        self.assertTrue(lroot_grp < l_dataset)

        self.assertIsInstance(lroot_grp, h5tbx.database.lazy.LGroup)

        self.assertIsInstance(l_dataset, h5tbx.database.lazy.LDataset)
        self.assertEqual(l_dataset.name, '/grp/test')
        self.assertEqual(l_dataset.filename, h5.hdf_filename)
        self.assertEqual(l_dataset.basename, 'test')
        self.assertEqual(l_dataset.parentname, '/grp')
        self.assertEqual(l_dataset.parentnames, ['grp'])

        self.assertListEqual(list(lroot_grp.keys()), ['grp', 'x'])

        self.assertIsInstance(lroot_grp['grp'], h5tbx.database.lazy.LGroup)
        self.assertEqual(lroot_grp['grp'].name, '/grp')

        self.assertIsInstance(lroot_grp['grp']['test'], h5tbx.database.lazy.LDataset)
        self.assertEqual(lroot_grp['grp']['test'].name, '/grp/test')

        self.assertEqual(l_dataset.isel(x=0), 1)
        self.assertEqual(l_dataset.isel(x=1), 2)
        self.assertEqual(l_dataset.isel(x=2), 3)

        self.assertEqual(l_dataset.sel(x=-1), 1)
        self.assertEqual(l_dataset.sel(x=0), 2)
        self.assertEqual(l_dataset.sel(x=1), 3)
