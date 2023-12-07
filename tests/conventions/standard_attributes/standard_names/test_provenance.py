import numpy as np
import unittest

import h5rdmtoolbox as h5tbx
# noinspection PyUnresolvedReferences
from h5rdmtoolbox.conventions.standard_names import accessor


class TestProvenance(unittest.TestCase):

    def setUp(self) -> None:
        cv = h5tbx.conventions.from_zenodo('https://zenodo.org/record/10156750', overwrite=True, force_download=True)

        h5tbx.use(cv)
        with h5tbx.File(data_type='experimental', contact=h5tbx.__author_orcid__) as h5:
            h5.create_dataset('time', data=np.linspace(0, 5, 5), standard_name='time', units='s', make_scale=True)
            h5.create_dataset('y', data=np.linspace(0, 10, 10), standard_name='y_coordinate', units='m',
                              make_scale=True)
            h5.create_dataset('x', data=np.linspace(0, 7, 7), standard_name='x_coordinate', units='m', make_scale=True)
            h5.create_dataset('u', data=np.random.rand(5, 10, 7), standard_name='x_velocity', units='m/s',
                              attach_scale=('time', 'y', 'x'))
        self.filename = h5.hdf_filename

    def tearDown(self) -> None:
        h5tbx.use(None)

    def test_provenance_basics(self):
        with h5tbx.set_config(add_provenance=True):
            with h5tbx.File(self.filename) as h5:
                u = h5.u[:]

            u_mean = u.snt[0:2, ...].snt.arithmetic_mean_of(dim='time')

            # u_mean = u.snt.arithmetic_mean_of()
            self.assertTrue('PROVENANCE' in u_mean.attrs)
            self.assertIn('__getitem__', u_mean.attrs['PROVENANCE']['processing_history'][0]['name'])
            self.assertIn('arithmetic_mean_of', u_mean.attrs['PROVENANCE']['processing_history'][1]['name'])

            with h5tbx.File(data_type='experimental', contact=h5tbx.__author_orcid__) as h5:
                h5.create_dataset('u_mean', data=u_mean)
                um = h5['u_mean'][()]

            self.assertTrue('PROVENANCE' in um.attrs)
            self.assertIn('__getitem__', u_mean.attrs['PROVENANCE']['processing_history'][0]['name'])
            self.assertIn('arithmetic_mean_of', um.attrs['PROVENANCE']['processing_history'][1]['name'])

    def test_rolling_mean(self):
        with h5tbx.set_config(add_provenance=True):
            with h5tbx.File(self.filename) as h5:
                u = h5.u[:]
                window = 2
                u_rmean = u.snt[0:2, ...].snt.rolling(time=window).mean()
            self.assertIn('__getitem__', u_rmean.attrs['PROVENANCE']['processing_history'][0]['name'])
            self.assertIn('rolling_mean', u_rmean.attrs['PROVENANCE']['processing_history'][1]['name'])
            self.assertEqual([2], u_rmean.attrs['PROVENANCE']['processing_history'][1]['window'])

            with h5tbx.File(data_type='experimental', contact=h5tbx.__author_orcid__) as h5:
                h5.create_dataset('u_rmean', data=u_rmean)
                u_rmean2 = h5['u_rmean'][()]

            self.assertIn('__getitem__', u_rmean2.attrs['PROVENANCE']['processing_history'][0]['name'])
            self.assertIn('rolling_mean', u_rmean2.attrs['PROVENANCE']['processing_history'][1]['name'])
            self.assertEqual([2], u_rmean2.attrs['PROVENANCE']['processing_history'][1]['window'])

    def test_rolling_max(self):
        with h5tbx.set_config(add_provenance=True):
            with h5tbx.File(self.filename) as h5:
                u = h5.u[:]
                window = 2
                u_rmax = u.snt[0:2, ...].snt.rolling(time=window).max()
            self.assertIn('__getitem__', u_rmax.attrs['PROVENANCE']['processing_history'][0]['name'])
            self.assertIn('rolling_max', u_rmax.attrs['PROVENANCE']['processing_history'][1]['name'])
            self.assertEqual([2], u_rmax.attrs['PROVENANCE']['processing_history'][1]['window'])

            with h5tbx.File(data_type='experimental', contact=h5tbx.__author_orcid__) as h5:
                h5.create_dataset('u_rmax', data=u_rmax)
                u_rmean2 = h5['u_rmax'][()]

            self.assertIn('__getitem__', u_rmean2.attrs['PROVENANCE']['processing_history'][0]['name'])
            self.assertIn('rolling_max', u_rmean2.attrs['PROVENANCE']['processing_history'][1]['name'])
            self.assertEqual([2], u_rmean2.attrs['PROVENANCE']['processing_history'][1]['window'])

    def test_rolling_std(self):
        with h5tbx.set_config(add_provenance=True):
            with h5tbx.File(self.filename) as h5:
                u = h5.u[:]
                window = 2
                u_rstd = u.snt[0:2, ...].snt.rolling(time=window).std()
            self.assertIn('__getitem__', u_rstd.attrs['PROVENANCE']['processing_history'][0]['name'])
            self.assertIn('rolling_std_of', u_rstd.attrs['PROVENANCE']['processing_history'][1]['name'])
            self.assertEqual([2], u_rstd.attrs['PROVENANCE']['processing_history'][1]['window'])

            with h5tbx.File(data_type='experimental', contact=h5tbx.__author_orcid__) as h5:
                h5.create_dataset('u_rstd', data=u_rstd)
                u_rmean2 = h5['u_rstd'][()]

            self.assertIn('__getitem__', u_rmean2.attrs['PROVENANCE']['processing_history'][0]['name'])
            self.assertIn('rolling_std_of', u_rmean2.attrs['PROVENANCE']['processing_history'][1]['name'])
            self.assertEqual([2], u_rmean2.attrs['PROVENANCE']['processing_history'][1]['window'])
