import matplotlib.pyplot as plt
import unittest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import plotting


class TestPlotting(unittest.TestCase):

    def test_decode_label(self):
        self.assertTupleEqual(('test', ''), plotting.decode_label('test'))
        self.assertEqual(('test ', 'm/s'), plotting.decode_label('test [m/s]'))

    def test_build_label_unit_str(self):
        label_str = plotting.build_label_unit_str('velocity', 'm/s', units_format='/')
        self.assertEqual('velocity / $m/s$', label_str)

        with self.assertRaises(ValueError):
            plotting.build_label_unit_str('velocity', 'm/s', units_format='?')

        label_str = plotting.build_label_unit_str('velocity', 'm/s', units_format='(')
        self.assertEqual('velocity ($m/s$)', label_str)

        label_str = plotting.build_label_unit_str('velocity', 'm/s', units_format='[')
        self.assertEqual('velocity [$m/s$]', label_str)

        with h5tbx.set_config(xarray_unit_repr_in_plots='in'):
            label_str = plotting.build_label_unit_str('velocity', 'm/s', units_format=None)
            self.assertEqual('velocity in $m/s$', label_str)

        self.assertEqual("velocity [$m/s$]",
                         plotting.XarrayLabelManipulation._adjust_units_label('velocity [m/s]', units_format='['))

        self.assertEqual("velocity ($m/s$)",
                         plotting.XarrayLabelManipulation._adjust_units_label('velocity [m/s]', units_format='('))

        self.assertEqual("velocity",
                         plotting.XarrayLabelManipulation._adjust_units_label('velocity', units_format='('))

        self.assertEqual("velocity",
                         plotting.XarrayLabelManipulation._adjust_units_label('velocity []', units_format='('))

        with h5tbx.set_config(xarray_unit_repr_in_plots='in'):
            self.assertEqual("velocity in $m/s$",
                             plotting.XarrayLabelManipulation._adjust_units_label('velocity [m/s]', units_format=None))

        self.assertEqual(None,
                         plotting.XarrayLabelManipulation._adjust_units_label(None))

        with h5tbx.use(None):
            with h5tbx.File() as h5:
                h5.create_dataset('x', data=[1, 2, 3],
                                  make_scale=True,
                                  attrs=dict(units='m',
                                             long_name='x_long_name'))
                h5.create_dataset('velocity', data=[5.3, 6.2, 7.1],
                                  attrs=dict(units='m/s',
                                             long_name='velocity'))
                plt.figure()
                ax = plt.gca()
                with h5tbx.set_config(xarray_unit_repr_in_plots='['):
                    h5['velocity'][()].plot(ax=ax)
                self.assertEqual(ax.get_xlabel(), f'dim_0')
                self.assertEqual(ax.get_ylabel(), f'velocity [$m/s$]')
                plt.close()

                h5['velocity'].dims[0].attach_scale(h5['x'])
                plt.figure()
                ax = plt.gca()
                with h5tbx.set_config(xarray_unit_repr_in_plots='['):
                    h5['velocity'][()].plot(ax=ax)
                self.assertEqual(ax.get_xlabel(), f'x_long_name [$m$]')
                self.assertEqual(ax.get_ylabel(), f'velocity [$m/s$]')
                plt.close()

                plt.figure()
                ax = plt.gca()
                with h5tbx.set_config(xarray_unit_repr_in_plots='('):
                    h5['velocity'][()].plot(ax=ax)
                self.assertEqual(ax.get_xlabel(), f'x_long_name ($m$)')
                self.assertEqual(ax.get_ylabel(), f'velocity ($m/s$)')
                plt.close()

                plt.figure()
                ax = plt.gca()
                with h5tbx.set_config(xarray_unit_repr_in_plots='('):
                    h5['velocity'][()].plot(ax=ax)
                    ax.set_xlabel('x [mm]')
                    ax.set_ylabel('velocity [km/s]')
                    self.assertEqual(ax.get_xlabel(), f'x ($mm$)')
                    self.assertEqual(ax.get_ylabel(), f'velocity ($km/s$)')

                    ax.set_xlabel(h5['x'][()])
                    ax.set_ylabel(h5['velocity'][()])
                    self.assertEqual(ax.get_xlabel(), f'x_long_name ($m$)')
                    self.assertEqual(ax.get_ylabel(), f'velocity ($m/s$)')

                    x = h5['x'][()]
                    x.attrs = {'units': 'm'}
                    v = h5['velocity'][()]
                    v.attrs = {'units': 'm/s'}
                    ax.set_xlabel(x)
                    ax.set_ylabel(v)
                    self.assertEqual(ax.get_xlabel(), f'x ($m$)')
                    self.assertEqual(ax.get_ylabel(), f'velocity ($m/s$)')
                plt.close()

                plt.figure()
                ax = plt.gca()
                with h5tbx.set_config(xarray_unit_repr_in_plots='('):
                    h5['velocity'][()].plot(ax=ax)
                ax.set_xylabel('x', 'y')
                self.assertEqual(ax.get_xlabel(), f'x')
                self.assertEqual(ax.get_ylabel(), f'y')
                plt.close()

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
