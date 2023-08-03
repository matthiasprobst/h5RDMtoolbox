import matplotlib.pyplot as plt
import unittest

import h5rdmtoolbox as h5tbx


class TestPlotting(unittest.TestCase):

    def test_label(self):
        h5tbx.use(None)
        with h5tbx.File() as h5:
            h5.create_dataset('x', data=[1, 2, 3],
                              make_scale=True,
                              attrs=dict(units='m/s',
                                         long_name='x_long_name'))

            h5tbx.set_config(xarray_unit_repr_in_plots='[]')
            h5['x'][()].plot()
            self.assertEqual("x_long_name [$m/s$]", plt.gca().get_ylabel())
            plt.close()

            h5tbx.set_config(xarray_unit_repr_in_plots='/')
            h5['x'][()].plot()
            self.assertEqual("x_long_name / $m/s$", plt.gca().get_ylabel())
            plt.close()

            h5tbx.set_config(xarray_unit_repr_in_plots='in')
            h5['x'][()].plot()
            self.assertEqual("x_long_name in $m/s$", plt.gca().get_ylabel())
            plt.close()

            h5tbx.set_config(xarray_unit_repr_in_plots='()')
            h5['x'][()].plot()
            self.assertEqual("x_long_name ($m/s$)", plt.gca().get_ylabel())
            plt.close()

            h5.create_dataset('y', data=[1, 2, 3],
                              attach_scale=h5['x'],
                              attrs=dict(units='Pa',
                                         long_name='y_long_name', ))

            plt.figure()
            h5tbx.set_config(xarray_unit_repr_in_plots='()')
            h5['y'][()].plot()
            self.assertEqual("x_long_name ($m/s$)", plt.gca().get_xlabel())
            self.assertEqual("y_long_name ($Pa$)", plt.gca().get_ylabel())
            plt.close()
