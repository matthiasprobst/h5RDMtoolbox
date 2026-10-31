"""Unit tests for h5rdmtoolbox.config"""
import unittest
import pytest

import h5rdmtoolbox as h5tbx
from h5rdmtoolbox import File
from h5rdmtoolbox.wrapper import core


@pytest.mark.parametrize('order', [[], ['unknown'], ['long_name', 'unknown'], 'long_name'])
def test_invalid_plotting_order_does_not_change_config(order):
    original = h5tbx.get_config('plotting_name_order')
    with pytest.raises(ValueError, match='plotting_name_order'):
        h5tbx.set_config(plotting_name_order=order)
    assert h5tbx.get_config('plotting_name_order') == original


@pytest.mark.parametrize('order', [('long_name', 'plot_name'), ['standard_name']])
def test_valid_plotting_order_is_restored(order):
    original = h5tbx.get_config('plotting_name_order')
    with h5tbx.set_config(plotting_name_order=order):
        assert h5tbx.get_config('plotting_name_order') == order
    assert h5tbx.get_config('plotting_name_order') == original


def test_compression_defaults_can_be_restored(tmp_path):
    with h5tbx.set_config(hdf_compression='gzip', hdf_compression_opts=1):
        with h5tbx.set_config(hdf_compression=None, hdf_compression_opts=None):
            with h5tbx.File(tmp_path / 'uncompressed.hdf', 'w') as h5:
                assert h5.create_dataset('data', data=[1, 2]).compression is None
        with h5tbx.File(tmp_path / 'compressed.hdf', 'w') as h5:
            assert h5.create_dataset('data', data=[1, 2]).compression == 'gzip'


def test_nested_config_restores_registry_format_after_exception():
    registry = h5tbx.get_ureg()
    original_config = h5tbx.get_config('ureg_format')
    original_format = registry.formatter.default_format
    try:
        with h5tbx.set_config(ureg_format='~P'):
            assert registry.formatter.default_format == '~P'
            with pytest.raises(RuntimeError):
                with h5tbx.set_config(ureg_format='~L'):
                    raise RuntimeError('leave inner context')
            assert h5tbx.get_config('ureg_format') == '~P'
            assert registry.formatter.default_format == '~P'
        assert registry.formatter.default_format == original_format
        assert h5tbx.get_config('ureg_format') == original_config
    finally:
        h5tbx.set_config(ureg_format=original_config)


@pytest.mark.parametrize('invalid', [{'unknown_setting': True}, {'require_unit': 'invalid'}])
def test_invalid_batch_does_not_change_registry(invalid):
    registry = h5tbx.get_ureg()
    original = h5tbx.get_config().copy()
    original_format = registry.formatter.default_format
    try:
        with pytest.raises((KeyError, ValueError)):
            h5tbx.set_config(ureg_format='~L', **invalid)
        assert h5tbx.get_config() == original
        assert registry.formatter.default_format == original_format
    finally:
        h5tbx.set_config(ureg_format=original['ureg_format'])


class TestConfig(unittest.TestCase):

    def test_set_logger(self):
        with h5tbx.set_config(init_logger_level='DEBUG'):
            self.assertEqual(h5tbx.get_config()['init_logger_level'], 'DEBUG')
        with h5tbx.set_config(init_logger_level=10):
            self.assertEqual(h5tbx.get_config()['init_logger_level'], 10)
        with self.assertRaises(ValueError):
            with h5tbx.set_config(init_logger_level='invalid'):
                pass
        with self.assertRaises(ValueError):
            with h5tbx.set_config(init_logger_level=100):
                pass

        with self.assertRaises(KeyError):
            with h5tbx.set_config(invalid='invalid'):
                pass

        with self.assertRaises(ValueError):
            with h5tbx.set_config(init_logger_level=3.4):
                pass

    def test_config_type(self):
        self.assertIsInstance(h5tbx.get_config('xarray_unit_repr_in_plots'), str)
        with self.assertRaises(KeyError):
            h5tbx.get_config('does_not_exist')
        with self.assertRaises(ValueError):
            h5tbx.set_config(require_unit=4.3)
        with self.assertRaises(ValueError):
            h5tbx.set_config(xarray_unit_repr_in_plots=123)
        h5tbx.set_config(xarray_unit_repr_in_plots='(')
        h5tbx.set_config(xarray_unit_repr_in_plots='/')
        with self.assertRaises(ValueError):
            h5tbx.set_config(ureg_format=123)

    def test_changing_ureg_format(self):
        DEFAULT_FORMAT = h5tbx.get_config('ureg_format')
        self.assertEqual(DEFAULT_FORMAT, 'C~')
        ureg = h5tbx.get_ureg()
        self.assertEqual(h5tbx.get_ureg().formatter.default_format, DEFAULT_FORMAT)
        q = ureg('1 mm')
        self.assertEqual(f'{q}', '1 mm')
        h5tbx.set_config(ureg_format='Lx~')
        self.assertEqual(h5tbx.get_config('ureg_format'), 'Lx~')
        self.assertEqual(f'{q}', '\\SI[]{\\begin{pmatrix}\\end{pmatrix}}{\\milli\\meter}')
        h5tbx.set_config(ureg_format='C~')
        self.assertEqual(f'{q}', '1 mm')

        q = ureg('2 mm')
        h5tbx.set_config(ureg_format='Lx~')
        self.assertEqual(f'{q}', '\\SI[]{\\begin{pmatrix}\\end{pmatrix}}{\\milli\\meter}')
        self.assertEqual(f"{q:.2~Lx}", '\\SI[]{\\begin{pmatrix}.2\\end{pmatrix}}{\\milli\\meter}')
        h5tbx.set_config(ureg_format=DEFAULT_FORMAT)

    def test_set_parameter(self):
        h5tbx.use(None)

        with File(mode='w') as h5:
            self.assertEqual(h5.__class__, core.File)

        h5 = File()
        self.assertEqual(h5.__class__, core.File)
        h5.close()

        h5tbx.use('h5tbx')

        with File() as h5:
            self.assertEqual(h5.__class__, h5tbx.File)

        h5 = File()
        self.assertEqual(h5.__class__, h5tbx.File)
        h5.close()
