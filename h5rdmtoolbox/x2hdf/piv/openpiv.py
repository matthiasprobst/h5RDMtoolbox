import pathlib
from abc import ABC
from configparser import ConfigParser
from typing import TypeVar, Dict

import h5py
import pandas as pd

from .interface import PIVFile, PIVParameterInterface, PIV_PARAMETER_GRP_NAME

try:
    from openpiv import windef
except ImportError:
    print('Could not import openpiv. Not installed.')
OpenPIVSetting = TypeVar('OpenPIVSetting')

OPENPIV_SOFTWARE_NAME = 'openpiv'


class OpenPIVParameterFile(PIVParameterInterface):
    """open PIV parmeter interface class"""

    def __init__(self, filename):
        super().__init__(filename)
        if filename is not None:
            _cfg = ConfigParser()
            _cfg.read(filename)
            self.param_dict = {}
            if len(list(_cfg.sections())) == 1:
                for s in _cfg.sections():
                    self.param_dict = dict(_cfg[s])
            else:
                for s in _cfg.sections():
                    self.param_dict[s.strip('-').strip(' ')] = dict(_cfg[s])

    @staticmethod
    def from_dir(dirname):
        """reads parameter from dirname and returns instance of this class"""
        pars = list(dirname.glob(f'*{OpenPIVParameterFile.suffix}'))
        if len(pars) != 1:
            raise FileExistsError('Cannot find parameter file')
        return OpenPIVParameterFile(pars[0])

    def save(self, filename):
        """Save parameter dicitonary to file"""
        with open(filename, 'w') as f:
            f.write(f'[openpiv parameter]')
            for k, v in self.param_dict.items():
                f.write(f'\n{k}={v}')

    @staticmethod
    def from_windef(settings: OpenPIVSetting):
        """Initialize OpenPIVParameterFile from openpiv instance of class windef.Settings"""
        _param_dict = settings.__dict__.copy()
        _param_dict.pop('_FrozenClass__isfrozen')
        o = OpenPIVParameterFile(None)
        o.param_dict = _param_dict
        return o

    def to_hdf(self, grp: h5py.Group):
        """Convert to HDF group"""

        def _to_grp(_dict, _grp):
            for k, v in _dict.items():
                if isinstance(v, dict):
                    _grp = _to_grp(v, _grp.create_group(k))
                else:
                    if k == 'windowsizes':
                        fwin = eval(v)[-1]
                        ds = _grp.create_dataset(k, data=[fwin, fwin, 1])
                        ds.attrs['units'] = 'pixel'
                        ds.attrs['standard_name'] = 'final_interrogation_window_size'
                    elif k == 'overlap':
                        fwin = eval(v)[-1]
                        ds = _grp.create_dataset(k, data=[fwin, fwin, 1])
                        ds.attrs['units'] = 'pixel'
                        ds.attrs['standard_name'] = 'overlap'
                    elif k == 'dt':
                        ds = _grp.create_dataset(k, data=float(v))
                        ds.attrs['units'] = 's'
                        ds.attrs['standard_name'] = 'pulse_delay'
                    elif k == 'scaling_factor':
                        ds = _grp.create_dataset(k, data=float(v))
                        ds.attrs['units'] = 'px/m'
                        ds.attrs['standard_name'] = 'piv_scaling_factor'
                    else:
                        _grp.attrs[k] = v
            return _grp

        return _to_grp(self.param_dict, grp)


class OpenPIVFile(PIVFile, ABC):
    """Open PIV File interface class"""
    suffix: str = None  # any suffix possible
    parameter = OpenPIVParameterFile
    _parameter: OpenPIVParameterFile = None

    def read(self, config, recording_time: float):
        """Read data from file."""
        px_mm_scale = float(self._parameter.param_dict['scaling_factor'])  # px/mm

        data = pd.read_table(self.filename)
        _ix = data["# x"].to_numpy()
        _iy = data["y"].to_numpy()

        for i, x in enumerate(_ix[0:-1]):
            if (x - _ix[i + 1]) > 0:
                break
        ix = _ix[:i + 1]
        iy = _iy[::i + 1]
        nx = len(ix)
        ny = len(iy)
        x = ix / px_mm_scale  # px/mm * 1/px = mm
        y = iy / px_mm_scale  # px/mm * 1/px = mm

        data_dict = {k: v.to_numpy().reshape((ny, nx)) for k, v in data.items() if k not in ('# x', 'y')}
        data_dict['ix'] = ix
        data_dict['iy'] = iy
        data_dict['x'] = x
        data_dict['y'] = y
        variable_attributes = {'ix': dict(standard_name='x_pixel_coordinate', units='pixel'),
                               'iy': dict(standard_name='y_pixel_coordinate', units='pixel'),
                               'x': dict(standard_name='x_coordinate', units='m'),
                               'y': dict(standard_name='y_coordinate', units='m'),
                               'u': dict(standard_name='x_velocity', units='m/s'),
                               'v': dict(standard_name='y_velocity', units='m/s'),
                               }
        if 'mask' in data_dict:
            variable_attributes['mask'] = dict(standard_name='mask', units='')

        if 'w' in data_dict:
            variable_attributes['w'] = dict(standard_name='z_coordinate', units='m')

        return data_dict, {}, variable_attributes

    def to_hdf(self, hdf_filename: pathlib.Path,
               config: Dict, recording_time: float) -> pathlib.Path:
        """converts the snapshot into an HDF file"""
        data, root_attr, variable_attr = self.read(config, recording_time)
        # building HDF file
        if hdf_filename is None:
            _hdf_filename = pathlib.Path.joinpath(self.name.parent, f'{self.name.stem}.hdf')
        else:
            _hdf_filename = hdf_filename
        with h5py.File(_hdf_filename, "w") as main:
            main.attrs['plane_directory'] = str(self.filename.parent.resolve())
            main.attrs['software'] = OPENPIV_SOFTWARE_NAME
            main.attrs['title'] = 'piv snapshot data'

            # process piv_parameters. there must be a parameter file at the parent location
            piv_param_grp = main.create_group(PIV_PARAMETER_GRP_NAME)
            self.write_parameters(piv_param_grp)

            var_list = []
            for varkey, vardata in data.items():
                if vardata.ndim == 1:
                    ds = main.create_dataset(
                        name=varkey, shape=vardata.shape,
                        maxshape=vardata.shape,
                        data=vardata, dtype=vardata.dtype,
                        compression=config['compression'],
                        compression_opts=config['compression_opts'])
                    ds.make_scale()
                else:
                    ds = main.create_dataset(
                        name=varkey, shape=vardata.shape,
                        chunks=vardata.shape,
                        maxshape=vardata.shape,
                        data=vardata, dtype=vardata.dtype,
                        compression=config['compression'],
                        compression_opts=config['compression_opts'])
                    var_list.append(ds)
            for ds in var_list:
                ds.dims[0].attach_scale(main['y'])
                ds.dims[1].attach_scale(main['x'])
            for k, v in variable_attr.items():
                for ak, av in v.items():
                    main[k].attrs[ak] = av
        return hdf_filename
