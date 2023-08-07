import requests
import unittest
import warnings

import h5rdmtoolbox as h5tbx


class TestConventions(unittest.TestCase):

    def setUp(self) -> None:
        try:
            requests.get('https://git.scc.kit.edu', timeout=5)
            self.connected = True
        except (requests.ConnectionError,
                requests.Timeout) as e:
            self.connected = False
            warnings.warn('No internet connection', UserWarning)

    def test_use(self):
        h5tbx.use(h5tbx.get_config()['default_convention'])
        self.assertEqual(h5tbx.conventions.get_current_convention().name, h5tbx.get_config()['default_convention'])
        h5tbx.use(None)
        self.assertEqual(h5tbx.conventions.get_current_convention().name, 'h5py')
        h5tbx.use('h5py')
        self.assertEqual(h5tbx.conventions.get_current_convention().name, 'h5py')
        h5tbx.use('h5tbx')
        self.assertEqual(h5tbx.conventions.get_current_convention().name, 'h5tbx')
        with self.assertRaises(ValueError):
            h5tbx.use('invalid_convention')

    def test_from_yaml(self):
        with open(h5tbx.utils.generate_temporary_filename(suffix='.yaml'), 'w') as f:
            f.write("""name: test""")
        with self.assertRaises(ValueError):
            cv = h5tbx.conventions.from_yaml(f.name)

        with open(h5tbx.utils.generate_temporary_filename(suffix='.yaml'), 'w') as f:
            f.write("""__name__: test""")
        with self.assertRaises(ValueError):
            cv = h5tbx.conventions.from_yaml(f.name)

        with open(h5tbx.utils.generate_temporary_filename(suffix='.yaml'), 'w') as f:
            f.writelines(['__name__: test\n', '__contact__: me'])

        cv = h5tbx.conventions.from_yaml(f.name)
        self.assertEqual(cv.name, 'test')
        self.assertEqual(cv.contact, 'me')

        f1 = h5tbx.utils.generate_temporary_filename(suffix='.yaml')
        f2 = h5tbx.utils.generate_temporary_filename(suffix='.yaml')
        with open(f1, 'w') as f:
            f.writelines(['__name__: test\n', '__contact__: me'])

        with open(f2, 'w') as f:
            f.writelines(['__name__: test\n', '__contact__: me'])

        with self.assertRaises(NotImplementedError):
            cv = h5tbx.conventions.from_yaml([f1, f2])

    def test_cv_h5tbx(self):
        h5tbx.use('h5tbx')
        with h5tbx.File() as h5:
            with self.assertRaises(h5tbx.errors.StandardAttributeError):
                h5.create_dataset('test', data=1)
        h5tbx.use(None)

    def test_from_zenodo(self):
        if self.connected:
            h5tbx.UserDir.clear_cache()
            with self.assertRaises(ValueError):  # because it is not a standard attribute YAML file!
                cv = h5tbx.conventions.from_zenodo(doi=8211688)
