import numpy as np
import unittest

import h5rdmtoolbox as h5tbx
# noinspection PyUnresolvedReferences
from h5rdmtoolbox.conventions.standard_names import accessor


class TestProvenance(unittest.TestCase):

    def test_provenance(self):
        cv = h5tbx.conventions.from_zenodo('https://zenodo.org/record/8301535')

        h5tbx.use(cv)

        with h5tbx.File(data_type='experimental', contact=h5tbx.__author_orcid__) as h5:
            h5.create_dataset('time', data=np.linspace(0, 5, 5), standard_name='time', units='s', make_scale=True)
            h5.create_dataset('y', data=np.linspace(0, 10, 10), standard_name='y_coordinate', units='m',
                              make_scale=True)
            h5.create_dataset('x', data=np.linspace(0, 7, 7), standard_name='x_coordinate', units='m', make_scale=True)
            h5.create_dataset('u', data=np.random.rand(5, 10, 7), standard_name='x_velocity', units='m/s',
                              attach_scale=('time', 'y', 'x'))
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
